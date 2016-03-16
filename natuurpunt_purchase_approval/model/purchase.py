from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from natuurpunt_tools import get_eth0
from collections import defaultdict
import logging

_logger = logging.getLogger('natuurpunt_purchase_approval')

# TODO: check that whole procurement workflow stays consistent

class purchase_order(osv.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    def _get_is_ready_for_final_approval(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids)
        for po in self.browse(cr, uid, ids, context=context):
            if po.state == 'confirmed' and all(approval_item.state == 'approved' for approval_item in po.approval_item_ids):
                res[po.id] = True
                self.generate_purchase_order_reminder(cr, uid, po, context=context)
        return res

    _columns = {
        # overriden columns
        'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines',
            states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
        ),
        # new columns
        'approval_item_ids': fields.one2many('purchase.approval.item', 'purchase_order_id', 'Approval Items', readonly=True),
        'is_ready_for_final_approval': fields.function(
            lambda self, *args, **kwargs: self._get_is_ready_for_final_approval(*args, **kwargs),
            type='boolean',
            string='Is ready for final approval',
            store={
                'purchase.order': (
                    lambda self, cr, uid, ids, ctx=None: ids,
                    ['state'],
                    10
                ),
                'purchase.approval.item': (
                    lambda self, cr, uid, ids, ctx=None: self._store_is_ready_for_final_approval(cr, uid, ids, ctx),
                    ['state'],
                    10
                ),
            },
        ),
    }

    def generate_purchase_order_reminder(self, cr, uid, po, context=None):
        """Generate purchase order reminder when final approval"""
        msg_obj = self.pool.get('mail.message')

        def get_html_body():
            base_url = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
            link = ("<b><a href='{}?db={}#id={}&view_type=form&model=purchase.order&action=458'>{}</a></b>")
            line = link.format(base_url, cr.dbname, po.id, po.name)
            html_body_end = "<span><p><p/>"+_('Send from host %s - db %s')%(get_eth0(),cr.dbname)+"</span>"
            yield line + html_body_end

        user = po.create_uid

        msg_vals = {'subject': _('Purchase Order Approval Reminder'),
                    'body': ''.join(get_html_body()),
                    'type': 'notification',
                    'notified_partner_ids': [(6,0,[user.partner_id.id])],
                    }
        msg_obj.create(cr, uid, msg_vals)
        self.send_purchase_order_reminder_email(cr, uid, user, msg_vals, context=context)

    def send_purchase_order_reminder_email(self, cr, uid, user, msg_vals, context=None):
        """Send purchase order approval reminder via e-mail"""

        if user.email_work:
            try:
                data_obj = self.pool.get('ir.model.data')
                template = data_obj.get_object(cr, uid, 'natuurpunt_purchase_approval', 'email_template_purchase_approval_order_reminder')
            except ValueError:
                raise osv.except_osv(_('Error!'),_("Cannot send email: no email template configured.\nYou can configure it under Settings/Technical/Email."))
            assert template._name == 'email.template'
            context['subject']   = msg_vals['subject']
            context['email_to']  = user.email_work
            context['body_html'] = msg_vals['body']
            context['res_id']    = False
            self.pool.get('email.template').send_mail(cr, uid, template.id, False, force_send=True, context=context)
            _logger.info('mail %s: %s', msg_vals['subject'], user.email_work)
            return True
        else:
            return True

    def delete_all_approval_items(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context):
            if po.state != 'draft':
                error_functional_scope = _('Cannot delete approval items')
                detailed_msg = _("""Purchase order %s (id %s) needs to be in 'draft' state for approval items to be deleted.""" % (po.name, po.id))
                raise osv.except_osv(error_functional_scope, detailed_msg)
            else:
                delete_one2many = [(2, approval_item.id) for approval_item in po.approval_item_ids]
                self.write(cr, SUPERUSER_ID, po.id, {'approval_item_ids': delete_one2many}, context)
        return True

    def _aggregate_analytical_accounts(self, cr, uid, po, context=None):
        """Sums all po lines by analytical account, if subjected to approval.
        Amounts are the one found on the lines, thus they are coming from the pricelist:
        so we first convert them in the currency of the company.

        :params po: purchase order (this).
        :returns: dictionary {analytic_account_id: total_amount}.
        """
        aggregated_accounts = defaultdict(float)

        po_currency = po.pricelist_id.currency_id
        company_currency = po.company_id.currency_id
        def aggregate_for(analytic_account_id, subtotal):
            if analytic_account_id:
                if analytic_account_id.dimension_id: # must always be true
                    if analytic_account_id.dimension_id.is_active_for_approval:
                        local_subtotal = self.pool.get('res.currency').compute(cr, uid, po_currency.id, company_currency.id, subtotal, context=context)
                        aggregated_accounts[analytic_account_id] += local_subtotal

        for line in po.order_line:
            aggregate_for(line.analytic_dimension_1_id, line.price_subtotal)
            aggregate_for(line.analytic_dimension_2_id, line.price_subtotal)
            aggregate_for(line.analytic_dimension_3_id, line.price_subtotal)

        for (analytic_account_id, amount) in aggregated_accounts.items():
            if amount <= analytic_account_id.dimension_id.unrestricted_amount:
                aggregated_accounts.pop(analytic_account_id)

        return dict((analytic_account_id.id, amount) for (analytic_account_id, amount) in aggregated_accounts.items())

    def create_all_approval_items(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):
            aggregated_accounts = self._aggregate_analytical_accounts(cr, uid, po, context)
            existing_approval_ids = self.pool.get('purchase.approval.item').search(cr, SUPERUSER_ID, [('purchase_order_id', '=', po.id)], context=context)

            to_be_deleted = []
            for pai in self.pool.get('purchase.approval.item').browse(cr, uid, existing_approval_ids, context=context):
                if pai.analytical_account_id.id in aggregated_accounts:
                    if aggregated_accounts[pai.analytical_account_id.id] <= pai.amount:
                        aggregated_accounts.pop(pai.analytical_account_id.id)
                    else:
                        to_be_deleted.append(pai.id)
                else:
                    to_be_deleted.append(pai.id)
            delete_one2many = [(2, oid) for oid in to_be_deleted]
            self.write(cr, SUPERUSER_ID, po.id, {'approval_item_ids': delete_one2many}, context)

            data = []
            for (account_id, amount) in aggregated_accounts.items():
                data.append({'purchase_order_id': po.id, 'company_id': po.company_id.id, 'analytical_account_id': account_id, 'amount': amount})
            create_one2many = [(0, 0, item) for item in data]
            self.write(cr, uid, po.id, {'approval_item_ids': create_one2many}, context)
        return True

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        self.create_all_approval_items(cr, uid, ids, context)
        return super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)

    def wkf_approve_order(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):

            # check that all approval items are fully approved, just in case admin patched a value manually
            if any(pai.state != 'approved' for pai in po.approval_item_ids):
                error_functional_scope = _('Cannot approve')
                detailed_msg = _("""Purchase order %s (id %s) still has at least one approval item waiting for approval.""" % (po.name, po.id))
                raise osv.except_osv(error_functional_scope, detailed_msg)

            # check that all amounts match all analytical accounts, just in case admin patched a value manually
            aggregated_accounts = self._aggregate_analytical_accounts(cr, uid, po, context)
            ResCurrency = self.pool.get('res.currency')
            company_currency = po.company_id.currency_id
            for pai in po.approval_item_ids:
                po_amount = aggregated_accounts[pai.analytical_account_id.id]
                if ResCurrency.compare_amounts(cr, uid, company_currency, po_amount, pai.amount) == 1:
                    error_functional_scope = _('Cannot approve')
                    detailed_msg = _("""Purchase order %s (id %s) and its approval items do not match regarding the amounts charged on analytical accounts.""" % (po.name, po.id))
                    raise osv.except_osv(error_functional_scope, detailed_msg)

            # invoice control must not allow invoicing of non approved order lines
            line_ids = []
            for line in po.order_line:
                if line.state == 'confirmed':
                    line_ids.append(line.id)
            self.pool.get('purchase.order.line').write(cr, uid, line_ids, {'state': 'approved'}, context=context)

        return super(purchase_order, self).wkf_approve_order(cr, uid, ids, context)

    def action_cancel_draft(self, cr, uid, ids, context=None):
        print "In cance_draft"
        super(purchase_order, self).action_cancel_draft(cr, uid, ids, context)
        for record in self.read(cr, uid, ids, ['order_line'], context):
            self.pool.get('purchase.order.line').write(cr, uid, record['order_line'], {'state': 'draft'}, context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        super(purchase_order, self).action_cancel(cr, uid, ids, context)
        for record in self.read(cr, uid, ids, ['order_line'], context):
            self.pool.get('purchase.order.line').write(cr, uid, record['order_line'], {'state': 'draft'}, context)
        return True

    def copy(self, cr, uid, oid, default=None, context=None):
        if default is None:
            default = {}
        default['approval_item_ids'] = []
        return super(purchase_order, self).copy(cr, uid, oid, default, context)

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        invoice_line_data = super(purchase_order, self)._prepare_inv_line(cr, uid, account_id, order_line, context)
        invoice_line_data.update({
            'analytic_dimension_1_id': order_line.analytic_dimension_1_id.id,
            'analytic_dimension_2_id': order_line.analytic_dimension_2_id.id,
            'analytic_dimension_3_id': order_line.analytic_dimension_3_id.id,
        })
        return invoice_line_data

    def order_close(self, cr, uid, ids, context=None):
        for order_id in ids:
            self.write(cr, uid, [order_id], {'state':'done'})
            for line_id in self.pool.get('purchase.order.line').search(cr, uid, [('order_id','=',order_id)]):
                self.pool.get('purchase.order.line').write(cr, uid, [line_id], {'state':'done'})
        return True

    def order_reopen(self, cr, uid, ids, context=None):
        for order_id in ids:
            self.write(cr, uid, [order_id], {'state':'approved'})
            for line_id in self.pool.get('purchase.order.line').search(cr, uid, [('order_id','=',order_id)]):
                self.pool.get('purchase.order.line').write(cr, uid, [line_id], {'state':'approved','invoiced':False})
        return True



class purchase_order_line(osv.Model):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'

    _columns = {
        # overriden columns
        # TODO: find a hook to modify 'state' instead of redefining it
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('cancel', 'Cancelled')
            ], 'Status', required=True, readonly=True,
            help=' * The \'Draft\' status is set automatically when purchase order in draft status. \
            \n* The \'Confirmed\' status is set automatically as confirm when purchase order in confirm status. \
            \n* The \'Done\' status is set automatically when purchase order is set as done. \
            \n* The \'Cancelled\' status is set automatically when user cancel purchase order.'),
    }

    def name_get(self, cr, uid, ids, context=None):
        res = dict.fromkeys(ids)
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = "%s - %s - %s" % (line.order_id.name, line.order_id.partner_id.name, line.name)
        return res.items()

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=None):
        if not args:
            args = []
        domain = []
        if name.strip():
            # we only search on the description (name), not the parent PO's name
            line_name = name.split(' - ')[-1]
            domain = [('name', operator, line_name)]
        found_ids = self.search(cr, uid, domain + args, limit=limit, context=context)
        return self.name_get(cr, uid, found_ids, context)

    def copy(self, cr, uid, oid, default=None, context=None):
        if default is None:
            default = {}
        return super(purchase_order_line, self).copy(cr, uid, oid, default, context)
