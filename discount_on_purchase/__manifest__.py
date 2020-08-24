# -*- coding: utf-8 -*-
{
    'name': "Discount on Purchase",

    'summary': """
        This module used to handle discount in purchase order and vendor bill in two type: In percent or 
         amount and handle multi currency""",

    'description': """
        This module used to handle discount in purchase order and vendor bill in two type: In percent or 
         amount and handle multi currency 
    """,

    'author': "Genesis Technology",
    'website': "",
    # 'images': ['static/description'],
    'category': 'Purchase Management',
    'version': '13.0.1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'purchase','account'],

    'data': [
        'views/res_config_settings_views.xml',
        'views/purchase_order.xml',
        'views/account_invoice.xml',
        'report/report.xml',

    ],
    'images': ['static/description/images.jpeg'],
    'price': 35,
    'currency': 'USD',
    'support': 'genesistechnologyit@gmail.com',

}
