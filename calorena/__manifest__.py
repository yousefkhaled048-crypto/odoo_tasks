{
    'name': 'Calorena',
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'author': 'Yousef',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
    ],
    'data': [
        'report/invoice_report.xml',
        'report/invoice_report_template.xml',
        'views/sale_order_line_views.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'calorena/static/src/css/invoice_report.css',
        ],
    },
    'installable': True,
    'application': False,
}