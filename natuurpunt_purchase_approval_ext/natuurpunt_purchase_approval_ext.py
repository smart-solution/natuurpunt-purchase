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

from osv import osv, fields
from openerp.tools.translate import _
import logging
import socket
import fcntl
import struct
from openerp import SUPERUSER_ID
from natuurpunt_tools import get_eth0

_logger = logging.getLogger('natuurpunt_purchase_approval_ext')

class purchase_approval_reminder(osv.osv_memory):

    _name = 'purchase.approval.reminder'

    def send_purchase_approval_reminders_email(self, cr, uid, user, msg_vals, context=None):
        """Send daily purchase approval reminders via e-mail"""

        if user.email_work and user.notification_email:
            try:
                data_obj = self.pool.get('ir.model.data')           
                template = data_obj.get_object(cr, uid, 'natuurpunt_purchase_approval_ext', 'email_template_purchase_approval_reminder')
            except ValueError:
                raise osv.except_osv(_('Error!'),_("Cannot send email: no email template configured.\nYou can configure it under Settings/Technical/Email."))
            assert template._name == 'email.template'
            context['subject']   = msg_vals['subject']
            context['email_to']  = "joeri.Belis@natuurpunt.be" #user.email_work
            context['body_html'] = msg_vals['body']
            context['body']      = msg_vals['body']
            context['res_id']    = False
            
            self.pool.get('email.template').send_mail(cr, uid, template.id, False, force_send=True, context=context)
            _logger.info('mail %s: %s', msg_vals['subject'], user.email_work)
            return True
        else:
            return True
 
    def generate_purchase_approval_reminders(self, cr, uid, context=None):
        """Generates daily purchase approval reminders"""
        if context == None:
            context = {}

        msg_obj = self.pool.get('mail.message')
        item_obj = self.pool.get('purchase.approval.item')
        user_obj = self.pool.get('res.users')

        # we need to check all users because invoice to complete is possible for everybody
        users = user_obj.search(cr, uid, [])

        html_body_end = "<span><p><p/>"+_('Send from host %s - db %s')%(get_eth0(),cr.dbname)+"</span>"
        link = "<b><a href='{}?db={}#view_type=list&model={}&menu_id={}'>{}</a></b>"
        base_url = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')

        companies = self.pool.get('res.company').search(cr, uid, [])
        for user in user_obj.browse(cr, uid, users):

            domain_filter = [('state','=','waiting'),
                             '|',('line_next_approver_id','=',user.id),
                             '&',('line_next_approver_id','!=',False),
                                 ('line_next_approver_id.approval_substitute_id','=',user.id)]

            for company in self.pool.get('res.company').browse(cr, uid, companies):

                po_items = []
                inv_items = []
                inv_comp = []

                items = item_obj.search(cr, uid, domain_filter)

                # Find the PO and Invoices waiting approval
                for item in item_obj.browse(cr, uid, items):
                    if item.purchase_order_id and item.company_id.id == company.id:
                        po_items.append(item.purchase_order_id.id)
                    elif item.invoice_id and item.company_id.id == company.id: 
                        inv_items.append(item.invoice_id.id)

                # Find the invoices to comlete
                inv_comp = self.pool.get('account.invoice').search(cr, uid, [('dimension_user_id','=',user.id),('company_id','=',company.id)])

                context.update({'lang': user.lang})

                if po_items:
                    po_items_link = link.format(base_url,cr.dbname,'purchase.approval.item',728,_('Purchase Orders waiting approval'))
                    body = _("You have {0} {1} for company {2}").format(len(po_items),po_items_link,company.name)
                    msg_vals = {
                        'subject': _("Purchase Approval Reminder"),
                        'body': body + html_body_end,
                        'type': 'notification',
                        'notified_partner_ids': [(6,0,[user.partner_id.id])],
                    }
                    msg_obj.create(cr, uid, msg_vals)
                    self.send_purchase_approval_reminders_email(cr, uid, user, msg_vals, context=context)

                if inv_items:
                    inv_items_link = link.format(base_url,cr.dbname,'purchase.approval.item',729,_('Invoices waiting approval'))
                    body = _("You have {0} {1} for company {2}").format(len(inv_items),inv_items_link,company.name)
                    msg_vals = {
                        'subject': _("Invoice Approval Reminder"),
                        'body': body + html_body_end,
                        'type': 'notification',
                        'notified_partner_ids': [(6,0,[user.partner_id.id])],
                    }
                    msg_obj.create(cr, uid, msg_vals)
                    self.send_purchase_approval_reminders_email(cr, uid, user, msg_vals, context=context)

                if inv_comp:
                    inv_comp_link = link.format(base_url,cr.dbname,'account.invoice',526,_('Invoices to complete'))
                    body = _("You have {0} {1} for company {2}").format(len(inv_comp),inv_comp_link,company.name)
                    msg_vals = {
                        'subject': _("Invoice to Complete Reminder"),
                        'body': body + html_body_end,
                        'type': 'notification',
                        'notified_partner_ids': [(6,0,[user.partner_id.id])],
                    }
                    msg_obj.create(cr, uid, msg_vals)
                    self.send_purchase_approval_reminders_email(cr, uid, user, msg_vals, context=context)


        return True

class account_invoice_line(osv.osv):

    _inherit = "account.invoice.line"

    def _delivery_status_get(self, cr, uid, ids, name, args, context=None):
        """Get the delivery status from the po line"""
        res = {}
        for line in self.browse(cr, uid, ids, context):
            if line.purchase_order_line_ids: 
                res[line.id] = line.purchase_order_line_ids[0].delivery_state
            else:
                res[line.id] = "/"
        return res 

    _columns = {
        'po_delivery_status': fields.function(_delivery_status_get, method=True, string='Delivery Status', type="char", readonly=True, store=False),
    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
