from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class account_analytic_dimension(osv.Model):
    _name = 'account.analytic.dimension'
    _inherit = 'account.analytic.dimension'

    _columns = {
        'is_active_for_approval': fields.boolean('Is active for approval?', help="If checked, then at least one level must be defined."),
        'unrestricted_amount': fields.float('Unrestricted amount', help="Maximum amount without approval.", digits_compute=dp.get_precision('Account')),
        'level_ids': fields.one2many('account.analytic.dimension.level', 'dimension_id', 'Levels'),
        'tolerance_absolute': fields.float('Tolerance (absolute)', digits_compute=dp.get_precision('Account'),
            help="If ('invoice approval item amount' - 'po approval item amount') > tolerance, then (partial) invoice needs extra approval."),
        'tolerance_percent': fields.float('Tolerance (%)', digits_compute=dp.get_precision('Account'),
            help="If ('invoice approval item amount' / 'po approval item amount') > (1 + tolerance/100), then (partial) invoice needs extra approval."),
    }

    def _check_level_ids_non_empty_if_active_for_approval(self, cr, uid, ids, context=None):
        for dimension in self.browse(cr, uid, ids, context=context):
            if dimension.is_active_for_approval and not dimension.level_ids:
                return False
        return True

    _constraints = [
        (_check_level_ids_non_empty_if_active_for_approval,
            "At least one level is required to activate this dimension for approval.",
            ['is_active_for_approval', 'level_ids']),
    ]

class purchase_approval_level(osv.Model):
    """This model defines the name of purchase approval levels globally (not specific by company)."""

    _name = 'purchase.approval.level'
    _order = 'name'

    _columns = {
        'name': fields.char('Name', size=32, required=True),
    }

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'There is already a level with this name.'),
    ]

class account_analytic_dimension_level(osv.Model):
    _name = 'account.analytic.dimension.level'
    _order = 'amount'

    _columns = {
        'dimension_id': fields.many2one('account.analytic.dimension', 'Dimension', required=True),
        'company_id': fields.related('dimension_id', 'company_id', type='many2one', relation='res.company', string="Dimension's company", store=True),
        'level_id': fields.many2one('purchase.approval.level', 'Level', required=True),
        'name': fields.related('level_id', 'name', type='char', size=32, string='Name'),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True),
        # FIXME: domain does not work at line creation time
        # FIXME: fallback is required
        'fallback_approver_id': fields.many2one('res.users', 'Fallback Approver', domain="[('company_id', 'child_of', company_id)]"),
        'active': fields.boolean('Active'),
    }

    _sql_constraints = [
        ('unique_dimension_name', 'unique(dimension_id, level_id)', 'There is already a level with this name for this analytical dimension.'),
        ('unique_dimension_amount', 'unique(dimension_id, amount)', 'There is already a level with this amount for this analytical dimension.'),
    ]

    _defaults = {
        'active': True,
    }

    # TODO: add constraint so that (name, amount) tuples are sorted -> avoid (level_1, 10000), (level_2 50)

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for level in self.read(cr, uid, ids, ['name', 'amount'], context=context):
            value = '%s: %s' % (level['name'], level['amount'])
            res.append((level['id'], value))
        return res

