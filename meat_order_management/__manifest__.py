{
    'name': 'Meat Order Management',
    'summary': 'Manage meat orders through Sales Quotations',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'author': 'Yousef',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
    ],
    'data': [
        'views/sale_order_views.xml',
        'report/invoice_report.xml',
        'report/invoice_report_template.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'meat_order_management/static/src/css/meat_invoice.css',
        ],
    },
    'installable': True,
    'application': False,
}
