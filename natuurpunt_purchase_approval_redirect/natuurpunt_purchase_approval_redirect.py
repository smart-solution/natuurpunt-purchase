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

    def redirect_to_invoice(self, cr, uid, ids, context=None):
        for pai in self.browse(cr,uid,ids,context=context):
            invoice_id = pai.invoice_id.id
        return {
                'name': _('My Invoices to Approve'),
                'view_type': 'form,tree',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'target': 'current',
                'context': context,
                'res_id': invoice_id,
                'type': 'ir.actions.act_window',
                }
        
    def redirect_to_purchase_order(self, cr, uid, ids, context=None):
        for pai in self.browse(cr,uid,ids,context=context):
            purchase_order_id = pai.purchase_order_id.id
        return {
                'name': _('My Purchases to Approve'),
                'view_type': 'form,tree',
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'target': 'current',
                'context': context,
                'res_id': purchase_order_id,
                'type': 'ir.actions.act_window',                
                }

purchase_approval_item()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: