{
    'name': 'Product UoM Barcode',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Multiple product barcodes linked to different UoMs',

    'description': """
        Manage multiple barcodes for the same product.
        Each additional barcode is linked to a specific Unit of Measure.
        Support barcode scanning inside Sales Orders.
    """,

    'author': 'Your Company',
    'license': 'LGPL-3',

    'depends': [
        'product',
        'sale_management',
    ],

    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
    ],

    'installable': True,
    'application': False,
}
