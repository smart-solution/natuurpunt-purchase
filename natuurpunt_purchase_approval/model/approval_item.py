from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
import logging
import datetime

# TODO: review ondelete attributes on all many2one
# TODO: check who is able to do the last approval
# TODO: check index regarding domains (search, record rule, action)
# TODO: manage refusal + on hold
# TODO: check places where _order is used implicitly (IMPORTANT: don't use it implicitly)

_logger = logging.getLogger('natuurpunt_purchase_approval')

class purchase_approval_item(osv.Model):
    _name = 'purchase.approval.item'
    _description = 'Approval items for purchase orders and invoices'
    _order = 'amount'

    STATES = [
        ('waiting', 'Waiting Level Approval'),
        ('approved', 'Approved'),
    ]
    
    def _get_next_line_to_approve(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids)
        for pai in self.browse(cr, uid, ids, context=context):
            for line in pai.line_ids: # order by amount (default)
                if not line.is_approved:
                    res[pai.id] = line.id
                    break
            else: # all lines have been approved
                res[pai.id] = False
        return res

    def _get_next_line_next_approver(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids)
        for pai in self.browse(cr, uid, ids, context=context):
            for line in pai.line_ids: # order by amount (default)
                if not line.is_approved:
                    res[pai.id] = line.planned_approver_id.id
                    break
                else: # all lines have been approved
                    res[pai.id] = False
        return res

    # called from purchase.order
    def _store_is_ready_for_final_approval(self, cr, uid, ids, context=None):
        po_ids = []
        for approval_item in self.read(cr, uid, ids, ['purchase_order_id'], context):
            if approval_item['purchase_order_id']:	
                po_ids.append(approval_item['purchase_order_id'][0])
        return po_ids

    def _get_dimension_user(self, cr, uid, ids, field_name, arg, context=None):
        if context is None: 
            context = {}
        res = {}
        for pai in self.browse(cr, uid, ids, context=context):
            invoice = self.pool['account.invoice'].read(cr, SUPERUSER_ID, [pai.invoice_id.id], ['dimension_user_id'], context=context)
            res[pai.id] = invoice[0]['dimension_user_id']
        return res

    def _store_get_values(self, cr, uid, ids, fields, context=None):
        """force function_field 'line_id' to be stored first
        because the stored related 'next_approver_id' field relies on its value
        the default _store_get_values return an arbitrary list
        """
        return [(priority,model_name,record_ids,sorted(function_fields, key = lambda x: 0 if x=='line_id' else 1)) 
                 for priority,model_name,record_ids,function_fields 
                 in super(purchase_approval_item, self)._store_get_values(cr, uid, ids, fields, context)]

    _columns = {
        'purchase_order_id': fields.many2one('purchase.order', 'Purchase Order', select=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', select=True),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, readonly=True),
        'dimension_user_id':fields.function(_get_dimension_user,
                                            method=True,
                                            type='many2one',
                                            relation='res.users',
                                            string='Verantw voor analytische toewijzing',
                                            store={
				                'account.invoice': (
                                                    lambda self, cr, uid, ids, ctx=None: self.pool.get('purchase.approval.item').search(cr, uid, [('invoice_id', 'in', ids)], context=ctx),
				                    ['dimension_user_id'],
				                    10,
				                ),
                                            },
					   ),

        # TODO: a_a_id not required if both po_id and invoice_id are null, so that an invoice without PO can be approved without a_a
        'analytical_account_id': fields.many2one('account.analytic.account', 'Analytical Account', select=True, required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True, readonly=True),
        'line_ids': fields.one2many('purchase.approval.item.line', 'approval_item_id', 'Levels of Approval', readonly=True),
        'line_id': fields.function(
            lambda self, *args, **kwargs: self._get_next_line_to_approve(*args, **kwargs),
            type='many2one',
            relation='purchase.approval.item.line',
            string='Next Level to Be Approved',
            store={
                'purchase.approval.item': (
                    lambda self, cr, uid, ids, ctx=None: ids,
                    ['analytical_account_id'],
                    10
                ),
                'purchase.approval.item.line': (
                    lambda self, cr, uid, ids, ctx=None: self.pool.get('purchase.approval.item').search(cr, uid, [('line_id', 'in', ids)], context=ctx),
                    ['is_approved'],
                    10
                ),
            },
        ),
        'next_level': fields.related('line_id', 'name', type='char', string='Next Level', help='Name of next level to approve.'),
        'next_amount': fields.related('line_id', 'amount', type='float', string='Next Amount', help='Amount of next level to approve.'),
        'next_approver_id': fields.related('line_id', 'planned_approver_id', type='many2one', relation='res.users', string='Next Approver', store=True),
        'partner_id': fields.related('invoice_id', 'partner_id', type='many2one', relation='res.partner', string='Partner', store=True),
        'state': fields.selection(STATES, 'State'),
        'line_next_approver_id': fields.function(
            lambda self, *args, **kwargs: self._get_next_line_next_approver(*args, **kwargs),
            type='many2one',
            relation='res.users',
            string='Next Approver',
            store={
                'purchase.approval.item': (
                    lambda self, cr, uid, ids, ctx=None: ids,
                    ['analytical_account_id'],
                    10
                ),
                'purchase.approval.item.line': (
                    lambda self, cr, uid, ids, ctx=None: self.pool.get('purchase.approval.item').search(cr, uid, [('line_id', 'in', ids)], context=ctx),
                    ['is_approved'],
                    10
                ),
            },
        ),
        'backup_approver': fields.related('next_approver_id', 'approval_substitute_id', type='many2one', relation='res.users', string='Backup Approver',store=False),
    }

    _defaults = {
        'state': 'waiting',
    }

    _sql_constraints = [
        ('unique_po_aa', 'unique(purchase_order_id, analytical_account_id)', 'There is already an approval item for this PO and this analytical account.'),
        ('unique_invoice_aa', 'unique(invoice_id, analytical_account_id)', 'There is already an approval item for this invoice and this analytical account.'),
        ('at_least_invoice_or_po_is_null', 'CHECK (purchase_order_id IS NULL OR invoice_id IS NULL)',
            'A purchase approval item is either linked to a PO or linked to an invoice, not both documents at the same time.'),
    ]

    def _create_lines(self, cr, uid, pai_id, context=None):
        pai = self.browse(cr, uid, pai_id, context=context)
        a_a_id = pai.analytical_account_id # required value
        DimensionLevel = self.pool.get('account.analytic.dimension.level')

        covered_amount = 0 # the amount already covered by approval item lines
        while a_a_id:
            if a_a_id.manager_id:
                level_id = a_a_id.manager_id.purchase_approval_level_id
                if level_id:
                    dim_level_id = DimensionLevel.search(cr, SUPERUSER_ID, [('level_id', '=', level_id.id), ('dimension_id', '=', a_a_id.dimension_id.id)], context=context)
                    if dim_level_id:
                        dim_level = DimensionLevel.read(cr, SUPERUSER_ID, dim_level_id[0], ['name', 'amount'], context=context)
                        if covered_amount < dim_level['amount']: # do not use twice the same level
                            values = {
                                'approval_item_id': pai_id,
                                'level_id': dim_level['id'],
                                'name': dim_level['name'],
                                'amount': dim_level['amount'],
                                'planned_approver_id': a_a_id.manager_id.id,
                                'is_approved': pai.state == "approved",
                                'company_id': pai.company_id.id,
                            }
                            self.pool.get('purchase.approval.item.line').create(cr, uid, values, context=context)
                            covered_amount = dim_level['amount']

                            # when pai.amount gets approvement, no need to approve higher amount value
                            if covered_amount >= pai.amount:
                                break

            a_a_id = a_a_id.parent_id

        else: # no more parent a_a_id and the amount is still not covered
            a_a_id = pai.analytical_account_id
            if not a_a_id.dimension_id.level_ids:
                # this should probably never happen, except if admin patched the DB to work around ORM constraints
                error_functional_scope = "%s -> %s" % (_('Integrity Error'), _('Cannot create approval items'))
                detailed_msg = _("""There is no level defined for dimension "%s" (id %s) although it is active for approval."""
                        % (a_a_id.dimension_id.name, a_a_id.dimension_id.id))
                raise osv.except_osv(error_functional_scope, detailed_msg)
            else:
                for dim_level in a_a_id.dimension_id.level_ids: # order by amount (default)
                    if not dim_level.fallback_approver_id:
                        break
                    if covered_amount < dim_level.amount: # do not use twice the same level
                        values = {
                            'approval_item_id': pai_id,
                            'level_id': dim_level.id,
                            'name': dim_level.name,
                            'amount': dim_level.amount,
                            'planned_approver_id': dim_level.fallback_approver_id.id,
                            'is_approved': pai.state == "approved",
                            'company_id': pai.company_id.id,
                        }
                        self.pool.get('purchase.approval.item.line').create(cr, uid, values, context=context)
                        covered_amount = dim_level.amount

                        # when pai.amount gets approvement, no need to approve higher amount value
                        if covered_amount >= pai.amount:
                            break

        if covered_amount < pai.amount: # we still could not manage to cover the amount
            error_functional_scope = _('Cannot create approval items')
            detailed_msg = _("""For dimension "%s" (id %s), there is no level with sufficient amount to cover %s on analytical account "%s" (id %s)."""
                    % (a_a_id.dimension_id.name, a_a_id.dimension_id.id, pai.amount, a_a_id.name, a_a_id.id))
            raise osv.except_osv(error_functional_scope, detailed_msg)

    def create(self, cr, uid, values, context=None):
        pai_id = super(purchase_approval_item, self).create(cr, uid, values, context)
        self._create_lines(cr, uid, pai_id, context)
        return pai_id

    def approve_item_level(self, cr, uid, ids, context=None):
        for pai in self.browse(cr, uid, ids, context=context):
            
            # In case of a refund, check if the invoice is approved
            if pai.invoice_id.refunded_invoice_id and pai.invoice_id.refunded_invoice_id.state not in ('approved','paid'):
                error_functional_scope = _('Cannot approve')
                detailed_msg = _("""Source Invoice %s (id %s) is not fully approved.""" % (pai.invoice_id.refunded_invoice_id.name, pai.invoice_id.refunded_invoice_id.id))
                raise osv.except_osv(error_functional_scope, detailed_msg)

            values = {
                'is_approved': True,
                'approval_timestamp': datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'actual_approver_id': uid,
            }
            self.pool.get('purchase.approval.item.line').write(cr, uid, [pai.line_id.id], values, context=context)
            if all(line.is_approved for line in pai.line_ids):
                self.write(cr, SUPERUSER_ID, [pai.id], {'state': 'approved'}, context=context)
                if pai.invoice_id:
                    res = self.pool.get('account.invoice').invoice_approve(cr, uid, [pai.invoice_id.id], context=context)
                    _logger.info("pai {}/{} uid: {} invoice: {} approved: {}".format(
                        pai.id,
                        pai.line_id.id,
                        uid,
                        pai.invoice_id.internal_number,
                        res)
                    )

        return True

class purchase_approval_item_line(osv.Model):
    _name = 'purchase.approval.item.line'
    _description = 'Approval item'
    _order = 'amount'

    _columns = {
        'approval_item_id': fields.many2one('purchase.approval.item', 'Approval Item', select=True, readonly=True, ondelete='set null'),
        'level_id': fields.many2one('account.analytic.dimension.level', 'Level to be Approved', select=True, required=True),
        'company_id': fields.related('approval_item_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),

        # level_id target might get changed after item creation so we copy the level name and amount here
        'name': fields.char('Level to be Approved', size=32, required=True, readonly=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True, readonly=True),

        'planned_approver_id': fields.many2one('res.users', 'Planned Appover', readonly=True),
        'actual_approver_id': fields.many2one('res.users', 'Actual Appover', readonly=True),
        'is_approved': fields.boolean('Is Approved?'),
        'approval_timestamp': fields.datetime('Approval Timestamp', readonly=True),
     }

    _defaults = {
        'is_approved': False,
    }

    _sql_constraints = [
        ('unique_item_id_level_id', 'unique(approval_item_id, level_id)', 'There is already an approval item line for this approval item and this dimension level.'),
    ]

