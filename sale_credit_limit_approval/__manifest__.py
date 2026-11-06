{
    'name': "Sales Credit Limit Approval",
    'version': '19.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Customer credit limits with a two-step Sales Order approval workflow",
    'description': """
Credit Limit & Two-Phase Sales Order Approval
=============================================
* Credit limit per partner (customers and vendors), defined on the contact.
* Credit used = residual of posted customer invoices and credit notes only
  (partial payments, credit notes, multi-currency and multi-company aware).
* Credit banner on the Sales Order (green within limit, red when exceeded).
* Approval workflow: Draft -> Waiting for Approval 1 -> Waiting for Approval 2
  -> Approved (plus Rejected / Cancelled), enforced on the backend.
* Changing a partner's credit limit restarts pending approvals at
  Waiting for Approval 1.
""",
    'depends': ['sale', 'account'],
    'data': [
        'security/credit_limit_security.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
