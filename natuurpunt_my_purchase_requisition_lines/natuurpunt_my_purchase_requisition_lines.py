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

class purchase_requisition_line(osv.osv):
    _inherit = 'purchase.requisition.line'

    def _search_purchase_requisition_by_me(self, cr, uid, obj, name, args, context=None):
        req_obj = self.pool.get('purchase.requisition')
        req_ids = req_obj.search(cr, uid,[('user_id','=',uid),('line_ids','!=',False)], context=context)
        if not req_ids:
            return [('id', '=', '0')]
        else:
            item_ids = []
            for data in req_obj.read(cr, uid, req_ids, fields=['line_ids'], context=context):
                for i in range(len(data['line_ids'])):
                    item_ids.append(data['line_ids'][i])
            if item_ids:
                return [('id', 'in', item_ids)]
            else:
                return [('id', '=', '0')]

    def _purchase_requisition_by_me(self,cr,uid,ids,fieldnames,args,context=None):
        res={}
        return res

    _columns = {
        'purchase_requisition_by_me':fields.function(
              _purchase_requisition_by_me,
              fnct_search=_search_purchase_requisition_by_me,
              method=True,
              type='boolean',
              string='Purchase requisition by me',
        ),
    }


purchase_requisition_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: