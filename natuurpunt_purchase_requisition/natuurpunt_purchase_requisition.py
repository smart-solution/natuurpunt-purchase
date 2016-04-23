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
from openerp import SUPERUSER_ID
import logging
from collections import defaultdict
from natuurpunt_tools import get_eth0

_logger = logging.getLogger('natuurpunt_purchase_requisition')

class purchase_requisition(osv.osv):
    _inherit = 'purchase.requisition'

    _columns = {
        'purchase_order_line_ids': fields.one2many('purchase.order.line', 'requisition_id', 'Purchase Order Lines'),
        'state': fields.selection([('draft','New'),('in_progress','In verwerking'),('cancel','Cancelled'),('done','Purchase Done')],
              'Status', track_visibility='onchange', required=True),
    }
    
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

    def send_purchase_requisition_reminders_email(self, cr, uid, user, msg_vals, context=None):
        """Send daily purchase requisition reminders via e-mail"""
        email_address = user.email_work
        if email_address:
            try:
                data_obj = self.pool.get('ir.model.data')
                template = data_obj.get_object(cr, uid, 'natuurpunt_purchase_requisition', 'email_template_purchase_requisition_reminder')
            except ValueError:
                raise osv.except_osv(_('Error!'),_("Cannot send email: no email template configured.\nYou can configure it under Settings/Technical/Email."))
            assert template._name == 'email.template'
            context['subject']   = msg_vals['subject']
            context['email_to']  = email_address
            context['body_html'] = msg_vals['body']
            context['res_id']    = False

            self.pool.get('email.template').send_mail(cr, uid, template.id, False, force_send=True, context=context)
            _logger.info('mail %s: %s', msg_vals['subject'], email_address)
            return True
        else:
            return True

    def generate_purchase_requisition_reminders(self, cr, uid, context=None):
        """Generate daily purchase requisition reminders"""
        line_obj = self.pool.get('purchase.requisition.line')
        msg_obj = self.pool.get('mail.message')

        # get draft purchase requisitions
        draft_prl = line_obj.search(cr, uid, [('state','=','draft'),])
        purchase_req_list = []
        for line in line_obj.browse(cr, uid, draft_prl):
            purchase_req_list.append((line.purchase_responsible_id,line.id))

        # group purchase requisition by user
        purchase_req_per_user = defaultdict(list)
        [purchase_req_per_user[k].append(v) for k, v in purchase_req_list]

        def get_detail_lines_html_body():
            base_url = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
            link = ("<b><a href='{}?db={}#view_type=list&model=purchase.requisition.line&menu_id=470'>{}</a></b> ")
            line = link.format(base_url, 
                               cr.dbname,
                               _('%s concept inkoopaanvraaglijn(en)<br>')%(len(purchase_requisition_list)))
            yield line

        html_body_end = "<span><p><p/>"+_('Send from host %s - db %s')%(get_eth0(),cr.dbname)+"</span>"

        for user,purchase_requisition_list in purchase_req_per_user.items():
            msg_vals = {'subject': _('Purchase Requisition Reminder'),
                        'body': ''.join(get_detail_lines_html_body()) + html_body_end,
                        'type': 'notification',
                        'notified_partner_ids': [(6,0,[user.partner_id.id])],
                    }
            msg_obj.create(cr, uid, msg_vals)
            self.send_purchase_requisition_reminders_email(cr, uid, user, msg_vals, context=context)

    def manually_generate_purchase_requisition_reminders(self, cr, uid, ids, context=None):
        self.generate_purchase_requisition_reminders(cr, uid, context=context)
        return True


purchase_requisition()

class purchase_requisition_line(osv.osv):

    _inherit = 'purchase.requisition.line'

    def write(self, cr, uid, ids, vals, context=None):
        """Change the status of the PR to In Progress when a line goes to status Done"""
        """or to Done when all lines are done"""
        if 'state' in vals and vals['state'] and vals['state'] == 'done':
            for req_line in self.browse(cr, uid, ids):
                if req_line.requisition_id.state in ('draft','in_progress'):

                    # Check if all lines are done, if yes close the PR
                    all_done = True
                    for line in req_line.requisition_id.line_ids:
                        if line.state == 'draft' and line.id not in ids:
                            all_done = False

                    # check if all purchase order are in status approved
                    # and all lines are done
                    if all_done:
                        for order in req_line.requisition_id.purchase_order_line_ids:
                            if order.order_id.state != 'approved':
                                all_done = False

                    if all_done:
                        self.pool.get('purchase.requisition').write(cr, uid, [req_line.requisition_id.id], {'state':'done'})
                    else:
                        self.pool.get('purchase.requisition').write(cr, uid, [req_line.requisition_id.id], {'state':'in_progress'})

        return super(purchase_requisition_line, self).write(cr, uid, ids, vals=vals, context=context)

class purchase_order(osv.osv):

    _inherit = 'purchase.order'

    def write(self, cr, uid, ids, vals, context=None):
        res = super(purchase_order, self).write(cr, uid, ids, vals, context=context)

        if 'state' in vals and vals['state'] == 'approved':
            for po in self.browse(cr, uid, ids):
                for poline in po.order_line:
                    if poline.requisition_line_id:
     
                        # Check if all po's from the purchase requisition are approved
                        all_done = True
                        
                        for reqline in poline.requisition_line_id.requisition_id.line_ids:
                            if reqline.state == 'draft':
                                all_done = False

                        for orderline in poline.requisition_line_id.requisition_id.purchase_order_line_ids:
                            if orderline.order_id.state != 'approved':
                                all_done = False

                        if all_done:
                            self.pool.get('purchase.requisition').write(cr, uid, [poline.requisition_line_id.requisition_id.id], {'state':'done'})

        return res 


class purchase_order_line(osv.osv):

    _inherit = 'purchase.order.line'

    _columns = {
        'purchase_resp_id': fields.many2one('res.users', 'Resp req', required=True),
    }

    def create(self, cr, uid, vals, context=None):
        if 'requisition_line_id' in vals and vals['requisition_line_id']:
            req_line = self.pool.get('purchase.requisition.line').browse(cr, uid, vals['requisition_line_id'])
            vals['purchase_resp_id'] = req_line.requisition_id.user_id.id
        return super(purchase_order_line, self).create(cr, uid, vals=vals, context=context)

    def redirect_to_purchase_order(self, cr, uid, ids, context=None):
        for pol in self.browse(cr,uid,ids,context=context):
            purchase_order_id = pol.order_id.id
        return {
                'name': _('Purchase Order'),
                'view_type': 'form,tree',
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'target': 'current',
                'context': context,
                'res_id': purchase_order_id,
                'type': 'ir.actions.act_window',    
                }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
