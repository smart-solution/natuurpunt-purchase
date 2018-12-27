# -*- coding: utf-8 -*-
##############################################################################
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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def redirect_to_purchase_order(self, cr, uid, ids, context=None):
        domain = [('partner_id','=','$PARTNER_ID'),('invoiced','=',False),('state','not in',['draft', 'cancel'])]
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name','=','Supplier Purchase Order Lines')])
        return {
            'domain': domain,
            'name': _('orderlijnen'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'purchase.order.line',
            'target': 'current',
            'context': context,
            'view_id': view_id[0],
            'type': 'ir.actions.act_window',
        }

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
                 date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False, context=None):

        result = super(account_invoice,self).onchange_partner_id(cr, uid, ids, type, partner_id,\
                 date_invoice, payment_term, partner_bank_id, company_id)
        if (partner_id and type == 'in_invoice'):
            domain = [('partner_id','=',partner_id),('invoiced','=',False),('state','not in',['draft', 'cancel'])]
            count_pol = self.pool.get('purchase.order.line').search_count(cr, uid, domain)
            if count_pol:
                warning = {
                    'title':'openstaande aankooplijnen!',
                    'message':'{} openstaande aankooplijnen voor partner {}'.format(count_pol, partner_id),
                }
                result['warning'] = warning

        return result

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
