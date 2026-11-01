# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Purchase requests with automatic RFQ generation per vendor',
    'description': """
Purchase Request
================
Lets users create purchase requests and, on confirmation, automatically
generates one draft RFQ per vendor, grouping all lines of the same vendor
into a single purchase order. Every generated RFQ is linked back to its
original request through a smart button on both documents.
""",
    'author': 'Your Company',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_request_sequence.xml',
        'views/purchase_request_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}