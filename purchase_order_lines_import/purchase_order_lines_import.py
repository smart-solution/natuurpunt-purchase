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

from osv import osv, fields
from datetime import datetime
import csv
import base64
from tools.translate import _

def lookahead(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, True
        last = val
    # Report the last value.
    yield last, False

class purchase_order_lines_import_wizard(osv.TransientModel):

    _name = "purchase.order.lines.import.wizard"

    _columns = {
        'lines_file': fields.binary('Entry Lines File', required=True),
    }

    def po_lines_import(self, cr, uid, ids, context=None):
        """Import po lines from a file"""
        obj = self.browse(cr, uid, ids)[0]

        order = self.pool.get('purchase.order').browse(cr, uid, context['active_id'])

        # Find the company
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id

        fname = '/tmp/csv_temp_' + datetime.today().strftime('%Y%m%d%H%M%S') + '.csv'
        fp = open(fname,'w+')
        fp.write(base64.decodestring(obj.lines_file))
        fp.close()
        fp = open(fname,'rU')
        reader = csv.reader(fp, delimiter=";", quoting=csv.QUOTE_NONE) #development -> delimiter ","; else delimiter =";"
        entry_vals = []

        for row in reader:
            #row = row[0]
            if reader.line_num <= 1:
                continue
            # Find product 
            product_id = False
            if row[0] != "":
                product_id = self.pool.get('product.product').search(cr, uid, [('id','=',row[0])])
                if not product_id:
                    raise osv.except_osv(_('No procuct found !'), _('No product could be found for the line %s'%(str(reader.line_num))))
                product_id = row[0]
            
            description = False
            if row[1] != "":
                description = row[1]
            # Find the dimensions
            dimension1 = False
            if row[2] != "":
                dimension1 = self.pool.get('account.analytic.account').search(cr, uid, [('code','=',row[2])])
                if not dimension1:
                    raise osv.except_osv(_('No analytic account found !'), _('No analytic account could be found for code %s, line %s'%(row[2],str(reader.line_num))))
                dimension1 = dimension1[0]
            dimension2 = False
            if row[3] != "":
                dimension2 = self.pool.get('account.analytic.account').search(cr, uid, [('code','=',row[3])])
                if not dimension2:
                    raise osv.except_osv(_('No analytic account found !'), _('No analytic account could be found for code %s, line %s'%(row[3],str(reader.line_num))))
                dimension2 = dimension2[0]
            dimension3 = False
            if row[4] != "":
                dimension3 = self.pool.get('account.analytic.account').search(cr, uid, [('code','=',row[4])])
                if not dimension3:
                    raise osv.except_osv(_('No analytic account found !'), _('No analytic account could be found for code %s, line %s'%(row[4],str(reader.line_num))))
                dimension3 = dimension3[0]

            # Find the due date
            date_planned = False
            if row[5] != "": 
                df = row[5].split('/')
                date_planned = df[2] + '-' + df[1].zfill(2) + '-' + df[0].zfill(2)
            
            responsible = False
            if row[6] != "":
                responsible = self.pool.get('res.users').search(cr, uid, [('partner_id','=',int(row[6]))]) 
                if responsible:
                    responsible = responsible[0]
                else:
                    raise osv.except_osv(_('No partner found !'), _('No user could be found for ID %s'%(row[6])))

            # Set Amount
            amount = 0.0
            if row[7] != "":
                amount = float(row[7].replace(',','.'))
                
            # Set unit of measure [8] 
            uom = self.pool.get('product.template').browse(cr, uid, int(row[0])).uom_id.id #TODO: unique op default code?
            if not uom:
                raise osv.except_osv(_('No unit of measure found !'), _('No uom could be found for product on line %s'%(str(reader.line_num))))
            
                
            # Set Unit Price
            unit_price = 0.0
            if row[8] != "":
                unit_price = float(row[8].replace(',','.'))

            # Set delivered quantity
            delivered_qty = 0.0
            if row[9] != "":
                delivered_qty = float(row[9].replace(',','.'))
                if delivered_qty > amount:
                    raise osv.except_osv(_('Delivered quantity can not be higher than quantity!'), _('line %s'%(str(reader.line_num))))


#             # Find tax account
#             tax_account = False
#             tax_amount = 0.0
#             if row[15] != "":
#                 if len(row[15]) == 1:
#                     row[15] = row[15].zfill(2)
#                 tax_accounts = self.pool.get('account.tax.code').search(cr, uid, [('code','=',row[15]),('company_id','=',company)])
#                 print "TAX ACCOUNTS:",tax_accounts
#                 if not tax_accounts:
#                     raise osv.except_osv(_('No tax account found !'), _('No tax account could be found for that code %s'%(row[15])))
#                 tax_account = tax_accounts[0]
# 
#                 if tax_account:
#                     tax_amount = float(row[16])

            vals = {
                'order_id': context['active_id'],
                'product_id': product_id,
                'name': description,
                'analytic_dimension_1_id': dimension1,
                'analytic_dimension_2_id': dimension2,
                'analytic_dimension_3_id': dimension3,
                'date_planned': date_planned,
                'purchase_resp_id': responsible,
                'product_qty': amount,
                'product_uom': uom,
                'price_unit': unit_price,
                #'discount': currency,
                'delivery_quantity': delivered_qty,
                'delivery_state': False,
            }
            entry_vals.append(vals)

        print "ENTRYVALS:",vals

        journal_id = order.journal_id.id
        """loop entry_vals and validate at last entry"""
        for line_vals, context['novalidate'] in lookahead(entry_vals):
            line_id = self.pool.get('purchase.order.line').create(cr, uid, line_vals, context=context)
            #self.pool.get('purchase.order.line').natuurpunt_account_id_change(cr, uid, [line_id], line_vals['account_id'], line_vals['partner_id'], journal_id, context=context)

        return True

class purchase_order_line(osv.osv):

    _inherit = 'purchase.order.line'

    def default_get(self, cr, uid, fields, context=None):
        """Set purchase order line reference from account move reference by default"""
        if context is None:
            context = {}
        result = super(purchase_order_line, self).default_get(cr, uid, fields, context=context)
#         if 'order_id' in context and context['order_id']:
#             move = self.pool.get('purchase.order').browse(cr, uid, context['order_id'])
#             result['ref'] = move.ref
        return result


    def create(self, cr, uid, vals, context=None, check=True):
        if context is None:
            context = {}
#         if 'ref' in vals and not(vals['ref']) and 'order_id' in vals and vals['order_id']:
#             order = self.pool.get('purchase.order').browse(cr, uid, vals['order_id'])
#             vals['ref'] = move.ref
        res = super(purchase_order_line, self).create(cr, uid, vals, context=context)#, check=check)
#         if 'invoice' in context and context['invoice']:
#             ref = context['invoice'].reference or context['invoice'].number or False
#             self.write(cr, uid, [res], {'ref':ref}, check=False, update_check=False, context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
