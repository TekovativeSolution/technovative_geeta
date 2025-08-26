{
    'name': 'Product Pricing Extension',
    'version': '17.0.1.0',
    'summary': 'Add pricing type, last purchase price, operational margin, and advanced quantity/customer pricing to products.',
    'description': """
Product Pricing Extension
=========================
- Adds **Pricelist tab** to Product Templates & Variants.
- Fields: Pricing Type, Last Purchase Price, Operational Margin (%), Landing Price (computed).
- Two extra pricing models:
    1. Quantity Based Pricing
    2. Customer Type Pricing
    """,
    'author': 'teknovative solution',
    'category': 'Product',
    'depends': ['product','contacts','sale','account'],
    'data': [
        'data/ir_module_category_data.xml',
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/res_partner_customer_type.xml',
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'wizard/price_lp_cus_wizard_views.xml',
        'wizard/price_lp_fixed_wizard_views.xml',
        'wizard/price_reg_cus_wizard_views.xml',
        'wizard/price_reg_fixed_wizard_views.xml',
        'wizard/price_lp_cus_pur_wizard_views.xml',
        'wizard/price_lp_pur_fixed_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
