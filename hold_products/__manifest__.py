{
    'name': 'Hold Products',
    'version': '18.0.1.0.0',
    'summary': 'Hold stock quantities and block Sale Orders from selling held quantities',
    'category': 'Sales',
    'depends': ['sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/hold_sequence_views.xml',
    ],
    'application': False,
}