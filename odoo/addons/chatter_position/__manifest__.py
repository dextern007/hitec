# -*- coding: utf-8 -*-
{
    "name": "Chatter Position Adjustment",
    "summary": "Chatter Position Adjustment",
    "version": "1.0",
    'author': "All About IT",
    'website': "https://www.aaitpro.com",
    'license': "LGPL-3",
    "category": "Extra Tools",
    'images': [],
    'support': 'info@aaitpro.com',
    "depends": ["web", "mail"],
    "data": [
        "views/res_users.xml",
        "views/web.xml",
        "views/assets.xml",
    ],
    'qweb': [
        'static/src/xml/form_buttons.xml',
    ],
    'installable': True,
    'auto_install': False,
}
