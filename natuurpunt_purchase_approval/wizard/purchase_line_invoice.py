from openerp.osv import osv
from openerp.tools.translate import _

from collections import defaultdict

class purchase_line_invoice(osv.TransientModel):
    """Creates invoice from purchase order lines.
    (Invoicing Control = Based on Purchase Order lines)

    Modifications from standard are explained by comments starting by NEW.
    """

    _inherit = 'purchase.order.line_invoice'

    def makeInvoices(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        Invoice = self.pool.get('account.invoice')
        PurchaseOrder = self.pool.get('purchase.order')
        PurchaseOrderLine = self.pool.get('purchase.order.line')
        InvoiceLine = self.pool.get('account.invoice.line')
        AccountJournal = self.pool.get('account.journal')

        def multiple_order_invoice_notes(orders):
            notes = ""
            for order in orders:
                notes += "%s \n" % order.notes
            return notes

        def make_invoice_by_partner(partner, orders, invoice_lines_ids):
            name = orders[0].name if orders else ''
            journal_id = AccountJournal.search(cr, uid, [('type', '=', 'purchase')], context=None)
            invoice_data = {
                'name': name,
                'origin': name,
                'type': 'in_invoice',
                'journal_id': journal_id[0] if journal_id else False,
                'reference': partner.ref,
                'account_id': partner.property_account_payable.id,
                'partner_id': partner.id,
                'invoice_line': [(6, 0, invoice_lines_ids)],
                'currency_id': orders[0].pricelist_id.currency_id.id,
                'comment': multiple_order_invoice_notes(orders),
                'payment_term': orders[0].payment_term_id.id,
                'fiscal_position': partner.property_account_position.id,
            }
            invoice_id = Invoice.create(cr, uid, invoice_data)
            PurchaseOrder.write(cr, uid, [order.id for order in orders], {'invoice_ids': [(4, invoice_id)]})
            return invoice_id

        record_ids = context.get('active_ids', [])
        if record_ids:
            partner_invoice_lines = defaultdict(lambda : defaultdict(list))

            for line in PurchaseOrderLine.browse(cr, uid, record_ids, context=context):
                # NEW: do not generate invoice for 'confirmed' lines, only 'approved' should match
                if (not line.invoiced) and (line.state not in ('draft', 'confirmed', 'cancel')):
                    acc_id = PurchaseOrder._choose_account_from_po_line(cr, uid, line, context=context)
                    invoice_line_data = PurchaseOrder._prepare_inv_line(cr, uid, acc_id, line, context=context)
                    invoice_line_data.update({'origin': line.order_id.name})
                    invoice_line_id = InvoiceLine.create(cr, uid, invoice_line_data, context=context)
                    PurchaseOrderLine.write(cr, uid, [line.id], {'invoiced': True, 'invoice_lines': [(4, invoice_line_id)]})
                    partner_invoice_lines[line.partner_id.id][line.order_id].append(invoice_line_id)

            invoice_ids = []
            for order_invoice_lines in partner_invoice_lines.values():
                invoice_line_ids = []
                [invoice_line_ids.extend(ids_list) for ids_list in order_invoice_lines.values()]
                orders = order_invoice_lines.keys()
                invoice_id = make_invoice_by_partner(orders[0].partner_id, orders, invoice_line_ids)
                invoice_ids.append(invoice_id)

        return {
            'domain': "[('id', 'in', %s)]" % invoice_ids,
            'name': _('Supplier Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window'
        }

