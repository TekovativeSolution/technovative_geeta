# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PriceLpCusWizard(models.TransientModel):
    _name = 'price.lp.cus.wizard'
    _description = 'Price LP Customer Wizard'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    qty_price_ids = fields.One2many('price.details.wizard.lp.customer', 'wizard_id', string="Quantity Pricing")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_id = self.env.context.get("default_product_id")
        if product_id:
            product = self.env['product.product'].browse(product_id)
            cust_lines = []
            for c in product.customer_lp_pricing_ids:
                cust_lines.append((0, 0, {
                    'customer_type_id': c.customer_type_id.id,
                    'margin_per': c.margin_per,
                    'amount': c.amount,
                    'margin': c.margin,
                }))
            res['qty_price_ids'] = cust_lines
        return res



class PriceDetailsWizardlpCustomer(models.TransientModel):
    _name = 'price.details.wizard.lp.customer'
    _description = 'Wizard Customer Pricing'

    wizard_id = fields.Many2one('price.lp.cus.wizard', ondelete="cascade")
    customer_type_id = fields.Many2one('res.partner.customer.type')
    margin_per = fields.Float()
    amount = fields.Float()
    margin = fields.Float()






