# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PriceLpfixedWizard(models.Model):
    _name = 'price.lp.fixed.wizard'
    _description = 'Price LP Fixed Wizard'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    qty_price_ids = fields.One2many('price.wizard.lp.fixed', 'wizard_id', string="Quantity Pricing")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_id = self.env.context.get("default_product_id")
        if product_id:
            product = self.env['product.product'].browse(product_id)
            qty_lines = []
            for q in product.qty_lp_pricing_ids:
                qty_lines.append((0, 0, {
                    'min_qty': q.min_qty,
                    'max_qty': q.max_qty,
                    'margin_per': q.margin_per,
                    'amount': q.amount,
                }))
            res['qty_price_ids'] = qty_lines
        return res

class PriceWizardlpFixed(models.TransientModel):
    _name = 'price.wizard.lp.fixed'
    _description = 'Wizard Fixed Pricing'

    wizard_id = fields.Many2one('price.lp.fixed.wizard', ondelete="cascade")
    min_qty = fields.Float()
    max_qty = fields.Float()
    margin_per = fields.Float()
    amount = fields.Float()







