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

    _columns = {
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
    }
purchase_requisition_line()

class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'

    _columns = {
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
    }
purchase_order_line()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: