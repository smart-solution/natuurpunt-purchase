# -*- coding: utf-8 -*-
from openerp.osv import fields, orm
from natuurpunt_tools import compose, uids_in_group

class puachase_order(orm.Model):

    _inherit = 'purchase.order'

    _columns = { 
        'quantity_check': fields.boolean('Check on quantity'),
    }   

    _defaults = { 
        'quantity_check': True,
    }   

class purchase_order_line(orm.Model):

    def _invoiced_qty(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for line in self.browse(cursor, user, ids, context=context):
            invoiced_qty = 0.0
            for invoice_line in line.invoice_lines:
                invoiced_qty += invoice_line.quantity
            res[line.id] = invoiced_qty
        return res

    def _invoiced_amount(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for line in self.browse(cursor, user, ids, context=context):
            invoiced_amount = 0.0
            for invoice_line in line.invoice_lines:
                invoiced_amount += invoice_line.price_subtotal
            res[line.id] = invoiced_amount
        return res

    def _can_change_delivery_state(self,cr,uid,ids,fieldnames,args,context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            purchase_users = uids_in_group(self,cr,uid,'group_purchase_user',context=context)
            res[line.id]=True if line.purchase_resp_id.id==uid or uid in purchase_users else False
        return res

    _inherit = 'purchase.order.line'

    _columns = {
        'invoiced_qty': fields.function(_invoiced_qty, string='Invoiced quantity', type='float'),
        'invoiced_amount': fields.function(_invoiced_amount, string='Invoiced amount', type='float'),
        'can_change_delivery_state': fields.function(
                                        _can_change_delivery_state,
                                        method=True,
                                        type='boolean',
                                        string='Can change delivery state',),
    }

class account_journal(orm.Model):

    _inherit = "account.journal"

    _columns = {
        'po_line_invoice_journal': fields.boolean('Journal for PO line invoice generation'),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if 'po_line_invoice_journal' in vals and vals['po_line_invoice_journal']:
            inv_journal = self.search(cr, uid, [('po_line_invoice_journal','=',True)])
            if inv_journal:
                self.write(cr, uid, inv_journal, {'po_line_invoice_journal':False})
        return super(account_journal, self).write(cr, uid, ids, vals, context=context)

