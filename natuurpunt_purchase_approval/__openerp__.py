# -*- coding: utf-8 -*-
{
    'name': 'natuurpunt_purchase_approval',
    'version': '1.0',
    'category': 'Purchase Management',
    'description': 'Allows complex multilevel approvals on purchase orders and invoices, based on 2-dimensional analytical accounts.',
    'author': 'Smart Solution (fabian.semal@smartsolution.be)',
    'website': 'http://www.smartsolution.be',
    'depends': [
        'purchase',
        'analytic',
        'multi_analytical_account',
        'natuurpunt_membership',
    ],
    'data': [
        'security/res.groups.csv',
        'security/ir.model.access.csv',
        'security/purchase_approver/right/ir.model.access.csv',
        'security/purchase_approver/rule/purchase_approval_item.xml',
        'security/invoice_approver/right/ir.model.access.csv',
        'security/invoice_approver/rule/invoice_approval_item.xml',
        'view/purchase.xml',
        'view/dimension.xml',
        'view/invoice.xml',
        'view/user.xml',
        'view/approval.xml',
        'workflow/purchase.xml',
    ],
    'installable': True,
    'active': False,
}

