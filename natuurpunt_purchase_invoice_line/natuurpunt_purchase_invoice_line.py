# -*- coding: utf-8 -*-
##############################################################################
#
#    Smart Solution bvba
#    Copyright (C) 2010-Today Smart Solution BVBA (<http://www.smartsolution.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################## 

"""

This Module allows to:
1/ Generate invoice lines from purchase order lines for existing invoices
2/ Make the purchase order lines available again when an invoice is deleted

"""

from openerp.osv import fields, osv
from openerp.tools.translate import _


class purchase_order_line_add_to_invoice(osv.osv_memory):

    _name = "purchase.order.line.add_to_invoice"
    _description = "Wizard to generate invoice lines from purchase order lines for existing invoices"

    _columns = {
        'invoice_id': fields.many2one('account.invoice','Factuur', required=True, domain=[('type','=','in_invoice'),('state','in',['draft','open'])])
    }


    def add_to_invoice(self, cr, uid, ids, context=None):
	"""
	Generate an invoice lines from a purchase order line for an existing invoice
	"""

        PurchaseOrder = self.pool.get('purchase.order')
        PurchaseOrderLine = self.pool.get('purchase.order.line')
        InvoiceLine = self.pool.get('account.invoice.line')

	wizard = self.browse(cr, uid, ids[0], context=context) 

        record_ids = context.get('active_ids', [])
        if record_ids:

            for line in PurchaseOrderLine.browse(cr, uid, record_ids, context=context):
                # Do not generate invoice lines for 'confirmed' po lines, only 'approved' should match
                if (not line.invoiced) and (line.state not in ('draft', 'confirmed', 'cancel')):
                    acc_id = PurchaseOrder._choose_account_from_po_line(cr, uid, line, context=context)
                    invoice_line_data = PurchaseOrder._prepare_inv_line(cr, uid, acc_id, line, context=context)
		    print "Invoice Line Data:",invoice_line_data
                    invoice_line_data.update({'origin': line.order_id.name, 'invoice_id':wizard.invoice_id.id})
                    invoice_line_id = InvoiceLine.create(cr, uid, invoice_line_data, context=context)
                    PurchaseOrderLine.write(cr, uid, [line.id], {'invoiced': True, 'invoice_lines': [(4, invoice_line_id)]})

        return {
            'domain': "[('id','in', [%s])]"%(wizard.invoice_id.id),
            'name': _('Supplier Invoices'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window'
        }

class account_invoice(osv.osv):

    _inherit = "account.invoice"


    def unlink(self, cr, uid, id, context=None):
	"""
	Reset the purchase order line visibility when an invoice is deleted
	"""

        PurchaseOrderLine = self.pool.get('purchase.order.line')

	inv = self.browse(cr, uid, id)[0]

	po_line_ids = []
	for line in inv.invoice_line:
	    for po_line in line.purchase_order_line_ids:
	    	po_line_ids.append(po_line.id)
	
	PurchaseOrderLine.write(cr, uid, po_line_ids, {'invoiced':False, 'invoice_lines':False})
	
	return super(account_invoice, self).unlink(cr, uid, id, context=None)








