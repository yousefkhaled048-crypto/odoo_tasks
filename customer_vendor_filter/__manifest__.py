{
    'name': 'Customer and Vendor Filter',
    'version': '18.0.1.0.0',
    'author': 'Yousef',
    'summary': 'Show only customers or only vendors in the right partner fields',
    'category': 'Sales',
    'depends': ['account', 'purchase'],
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
    ],
    'application': False,
}