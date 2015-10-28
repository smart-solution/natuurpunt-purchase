# -*- encoding: utf-8 -*-

from mx import DateTime
import time

from openerp.osv import fields, osv
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.osv.orm import browse_record, browse_null


class purchase_order_attachment_wizard(osv.osv_memory):

    _name = 'purchase.order.attachment.wizard'

    _columns = {
        'file_data' : fields.binary('File', required=True), 
        'file_name' : fields.char('Filename', size=128, required=True), 
    }

    def file_attach(self, cr, uid, ids, context=None):
        """Attach the file to the purchase order"""
        attach_obj = self.pool.get('ir.attachment')
        wizard = self.browse(cr, uid, ids[0])

        vals = {
            'name': wizard.file_name,
            'datas_fname': wizard.file_name,
            'datas': wizard.file_data,
            'res_model': 'purchase.order',
            'res_id': context['active_id']
        }

        attach_obj.create(cr, uid, vals, context=context)

        return True

class purchase_requisition(osv.osv):

    _inherit = 'purchase.requisition'

    _columns = {
        'purchase_order_line_ids': fields.one2many('purchase.order.line', 'requisition_id', 'Purchase Lines'),
    }

#    def copy(self, cr, uid, id, default=None, context=None):
#        """Do not copy purchase order line"""
#        if default == None:
#            default= {}
#        default['purchase_line_ids'] = []
#        default.update({'purchase_line_ids': []})
#        default['history'] = """In case of selection ‘multiple’ and in the case of a purchase requisition line being closed by confirming a quotation, the purchase requisition line was removed from following other pending quotations:\nProduct - description - PO - [partner reference] partner - number of units - unit of measure - unit price"""
#        return super(purchase_requisition, self).copy(cr, uid, id, default=default, context=context)
#
#    def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
#        """
#        Create New RFQ for Supplier
#        """
#        print "In make purchase order"
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
#                raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
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
#                        'taxes_id': [(6, 0, taxes)],
#                        'requisition_id':requisition.id,
#                        'requisition_line_id': line.id,
#                        'analytic_dimension_1_id': line.analytic_dimension_1_id.id,
#                        'analytic_dimension_2_id': line.analytic_dimension_2_id.id,
#                        'analytic_dimension_3_id': line.analytic_dimension_3_id.id,
#                        'analytic_dimension_1_required': line.analytic_dimension_1_required,
#                        'analytic_dimension_2_required': line.analytic_dimension_2_required,
#                        'analytic_dimension_3_required': line.analytic_dimension_3_required,
#                    }, context=context)
#
#        return res
#
#
#    def create(self, cr, uid, vals, context=None):
#        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'purchase.order.requisition')
#        return super(purchase_requisition, self).create(cr, uid, vals, context=context)
#
#    _defaults = {
#        'name': '/',
#        'exclusive': 'exclusive',
#        'history': """In case of selection ‘multiple’ and in the case of a purchase requisition line being closed by confirming a quotation, the purchase requisition line was removed from following other pending quotations:\nProduct - description - PO - [partner reference] partner - number of units - unit of measure - unit price"""
#    }
#    
#purchase_requisition()
#
#
#class purchase_order(osv.osv):
#    _inherit = "purchase.order"
#    
#    def do_merge(self, cr, uid, ids, context=None):
#        """
#        To merge similar type of purchase orders.
#        Orders will only be merged if:
#        * Purchase Orders are in draft
#        * Purchase Orders belong to the same partner
#        * Purchase Orders are have same stock location, same pricelist
#        Lines will only be merged if:
#        * Order lines are exactly the same except for the quantity and unit
#
#         @param self: The object pointer.
#         @param cr: A database cursor
#         @param uid: ID of the user currently logged in
#         @param ids: the ID or list of IDs
#         @param context: A standard dictionary
#
#         @return: new purchase order id
#
#        """
#        print "In do Merge"
#        #TOFIX: merged order line should be unlink
#        wf_service = netsvc.LocalService("workflow")
#        def make_key(br, fields):
#            list_key = []
#            for field in fields:
#                field_val = getattr(br, field)
#                if field in ('product_id', 'move_dest_id', 'account_analytic_id'):
#                    if not field_val:
#                        field_val = False
#                if isinstance(field_val, browse_record):
#                    field_val = field_val.id
#                elif isinstance(field_val, browse_null):
#                    field_val = False
#                elif isinstance(field_val, list):
#                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
#                list_key.append((field, field_val))
#            list_key.sort()
#            return tuple(list_key)
#
#        # Compute what the new orders should contain
#
#        new_orders = {}
#
#        for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'draft']:
#            order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id'))
#            new_order = new_orders.setdefault(order_key, ({}, []))
#            new_order[1].append(porder.id)
#            order_infos = new_order[0]
#            if not order_infos:
#                order_infos.update({
#                    'origin': porder.origin,
#                    'date_order': porder.date_order,
#                    'partner_id': porder.partner_id.id,
#                    'dest_address_id': porder.dest_address_id.id,
#                    'warehouse_id': porder.warehouse_id.id,
#                    'location_id': porder.location_id.id,
#                    'pricelist_id': porder.pricelist_id.id,
#                    'state': 'draft',
#                    'order_line': {},
#                    'notes': '%s' % (porder.notes or '',),
#                    'fiscal_position': porder.fiscal_position and porder.fiscal_position.id or False,
#                })
#            else:
#                if porder.date_order < order_infos['date_order']:
#                    order_infos['date_order'] = porder.date_order
#                if porder.notes:
#                    order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
#                if porder.origin:
#                    order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin
#
#            for order_line in porder.order_line:
#                line_key = make_key(order_line, ('name', 'requisition_id', 'requisition_line_id', 'date_planned', 'taxes_id', 'price_unit', 'product_id', 'move_dest_id', 'account_analytic_id'))
#                o_line = order_infos['order_line'].setdefault(line_key, {})
#                if o_line:
#                    # merge the line with an existing line
#                    o_line['product_qty'] += order_line.product_qty * order_line.product_uom.factor / o_line['uom_factor']
#                else:
#                    # append a new "standalone" line
#                    for field in ('product_qty', 'product_uom'):
#                        field_val = getattr(order_line, field)
#                        if isinstance(field_val, browse_record):
#                            field_val = field_val.id
#                        o_line[field] = field_val
#                    o_line['uom_factor'] = order_line.product_uom and order_line.product_uom.factor or 1.0
#
#        allorders = []
#        orders_info = {}
#        for order_key, (order_data, old_ids) in new_orders.iteritems():
#            # skip merges with only one order
#            if len(old_ids) < 2:
#                allorders += (old_ids or [])
#                continue
#
#            # cleanup order line data
#            for key, value in order_data['order_line'].iteritems():
#                del value['uom_factor']
#                value.update(dict(key))
#            order_data['order_line'] = [(0, 0, value) for value in order_data['order_line'].itervalues()]
#
#            # create the new order
#            neworder_id = self.create(cr, uid, order_data)
#            orders_info.update({neworder_id: old_ids})
#            allorders.append(neworder_id)
#
#            # make triggers pointing to the old orders point to the new order
#            po_obj = self.pool.get('purchase.order')
#            pol_obj = self.pool.get('purchase.order.line')
#            for old_id in old_ids:
#                wf_service.trg_redirect(uid, 'purchase.order', old_id, neworder_id, cr)
#                wf_service.trg_validate(uid, 'purchase.order', old_id, 'purchase_cancel', cr)
#                old_po = po_obj.browse(cr, uid, old_id)
#                for old_po_line in old_po.order_line:
#                    pol_obj.write(cr, uid, old_po_line.id, {'requisition_id':False})
#        print "ORDERINFO:",orders_info        
#        return orders_info
#
#    def wkf_confirm_order(self, cr, uid, ids, context=None):
#        print "wkf_confirm_order"
#        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)
#        po_obj = self.pool.get('purchase.order')
#        pr_obj = self.pool.get('purchase.requisition')
#        pol_obj = self.pool.get('purchase.order.line')
#        prl_obj = self.pool.get('purchase.requisition.line')
#        for po in self.browse(cr, uid, ids, context=context):
#            for line in po.order_line:
#                if line.requisition_id and (line.requisition_id.exclusive=='exclusive'):
#                    #Set the prl state at done
#                    print "Confirm order"
#                    prl_obj.write(cr, uid, [line.requisition_line_id.id], {'state':'done'})
#
#                if line.requisition_id and (line.requisition_id.exclusive=='multiple'):
#
#                    # Find other pol from the same requisition line
#                    pol_ids = pol_obj.search(cr, uid, [('requisition_line_id', '=', line.requisition_line_id.id)])
#                    print "pol_ids:",pol_ids
#                    for pol in pol_obj.browse(cr, uid, pol_ids, context=context):
#                        print "POL: ", pol.order_id.id, pol.order_id.name
#                        #Delete only lines from other po
#                        if pol.order_id.id != po.id and pol.order_id.state != 'cancel':
#                            print "found a line to delete: ", [pol.id], [pol.name]
#                            #SAve history of th deleted line in the pr
#                            pr = pr_obj.browse(cr, uid, line.requisition_id.id)
#                            del_log = '\n' + 'Deleted quotation line: %s - %s - %s - [%s] %s - %s - %s - %s - %s'%(pol.product_id.default_code, pol.name, pol.order_id.name, pol.order_id.partner_id.ref, pol.order_id.partner_id.name, pol.product_qty, pol.product_uom.name, pol.price_unit, pol.order_id.default_po_currency.name)
#                            history = pr.history
#                            history += del_log
#                            pr_obj.write(cr, uid, [pr.id], {'history':history})
#
#                            #Delete the po line
#                            print "Deleting po line"
#                            order_lines = []
#                            for oline in pol.order_id.order_line:
#                                order_lines.append(oline.id)
#                            pol_obj.unlink(cr, uid, [pol.id])
#                            order_lines.remove(pol.id)
#
#                            #If the po has no more line, delete the po
#                            print "ORDLINE:",order_lines
#                            #if not(order.order_line):
#                            if not(order_lines):
#                                print "deleting po"
#                                po_obj.unlink(cr, uid, [pol.order_id.id])
#
#                    #Set the prl status as done if all pol are done
#                    pol_ids = pol_obj.search(cr, uid, [('requisition_line_id', '=', line.requisition_line_id.id)])
#                    prl_done = True
#                    for pol in pol_obj.browse(cr, uid, pol_ids, context=context):
#                        if pol.po_state == 'draft':
#                            prl_done = False
#                    if prl_done:
#                        prl_obj.write(cr, uid, [line.requisition_line_id.id], {'state':'done'})
#
#                    #if all prl are done, the pr is done too
#                    prl_ids = prl_obj.search(cr, uid, [('state','!=','done'),('requisition_id','=',line.requisition_id.id)])
#                    #prl_ids = prl_obj.search(cr, uid, [('requisition_id','=',line.requisition_id.id)])
#                    for prl in prl_obj.browse(cr, uid, prl_ids):
#                        print "PRL: %s %s"%(prl.state,prl.product_id.name)
#                    if not prl_ids:
#                        print "Closing tender"
#                        line.requisition_id.tender_done(context=context)
#        return res
#    
#purchase_order()

