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

class purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def _search_approved_by_me(self, cr, uid, obj, name, args, context=None):
        line_obj = self.pool.get('purchase.approval.item.line')
        # get uid's approval lines
        line_ids = line_obj.search(cr, uid,[('actual_approver_id','=',uid),('approval_item_id','!=',False)], context=context)
        if not line_ids:
            return [('id', '=', '0')]
        else:
            item_ids = []
            for data in line_obj.read(cr, uid, line_ids, fields=['approval_item_id'], context=context):
                item_ids.append(data['approval_item_id'][0])
            if item_ids:
                item_obj = self.pool.get('purchase.approval.item')
                purchase_ids = []
                for data in item_obj.read(cr, uid, item_ids, fields=['purchase_order_id'], context=context):
                    # only invoices , not purchase orders
                    if data['purchase_order_id']:
                        purchase_ids.append(data['purchase_order_id'][0])
                return [('id', 'in', purchase_ids)]
            else:
                return [('id', '=', '0')]

    def _approved_by_me(self,cr,uid,ids,fieldnames,args,context=None):
        res={}
        return res

    _columns = {
        'approved_by_me':fields.function(
              _approved_by_me,
              fnct_search=_search_approved_by_me,
              method=True,
              type='boolean',
              string='Approved by me',
        ),
    }


purchase_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: