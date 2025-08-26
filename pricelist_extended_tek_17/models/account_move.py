from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()

        for move in self:
            if move.move_type == 'in_invoice':  # Only vendor bills
                for line in move.invoice_line_ids:
                    if line.product_id and line.quantity > 0:
                        product = line.product_id.product_tmpl_id
                        unit_cost = line.price_subtotal / line.quantity
                        product.write({'last_purchase_price': unit_cost})
                        product._compute_landing_price()

                        if product.auto_sync_to_variants:
                            product._sync_pricing_to_variants()

        return res
