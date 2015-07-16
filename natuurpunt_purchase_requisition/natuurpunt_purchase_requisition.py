# -*- coding: utf-8 -*-
##############################################################################
#
#    Natuurpunt VZW
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
from tools.translate import _

class purchase_requisition(osv.osv):
    _inherit = 'purchase.requisition'
    
    def uid_in_group_purchase_requisition_manager(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.model.data')
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_purchase_requisition_manager')], context=context)
        res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        pur_req_manager_group = self.pool.get('res.groups').browse(cr, uid, res_id)
        gp_users = [x.id for x in pur_req_manager_group.users]        
        return uid in gp_users
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        # override view domain, manager get to see everything = default
        if not(self.uid_in_group_purchase_requisition_manager(cr, uid, context)):
            args.append(['user_id', '=', uid])
        return super(purchase_requisition, self).search(cr, uid, args, offset, limit, order, context=context, count=count)    
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):        
        # override default search if manager                                   
        if view_type == 'search':
            if self.uid_in_group_purchase_requisition_manager(cr, uid, context):
                new_view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'purchase.requisition.list.select')])
            else:
                new_view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'np.purchase.requisition.list.select')])
            assert(len(new_view_id) == 1)
            view_id = new_view_id[0]
        return super(purchase_requisition,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)            

purchase_requisition()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: