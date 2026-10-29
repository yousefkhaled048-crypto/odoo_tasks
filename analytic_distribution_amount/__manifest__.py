# -*- coding: utf-8 -*-
{
    'name': 'Sale Analytic Distribution by Fixed Amount',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Enter the analytic distribution of sale order lines with fixed amounts',
    'description': """
Sale Analytic Distribution by Fixed Amount
==========================================
- A [% | Amount] toggle inside the analytic distribution popup switches between
  percentage entry and fixed amount entry (per user, remembered across records).
- In Amount mode each line shows an editable fixed amount based on the untaxed
  subtotal of the sale order line, with the resulting percentage as a hint.
- The amounts entered are stored in a new field 'analytic_distribution_amount'
  on sale.order.line, kept in sync with the percentages of
  'analytic_distribution' (the percentages remain the source of truth used by
  Odoo when posting analytic entries).
- A footer shows the subtotal basis and the distributed amount while editing.
""",
    'author': 'Yousef',
    'depends': ['sale', 'account', 'purchase', 'hr_expense'],
        'data': [
            'views/sale_order_views.xml',
            'views/account_move_views.xml',
            'views/purchase_order_views.xml',
            'views/hr_expense_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'analytic_distribution_amount/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}