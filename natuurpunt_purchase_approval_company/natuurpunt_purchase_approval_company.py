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

class purchase_approval_item(osv.osv):
    _inherit = 'purchase.approval.item'
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        # Get the company
        company = self.pool.get('res.users').browse(cr, uid, uid, context).company_id
        company_id = company.id
        set_company = lambda x: ['company_id', '=', company_id] if x == ['company_id', '=', 0] else x
        new_args = list(map(set_company,args)) 
        return super(purchase_approval_item, self).search(cr, uid, new_args, offset, limit, order, context=context, count=count)
              
purchase_approval_item()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: