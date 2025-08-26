# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PricelppurfixedWizard(models.Model):
    _name = 'price.lp.pur.fixed.wizard'
    _description = 'Price LP Purchase Fixed Wizard'

    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    qty_price_reg_ids = fields.One2many('price.quantity.lp.pur.fixed', 'wizard_id', string="Quantity Pricing")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_id = self.env.context.get("default_product_id")
        if product_id:
            product = self.env['product.product'].browse(product_id)
            qty_lines = []
            for q in product.qty_lp_purchase_ids:
                qty_lines.append((0, 0, {
                    'min_qty': q.min_qty,
                    'max_qty': q.max_qty,
                    'margin_per': q.margin_per,
                    'amount': q.amount,
                }))
            res['qty_price_reg_ids'] = qty_lines
        return res

class PriceWizardlppurFixed(models.TransientModel):
    _name = 'price.quantity.lp.pur.fixed'
    _description = 'Wizard LP Purchase Fixed Pricing'

    wizard_id = fields.Many2one('price.lp.pur.fixed.wizard', ondelete="cascade")
    min_qty = fields.Float()
    max_qty = fields.Float()
    margin_per = fields.Float()
    amount = fields.Float()







