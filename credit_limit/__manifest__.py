{
    'name': 'Partner Credit Limit',
    'version': '19.0.1.0.0',
    'summary': 'Customer Credit Limit and Due Amount on the partner form',
    'depends': ['base', 'account', 'sale'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}