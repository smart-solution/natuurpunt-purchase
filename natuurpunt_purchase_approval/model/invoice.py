from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

from collections import defaultdict

class AccountInvoice(osv.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    _columns = {
        # overriden columns
        # TODO: most fields should be readonly in the new "confirmed" state

        # TODO: find a hook to modify 'state' instead of redefining it
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            # added 'confirmed' and 'approved' states for supplier invoices
            ('confirmed','Waiting Approval'),
            ('approved','Approved'),
            ('paid','Paid'),
            ('cancel','Cancelled'),
            ],'Status', select=True, readonly=True, track_visibility='onchange',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma status,invoice does not have an invoice number. \
            \n* The \'Open\' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice. \
            \n* The \'Waiting Approval\' when supplier invoice is waiting for approval. \
            \n* The \'Approved\' when supplier invoice is approved. \
            \n* The \'Paid\' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled. \
            \n* The \'Cancelled\' status is used when user cancel invoice.'),

        # new columns
        'approval_item_ids': fields.one2many('purchase.approval.item', 'invoice_id', readonly=True),
        'purchase_order_ids': fields.many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id',
        'Purchase Orders', readonly="True", help="Purchase Orders used to generate current Invoice."),
        'refund_id': fields.many2one('account.invoice', 'Refund', domain="[('type','=','in_refund')]"),
        'refunded_invoice_id': fields.many2one('account.invoice', 'Source Invoice', domain="[('type','=','in_invoice')]"),
    }

    def delete_all_approval_items(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.state != 'draft':
                error_functional_scope = _('Cannot delete approval items')
                detailed_msg = _("""Invoice %s (id %s) needs to be in 'draft' state for approval items to be deleted.""" % (invoice.name, invoice.id))
                raise osv.except_osv(error_functional_scope, detailed_msg)
            else:
                delete_one2many = [(2, approval_item.id) for approval_item in invoice.approval_item_ids]
                self.write(cr, SUPERUSER_ID, invoice.id, {'approval_item_ids': delete_one2many}, context)
        return True

    def _aggregate_analytical_accounts(self, cr, uid, invoice, context):
        """Sums all invoice lines by analytical account, if subjected to approval.
        Amounts are the one found on the lines, thus they are coming from the pricelist:
        so we first convert them in the currency of the company.

        :params invoice: invoice (this).
        :returns: dictionary {analytic_account_id: total_amount}.
        """
        aggregated_accounts = defaultdict(float)

        po_currency = invoice.currency_id
        company_currency = invoice.company_id.currency_id
        def aggregate_for(analytic_account_id, subtotal):
            if analytic_account_id:
                if analytic_account_id.dimension_id:
                    if analytic_account_id.dimension_id.is_active_for_approval:
                        local_subtotal = self.pool.get('res.currency').compute(cr, uid, po_currency.id, company_currency.id, subtotal, context=context)
                        aggregated_accounts[analytic_account_id] += local_subtotal

        for line in invoice.invoice_line:
            aggregate_for(line.analytic_dimension_1_id, line.price_subtotal)
            aggregate_for(line.analytic_dimension_2_id, line.price_subtotal)
            aggregate_for(line.analytic_dimension_3_id, line.price_subtotal)

        # XXX: check if next loop is relevant for invoices (it is for PO)
        # it may actually make more sense to check unrestricted amount later in the process
        for (analytic_account_id, amount) in aggregated_accounts.items():
            if amount <= analytic_account_id.dimension_id.unrestricted_amount:
                aggregated_accounts.pop(analytic_account_id)

        return dict((analytic_account_id.id, amount) for (analytic_account_id, amount) in aggregated_accounts.items())

    def _aggregate_related_orders_analytical_accounts(self, cr, uid, invoice, context=None):
        orders_aggregated_accounts = defaultdict(float)
        # for all related PO, aggregates all lines (even those not invoiced on the current invoice)
        for order_id in invoice.purchase_order_ids: # PO used when *creating* current invoice
            for approval_item in order_id.approval_item_ids:
                orders_aggregated_accounts[approval_item.analytical_account_id.id] += approval_item.amount
            # no need to test for unrestricted_amount since *order* approval_item_ids have been created without it (see purchase_order._aggregate_analytical_accounts)
        return orders_aggregated_accounts

    def _aggregate_related_approved_invoices_analytical_accounts(self, cr, uid, invoice, context=None):
        other_invoices_aggregated_accounts = defaultdict(float)

        # all related approved invoices, except the current invoice (which is not approved anyway)
        related_approved_invoice_ids = set()
        for order in invoice.purchase_order_ids:
            print "### PO:",order.id
            for related_invoice_id in order.invoice_ids:
                print "### RINV:",related_invoice_id
                if related_invoice_id != invoice.id and related_invoice_id.state in ('approved', 'paid', 'payment_blocked'):
                    related_approved_invoice_ids.add(related_invoice_id)

        # for all related approved invoices, aggregates all lines
        for invoice_id in related_approved_invoice_ids:
            #for approval_item in related_invoice_id.approval_item_ids:
            for approval_item in invoice_id.approval_item_ids:
                other_invoices_aggregated_accounts[approval_item.analytical_account_id.id] += approval_item.amount
                print "### AI AMOUNT:",approval_item.amount
            # no need to test for unrestricted_amount since *invoice* approval_item_ids have been created without it (see account_invoice._aggregate_analytical_accounts)

        print "### OIAA",other_invoices_aggregated_accounts
        return other_invoices_aggregated_accounts

    def create_all_approval_items(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids, context=context):
            # required for invoices: "delete all then create or update" (anyway you should not be able to cancel an invoice or set it to draft)
            exists_approval = self.pool.get('purchase.approval.item').search(cr, SUPERUSER_ID, [('invoice_id', '=', invoice.id)], context=context)
            if exists_approval:
                error_functional_scope = _('Cannot create approval items')
                detailed_msg = _("""There is already at least one approval line for invoice %s (id %s).\
                    You need to delete all approval lines of an invoice before creating new ones.""" % (invoice.name, invoice.id))
                raise osv.except_osv(error_functional_scope, detailed_msg)
            else:
                # aggregates across all approved invoices related to the PO lines invoiced here + other PO lines from the same PO

                # type: orders_aggregated_accounts = defaultdict(float)
                orders_aggregated_accounts = self._aggregate_related_orders_analytical_accounts(cr, uid, invoice, context=context)

                # type: other_invoices_aggregated_accounts = defaultdict(float)
                other_invoices_aggregated_accounts = self._aggregate_related_approved_invoices_analytical_accounts(cr, uid, invoice, context=context)

                aggregated_accounts = self._aggregate_analytical_accounts(cr, uid, invoice, context)
                approval_items = []
                ResCurrency = self.pool.get('res.currency')
                company_currency = invoice.company_id.currency_id
                for (a_a_id, amount) in aggregated_accounts.items():
                    related_amount = other_invoices_aggregated_accounts[a_a_id] # KeyError -> 0.0
                    #related_amount = 0
                    orders_amount = orders_aggregated_accounts[a_a_id] # no KeyError possible here
                    print "### invoice:",invoice.number
                    print "### amount",amount
                    print "### related amount",related_amount
                    #approval_item_data = {'invoice_id': invoice.id, 'company_id': invoice.company_id.id, 'analytical_account_id': a_a_id, 'amount': amount + related_amount, 
                    #                      'dimension_user_id':invoice.dimension_user_id.id}
                    approval_item_data = {'invoice_id': invoice.id, 'company_id': invoice.company_id.id, 'analytical_account_id': a_a_id, 'amount': amount, 
                                          'dimension_user_id':invoice.dimension_user_id.id}
                    a_a = self.pool.get('account.analytic.account').browse(cr, uid, a_a_id, context=context)
                    # we keep the if clause without currency flavor as documentation
                    # if (amount + related_amount - orders_amount) <= a_a.dimension_id.tolerance_absolute and \
                    #    amount + related_amount <= (1 + a_a.dimension_id.tolerance_percent/100) * orders_amount:
                    if ResCurrency.compare_amounts(cr, uid, company_currency, amount + related_amount - orders_amount, a_a.dimension_id.tolerance_absolute) <= 0 and \
                        ResCurrency.compare_amounts(cr, uid, company_currency, amount + related_amount, (1 + a_a.dimension_id.tolerance_percent/100) * orders_amount) <= 0:
                        # then we can auto-approve for this analytic account
                        print "Auto Approve"
                        approval_item_data.update({'state': 'approved'})
                    approval_items.append(approval_item_data)

                create_one2many = [(0, 0, item) for item in approval_items]
                data = {'approval_item_ids': create_one2many}
                if all(item.get('state', 'waiting') == 'approved' for item in approval_items):
                    data.update({'state': 'approved'})
                self.write(cr, uid, [invoice.id], data, context)
        return True

    def invoice_validate(self, cr, uid, ids, context=None):
        super(AccountInvoice, self).invoice_validate(cr, uid, ids, context)
        supplier_invoice_ids = [invoice.id for invoice in self.browse(cr, uid, ids, context=context) if invoice.type == 'in_invoice']
        if supplier_invoice_ids:
            self.write(cr, uid, supplier_invoice_ids, {'state': 'confirmed'}, context)
            self.create_all_approval_items(cr, uid, supplier_invoice_ids, context) # may auto approve some invoices
        supplier_refund_ids = [invoice.id for invoice in self.browse(cr, uid, ids, context=context) if invoice.type == 'in_refund']
        if supplier_refund_ids:
            #self.write(cr, uid, supplier_refund_ids, {'state': 'approved'}, context)
            self.write(cr, uid, supplier_refund_ids, {'state': 'confirmed'}, context)
            self.create_all_approval_items(cr, uid, supplier_refund_ids, context) # may auto approve some invoices
        return True

    def invoice_approve(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids):
            assert invoice.state == 'confirmed', 'Invoice must be confirmed before it can be approved'
            if not invoice.approval_item_ids:
                continue
            #approve invoice when all approval_items are approved
            if not([app_item for app_item in invoice.approval_item_ids if app_item.state != 'approved']):
                self.write(cr, uid, ids, {'state': 'approved'}, context=context)
        return True

    def copy(self, cr, uid, oid, default=None, context=None):
        if default is None:
            default = {}
        default['approval_item_ids'] = []
        default['purchase_order_ids'] = []
        default['refund_id'] = False
        default['refunded_invoice_id'] = False
        return super(AccountInvoice, self).copy(cr, uid, oid, default, context)

class AccountInvoiceLine(osv.Model):
    _name = 'account.invoice.line'
    _inherit = 'account.invoice.line'

    _columns = {
        # new columns
        'purchase_order_line_ids': fields.many2many('purchase.order.line', 'purchase_order_line_invoice_rel', 'invoice_id', 'order_line_id', 'Purchase Order Lines', readonly=True),
    }

    def copy(self, cr, uid, oid, default=None, context=None):
        if default is None:
            default = {}
        default['purchase_order_line_ids'] = []
        return super(AccountInvoiceLine, self).copy(cr, uid, oid, default, context)

#    def write(self, cr, uid, ids, vals, context=None):
#        """Check if the po line should still be available"""
#        if 'quantity' in vals:
#            for line in self.browse(cr, uid, ids):
#
#        return super(purchase_order_line, self).write(cr, uid, ids, vals=vals, context=context)

class account_invoice_refund(osv.osv_memory):

    """Refunds invoice"""

    _inherit = "account.invoice.refund"


    def invoice_refund(self, cr, uid, ids, context=None):
        res = super(account_invoice_refund, self).invoice_refund(cr, uid, ids, context=context)
        print "REFUND RES:",res
        print "CTX:",context
        refund_id = res['domain'][1][2][0]
        invoice_id = context['active_id']
        self.pool.get('account.invoice').write(cr, uid, [invoice_id], {'refund_id':refund_id})
        self.pool.get('account.invoice').write(cr, uid, [refund_id], {'refunded_invoice_id':invoice_id})
        return res


