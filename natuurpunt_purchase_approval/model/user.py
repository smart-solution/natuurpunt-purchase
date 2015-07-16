from openerp.osv import fields, osv

class user(osv.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    _columns = {
        # new columns
        'purchase_approval_level_id': fields.many2one('purchase.approval.level', 'Purchase Approval Level'),
        'approval_substitute_id': fields.many2one('res.users', 'Approval Substitute',
            help="Backup approver for this user and this user's level."),
        'notification_email':fields.boolean('Items to approve notification email', 
            help="When items to approve, system will send a notification email"),
    }

    def __init__(self, pool, cr):
        res = super(user, self).__init__(pool, cr)
        #self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append('approval_substitute_id')
        #self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append('approval_substitute_id')
        return res

    def manually_generate_purchase_approval_reminders(self, cr, uid, ids, context=None):
	wizard_id = self.pool.get("purchase.approval.reminder")
        wizard_id.generate_purchase_approval_reminders(cr, uid, context)
	return True
