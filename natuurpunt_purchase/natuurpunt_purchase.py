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

import time
from openerp.osv import fields, osv
from openerp import netsvc
from openerp.osv.orm import browse_record, browse_null
from openerp.tools.translate import _


class purchase_order(osv.osv):

        _inherit = "purchase.order"

        _columns = {
            'partner_delivery_id': fields.many2one('res.partner', 'Partner for Delivery'),
            'delivery_address': fields.text('Leveradres ',help="Alleen in te vullen indien verschillend van adres 'Partner voor levering' "),
            'default_po_currency': fields.related('pricelist_id', 'currency_id', type='many2one', relation='res.currency', string='Default Currency', readonly=True),
            'dest_address_id':fields.many2one('res.partner', 'Customer Address (Direct Delivery)',
                states={'confirmed':[('readonly',False)], 'approved':[('readonly',False)],'done':[('readonly',True)]},
                help="Put an address if you want to deliver directly from the supplier to the customer. " \
                    "Otherwise, keep empty to deliver to your own company."),
        }

        _defaults = {
            'invoice_method': 'manual',
        }

        _order = 'name desc'
            
        def wkf_send_rfq(self, cr, uid, ids, context=None):
            '''
            This function opens a window to compose an email, with the edi purchase template message loaded by default
            '''
            ir_model_data = self.pool.get('ir.model.data')
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = dict(context)
            ctx.update({
                'default_model': 'purchase.order',
                'default_res_id': ids[0],
                'default_use_template': bool(template_id),
                #'default_template_id': template_id,
                'default_template_id': False,
                'default_composition_mode': 'comment',
            })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx, 
            }


        def create(self, cr, uid, vals, context=None):
            """Adds the partner to deliver"""            
            if 'warehouse_id' in vals and vals['warehouse_id']:
                warehouse = self.pool.get('stock.warehouse').browse(cr, uid, vals['warehouse_id'])
                if warehouse.partner_id:
                    vals['dest_address_id'] = warehouse.partner_id.id
            return super(purchase_order, self).create(cr, uid, vals, context=context)

        def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, delivery_partner_id):
            if not warehouse_id:
                return {}
            warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id)
            if warehouse.partner_id and not delivery_partner_id:
                return {'value':{'location_id': warehouse.lot_input_id.id, 'dest_address_id': warehouse.partner_id.id}}
            elif not warehouse.partner_id and delivery_partner_id:
                return False
            else:                
                return {'value':{'location_id': warehouse.lot_input_id.id}}


        def status_rfq_sent(self, cr, uid, ids, context=None):
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'purchase.order', ids[0], 'send_rfq', cr)
            return True

        def print_po(self, cr, uid, ids, context=None):
            '''
            This function prints the purchase order
            '''
            assert len(ids) == 1, 'This option should only be used for a single id at a time'
            datas = {
                     'model': 'purchase.order',
                     'ids': ids, 
                     'form': self.read(cr, uid, ids[0], context=context),
            }
            return {'type': 'ir.actions.report.xml', 'report_name': 'aankoop.order', 'datas': datas, 'nodestroy': True}


class purchase_order_line(osv.osv):

    _inherit = "purchase.order.line"

    def _check_qty_and_unitprice(self, cr, uid, ids, context=None):
        for order_line in self.browse(cr, uid, ids, context=context):
            if order_line.product_qty < 0 or order_line.price_unit < 0:
                return False
        return True

    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Purchase Requisition'),
        'requisition_line_id': fields.many2one('purchase.requisition.line', 'Purchase Requisition Line'),
        'purchase_resp_id': fields.related('requisition_line_id', 'requisition_id', 'user_id', type='many2one', relation='res.users', string='Resp Req', store=True),
        'po_resp_id': fields.related('order_id', 'create_uid', type='many2one', relation='res.users', string='Resp Order', store=True),
        'delivery_state': fields.char('Delivery Status', size=128),
        'po_state': fields.related('order_id','state', type="char", string='State', readonly=True),
        'dest_address_id': fields.related('order_id', 'dest_address_id', type="many2one", relation="res.partner", string="Partner for Delivery", store=False),
    }

    _order = "order_id desc,name"

    _constraints = [
         (_check_qty_and_unitprice, _(u'Qty/price must be more than 0'), ['product_qty', 'price_unit']),
    ]

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {} 
        result = super(purchase_order_line, self).default_get(cr, uid, fields, context=context)
        print "DEFAULTGETCTX:",context

       # Copy the values of the last created line
        if 'order_id' in context and context['order_id']:
            lines = self.pool.get('purchase.order').read(cr, uid, context['order_id'], ['order_line'])['order_line']
            if lines:
                line = self.pool.get('purchase.order.line').browse(cr, uid, max(lines))
                result['analytic_dimension_1_id'] = line.analytic_dimension_1_id.id
                result['analytic_dimension_2_id'] = line.analytic_dimension_2_id.id
                result['analytic_dimension_3_id'] = line.analytic_dimension_3_id.id
                result['purchase_resp_id'] = line.purchase_resp_id.id
        return result

    def unlink(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids):
            if line.state == 'approved':
                raise osv.except_osv(_('Error!'), _('You cannot delete approved purchase order lines.'))
        return super(purchase_order_line, self).unlink(cr, uid, ids, context=context)

    def line_invoice_reopen(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids):
            if line.invoiced:
                line.write({'invoiced':False})
        return True

    def onchange_product_uom(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
        partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
        name=False, price_unit=False, context=None):
        return True

purchase_order_line()

class purchase_order_line_delivery(osv.osv_memory):

    _name = "purchase.order.line.delivery"

    _columns = {
        'delivery_state': fields.char('Delivery Status', size=128)
    }

    def delivery_state_set(self, cr, uid, ids, context=None):
        for wiz in self.browse(cr, uid ,ids):
            self.pool.get('purchase.order.line').write(cr, uid, [context['active_id']], {'delivery_state':wiz.delivery_state})
            po_line = self.pool.get('purchase.order.line').browse(cr, uid, context['active_id'])
            user = self.pool.get('res.users').browse(cr, uid, uid)
            log_vals = {
                'author_id': user.partner_id.id,
                'type': 'notification',
                'model': 'purchase.order',
                'res_id': po_line.order_id.id,
                'body': "Delivery status of line %s <br/>Changed to : %s"%(po_line.name, wiz.delivery_state)
            }
            self.pool.get('mail.message').create(cr, uid, log_vals)
        return True


class purchase_requisition(osv.osv):

    _inherit = 'purchase.requisition'

    _columns = {
        'purchase_line_ids': fields.one2many('purchase.order.line', 'requisition_id', 'Purchase Lines'),
        'state': fields.selection([('draft','New'),('cancel','Cancelled'),('done','Purchase Done')],
                       'Status', track_visibility='onchange', required=True),

    }

    _order = "date_start desc"


    def create(self, cr, uid, vals, context=None):
        print "Vals",vals
        ids =  super(purchase_requisition, self).create(cr, uid, vals, context=context)
        obj = self.browse(cr, uid, ids)
        print "PR Name:",obj.name
        return ids

    def copy(self, cr, uid, id, default=None, context=None):
        """Do not copy purchase order line"""
        if default == None:
            default= {}
        default['purchase_line_ids'] = []
        default.update({'purchase_line_ids': []})
        return super(purchase_requisition, self).copy(cr, uid, id, default=default, context=context)

    def unlink(self, cr, uid, ids, context=None):
        return super(purchase_requisition, self).unlink(cr, uid, ids, context=context)

    def tender_cancel(self, cr, uid, ids, context=None):
        purchase_order_obj = self.pool.get('purchase.order')
        for purchase in self.browse(cr, uid, ids, context=context):
            for purchase_id in purchase.purchase_ids:
                if purchase.state != 'draft' and purchase_id.state != 'cancel':
                    raise osv.except_osv(_('Warning!'), _('First cancel the Purchase Orders for this Purchase requisition.'))
                
                #if str(purchase_id.state) in('draft'):
                #    purchase_order_obj.action_cancel(cr,uid,[purchase_id.id])
            for line in purchase.line_ids:
                if str(line.state) in ('draft'):
                    line.write({'state':'cancel'})
                
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def tender_reset(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            for line in purchase.line_ids:
                if str(line.state) in ('cancel'):
                    line.write({'state':'draft'})
        return self.write(cr, uid, ids, {'state': 'draft'})


#    def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
#        """
#        Create New RFQ for Supplier
#        """
#        if context is None:
#            context = {}
#        assert partner_id, 'Supplier should be specified'
#        purchase_order = self.pool.get('purchase.order')
#        purchase_order_line = self.pool.get('purchase.order.line')
#        res_partner = self.pool.get('res.partner')
#        fiscal_position = self.pool.get('account.fiscal.position')
#        supplier = res_partner.browse(cr, uid, partner_id, context=context)
#        supplier_pricelist = supplier.property_product_pricelist_purchase or False
#        res = {}
#        for requisition in self.browse(cr, uid, ids, context=context):
#            if supplier.id in filter(lambda x: x, [rfq.state <> 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
#                 raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
#            location_id = requisition.warehouse_id.lot_input_id.id
#            purchase_id = purchase_order.create(cr, uid, {
#                        'origin': requisition.name,
#                        'partner_id': supplier.id,
#                        'pricelist_id': supplier_pricelist.id,
#                        'location_id': location_id,
#                        'company_id': requisition.company_id.id,
#                        'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
#                        'requisition_id':requisition.id,
#                        'notes':requisition.description,
#                        'warehouse_id':requisition.warehouse_id.id ,
#            })
#            res[requisition.id] = purchase_id
#            for line in requisition.line_ids:
#                if 'requisition_lines' not in context or ('requisition_lines' in context and context['requisition_lines'] and line.id in context['requisition_lines']):
#                    product = line.product_id
#                    seller_price, qty, default_uom_po_id, date_planned = self._seller_details(cr, uid, line, supplier, context=context)
#                    taxes_ids = product.supplier_taxes_id
#                    taxes = fiscal_position.map_tax(cr, uid, supplier.property_account_position, taxes_ids)
#                    purchase_order_line.create(cr, uid, {
#                        'order_id': purchase_id,
#                        'name': line.name,
#                        'product_qty': qty,
#                        'product_id': product.id,
#                        'product_uom': default_uom_po_id,
#                        'price_unit': seller_price,
#                        'date_planned': date_planned,
#                        'price_unit' : line.product_price_unit,
#                        'taxes_id': [(6, 0, taxes)],
#                        'requisition_line_id': line.id
#                    }, context=context)
#
#        return res

#    _defaults = {
#        'exclusive': 'multiple',
#    }


class purchase_requisition_line(osv.osv):

    _inherit = 'purchase.requisition.line'
    _rec_name = 'name'

    def _check_qty_and_unitprice(self, cr, uid, ids, context=None):
        for req_line in self.browse(cr, uid, ids, context=context):
            if req_line.product_qty < 0 or req_line.product_price_unit < 0:
                return False
        return True

    _columns = {
        'name': fields.text('Description', required=True),
        'purchase_responsible_id': fields.many2one('res.users', 'Purchase Responsible'),
        'product_price_unit': fields.float('Unit Price', digits=(16,4)),
        'state': fields.selection([('draft','Draft'),('done','Done'),('cancel','Cancelled')], 'Status'),
        'product_category_id': fields.many2one('product.category', 'Product Category'),
        'product_id': fields.many2one('product.product', 'product', domain=[('purchase_ok','=',True)]),
    }

    _defaults = {
        'state': 'draft',
    }
    _order = 'requisition_id desc,name'

    _constraints = [
         (_check_qty_and_unitprice, _(u'Qty/price must be more than 0'), ['product_qty', 'product_price_unit']),
    ]

    def onchange_product_id(self, cr, uid, ids, product_id, product_uom_id, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if context is None:
            context = {}
        value = {'product_uom_id': ''}
        if product_id:
            lang = self.pool.get('res.users').browse(cr, uid, uid).lang
            context.update({'lang': lang})
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            line_desc = "[" + prod.id + "] " + prod.name
            value = {'product_category_id':prod.categ_id.id, 'product_uom_id': prod.uom_id.id,'product_qty':1.0, 'name':line_desc, 'purchase_responsible_id':prod.categ_id.purchase_responsible_id and prod.categ_id.purchase_responsible_id.id or False, 'product_price_unit':prod.standard_price}
        return {'value': value}


    def create(self, cr, uid, vals, context=None):
        if 'product_id' in vals and vals['product_id'] and 'product_category_id' not in vals:
            product = self.pool.get('product.product').browse(cr, uid, vals['product_id'])
            vals['product_category_id'] = product.categ_id.id
        return super(purchase_requisition_line, self).create(cr, uid, vals, context=context)

purchase_requisition_line()


class purchase_requisition_line_partner(osv.osv_memory):
    _name = "purchase.requisition.line.partner"
    _description = "Purchase Requisition Line Partner"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier', required=True,domain=[('supplier', '=', True)]),
    }

    def create_order(self, cr, uid, ids, context=None):
        active_ids = context and context.get('active_ids', [])
        data =  self.browse(cr, uid, ids, context=context)[0]
        po_obj =  self.pool.get('purchase.order')
        porders = []
        preq =  []
        for line in self.pool.get('purchase.requisition.line').browse(cr, uid, active_ids):
            if line.state == 'draft':
                if line.requisition_id.id in preq:
                    context['skip_note'] = True
                else:
                    context['skip_note'] = False
                    preq.append(line.requisition_id.id)
                context['requisition_lines'] = [line.id]
                res = self.pool.get('purchase.requisition').make_purchase_order(cr, uid, [line.requisition_id.id], data.partner_id.id, context=context)
                porders.append(res[line.requisition_id.id])
        # Merge the orders
        merge_res = po_obj.do_merge(cr, uid, porders, context)    
        if not merge_res:
            poids = porders
            print "NOT MERGE RES:",merge_res
        else:
            poids = merge_res.keys()
            print "MERGE RES:",merge_res
        # Delete the old po's
        old_pos = po_obj.search(cr, uid, [('id','in',porders),('state','=','cancel')])
        po_obj.unlink(cr, uid, old_pos)    

#        return {'type': 'ir.actions.act_window_close'}
        mod_obj = self.pool.get('ir.model.data')
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'purchase_order_tree')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','purchase.order'),('name','=','purchase.order.tree')])

        return {'name': _('Purchase Orders'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'domain': [('id','in',poids)],
        }


purchase_requisition_line_partner()

class product_product(osv.osv):

    _inherit = 'product.product'

    _defaults = {
        'sale_ok': False,
        'type': 'service',
    }
    
    def _get_partner_code_name(self, cr, uid, ids, product, partner_id, context=None):
        for supinfo in product.seller_ids:
            if supinfo.name.id == partner_id:
                return {'code': supinfo.product_code or product.default_code, 'name': supinfo.product_name or product.name, 'variants': ''}
        res = {'code': str(product.id), 'name': product.name, 'variants': product.variants}
        return res
    
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        def _name_get(d):
            name = d.get('name','')
            code = d.get('id',False)
            if code:
                name = '[%s] %s' % (code,name)
            if d.get('variants'):
                name = name + ' - %s' % (d['variants'],)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        result = []
        for product in self.browse(cr, user, ids, context=context):
            sellers = partner_ids and filter(lambda x: x.name.id in partner_ids, product.seller_ids) or []
            if sellers:
                for s in sellers:
                    mydict = {
                              'id': product.id,
                              'name': s.product_name or product.name,
                              'default_code': s.product_code or product.default_code,
                              'variants': product.variants
                              }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                          'id': product.id,
                          'name': product.name,
                          'default_code': product.default_code,
                          'variants': product.variants
                          }
                result.append(_name_get(mydict))
        return result

class product_category(osv.osv):

    _inherit = 'product.category'

    _columns = {
        'purchase_responsible_id': fields.many2one('res.users', 'Purchase Responsible'),
    }
    
class account_invoice(osv.osv):
    
    _inherit = 'account.invoice'
    
    def view_origin_po(self, cr, uid, ids, context=None):
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','view.origin.po'),
                                                            ('name','=','view.origin.po.form')])

        invoice = self.browse(cr, uid, ids)[0]
        context['default_veld'] = invoice.number
        po_line_ids = []
        amount_total = []
        for inv_line in invoice.invoice_line:
            po_line_ids += [polines.id for polines in inv_line.purchase_order_line_ids]
	    amount_total += [polines.price_subtotal for polines in inv_line.purchase_order_line_ids]
        context['default_po_line_ids'] = po_line_ids
        context['default_amount_total'] = sum(amount_total)

# fill needed fields in context
        return {
            'type': 'ir.actions.act_window',
            'name': 'Brondocumenten',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id[0],
            'res_model': 'view.origin.po',
            'target': 'new',
            'context': context,
            }
        
# zie natuurpunt_bankstatement (create_partner)

class view_origin_po(osv.osv_memory):
    _name = "view.origin.po"
    
    _columns = {
        'veld': fields.char('Naam'),
        'po_line_ids': fields.many2many('purchase.order.line', 'purchase_order_line_invoice_rel', 'invoice_id', 'order_line_id', 'Purchase Order Lines', readonly=True),
        'amount_total': fields.float('Bestellijn totalen excl. BTW', readonly=True),
        }
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
