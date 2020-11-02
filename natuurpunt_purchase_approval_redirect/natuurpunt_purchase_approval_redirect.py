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

        if context.get('approval',False):
            company_ids = [pai.invoice_id.company_id.id for pai in self.browse(cr,uid,ids)]
            domain = [
                ('invoice_id', '!=', False),
                ('state', '=', 'waiting'),
                '|',
                ('line_next_approver_id', '=', uid),
                '&',
                ('line_next_approver_id', '!=', False),
                ('line_next_approver_id.approval_substitute_id', '=', uid),
                ('invoice_id.company_id.id', 'in', company_ids),
            ]
            view_name = _('My Invoices to Approve')
        else:
            domain = [
                ('invoice_id', '!=', False),
                ('state', '=', 'waiting'),
            ]
            view_name = _('Invoices to Approve')          
        all_ids = self.search(cr,uid,domain)
        invoice_ids = [pai.invoice_id.id for pai in self.browse(cr,uid,all_ids)]

        for pai in self.browse(cr,uid,ids,context=context):
            invoice_id = pai.invoice_id.id
        context['redirect_id'] = invoice_id
        context.pop('group_by', None)
        return {
                'name': view_name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'target': 'current',
                'context': context,
                'type': 'ir.actions.act_window',
                'domain': [('id','in',invoice_ids)],
                }
        
    def redirect_to_purchase_order(self, cr, uid, ids, context=None):

        if context.get('approval',False):
            company_ids = [pai.purchase_order_id.company_id.id for pai in self.browse(cr,uid,ids)]
            domain = [
                ('purchase_order_id', '!=', False),
                ('state', '=', 'waiting'),
                '|',
                ('line_next_approver_id', '=', uid),
                '&',
                ('line_next_approver_id', '!=', False),
                ('line_next_approver_id.approval_substitute_id.id', '=', uid),
                ('purchase_order_id.company_id.id', 'in', company_ids),
            ]
            view_name = _('My Purchases to Approve'),
        else:
            domain = [
                ('purchase_order_id', '!=', False),
                ('state', '=', 'waiting'),
            ]
            view_name = _('Purchases to Approve'),
        all_ids = self.search(cr,uid,domain)
        purchase_order_ids = [pai.purchase_order_id.id for pai in self.browse(cr,uid,all_ids)]

        for pai in self.browse(cr,uid,ids,context=context):
            purchase_order_id = pai.purchase_order_id.id
        context['redirect_id'] = purchase_order_id
        context.pop('group_by', None)
        return {
                'name': view_name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'target': 'current',
                'context': context,
                'type': 'ir.actions.act_window',
                'domain': [('id','in',purchase_order_ids)],
                }

purchase_approval_item()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
