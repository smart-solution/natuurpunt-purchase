# -*- coding: utf-8 -*-
from openerp.osv import fields, orm
from openerp.tools.translate import _

class purchase_order_line(orm.Model):

    _inherit = "purchase.order.line"

    def _function_delivery_balance(self, cr, uid, ids, name, arg, context=None):
        res = {}
        return res

    def _search_delivery_balance(self, cr, uid, obj, name, args, context=None):
        if context is None:
            context = {}
        if not args:
            return []
        cr.execute('SELECT id FROM purchase_order_line where product_qty > delivery_quantity')
        res = cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    _columns = {
        'delivery_balance': fields.function(
            _function_delivery_balance,
            fnct_search=_search_delivery_balance,
            type='boolean',
            string='delivery_balance'),
    }
