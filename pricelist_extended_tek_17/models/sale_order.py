from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    pricing_type = fields.Selection(
        [
            ('quantity', 'Quantity Based'),
            ('fixed', 'Trader Price'),
        ],
        string="Pricing Type",
        default='quantity'
    )

    customer_type_id = fields.Many2one(
        'res.partner.customer.type',
        string="Customer Type"
    )

    @api.onchange('partner_id')
    def _onchange_partner_id_set_pricing_and_customer_type(self):
        if self.partner_id:
            self.pricing_type = self.partner_id.pricing_type
            self.customer_type_id = self.partner_id.customer_type_id.id

        else:
            self.pricing_type = False
            self.customer_type_id = False

    @api.model
    def create(self, vals):
        # if no value passed, fetch from partner
        if vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if not vals.get('pricing_type'):
                vals['pricing_type'] = partner.pricing_type or 'quantity'
            if not vals.get('customer_type_id'):
                vals['customer_type_id'] = partner.customer_type_id.id or False
        return super().create(vals)

    def write(self, vals):
        for order in self:
            if vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                if 'pricing_type' not in vals:
                    vals['pricing_type'] = partner.pricing_type or 'quantity'
                if 'customer_type_id' not in vals:
                    vals['customer_type_id'] = partner.customer_type_id.id or False
        return super().write(vals)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_info = fields.Char(
        string="Price Info",
        compute="_compute_price_info",
        store=False
    )

    @api.depends('product_id')
    def _compute_price_info(self):
        """Compute basic price info display"""
        for line in self:
            if line.product_id:
                info_parts = []
                # Landing price
                if line.product_id.landing_price:
                    currency = line.order_id.currency_id
                    landing_price = currency.round(line.product_id.landing_price)
                    info_parts.append(f"LP: {currency.symbol}{landing_price}")

                # Pricing type
                if line.product_id.pricing_type:
                    type_display = dict(line.product_id._fields['pricing_type'].selection).get(
                        line.product_id.pricing_type, ''
                    )
                    info_parts.append(f"Type: {type_display}")

                # Quantity pricing count
                qty_count = len(line.product_id.qty_pricing_ids)
                if qty_count > 0:
                    info_parts.append(f"Qty Rules: {qty_count}")

                # Customer pricing count
                cust_count = len(line.product_id.customer_pricing_ids)
                if cust_count > 0:
                    info_parts.append(f"Cust Rules: {cust_count}")

                line.price_info = " | ".join(info_parts) if info_parts else "No pricing info"
            else:
                line.price_info = ""

    def action_show_price_details(self):
        """Action to show detailed price information in a wizard popup"""
        if self.order_id.pricing_type == 'fixed':
            if self.product_id.pricing_type == 'regular':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.reg.cus.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }

            if self.product_id.pricing_type == 'lp_based':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.lp.cus.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }
            if self.product_id.pricing_type == 'lp_based_purchase':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.lp.cus.pur.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }
        if self.order_id.pricing_type == 'quantity':
            if self.product_id.pricing_type == 'regular':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.fixed.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }

            if self.product_id.pricing_type == 'lp_based':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.lp.fixed.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }

            if self.product_id.pricing_type == 'lp_based':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.lp.fixed.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }

            if self.product_id.pricing_type == 'lp_based_purchase':
                return {
                    'type': 'ir.actions.act_window',
                    'name': f'Price Details - {self.product_id.name}',
                    'res_model': 'price.lp.pur.fixed.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': self.id,
                        'active_model': 'sale.order.line',
                        'default_product_id': self.product_id.id,
                        'default_sale_line_id': self.id,
                    }
                }

    @api.onchange("product_id","product_uom_qty")
    def _onchange_product_id_pricing(self):
        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue

            partner = line.order_id.partner_id
            product = line.product_id.product_tmpl_id
            qty = line.product_uom_qty or 1.0
            price = 0.0

            # Check partner pricing type
            if partner.pricing_type == "fixed":
                # product regular → use customer_pricing_ids
                if product.pricing_type == "regular":
                    customer_line = product.customer_pricing_ids.filtered(
                        lambda cp: cp.customer_type_id == partner.customer_type_id
                    )
                    if customer_line:
                        price = customer_line[0].amount

                # product lp_based → use customer_lp_pricing_ids
                elif product.pricing_type == "lp_based":
                    customer_line = product.customer_lp_pricing_ids.filtered(
                        lambda cp: cp.customer_type_id == partner.customer_type_id
                    )
                    if customer_line:
                        price = customer_line[0].amount

                elif product.pricing_type == "lp_based_purchase":
                    customer_line = product.customer_lp_purchase_ids.filtered(
                        lambda cp: cp.customer_type_id == partner.customer_type_id
                    )
                    if customer_line:
                        price = customer_line[0].amount


            elif partner.pricing_type == "quantity":

                if product.pricing_type == "regular":

                    qty_line = product.qty_pricing_ids.filtered(

                        lambda qp: (not qp.min_qty or qty >= qp.min_qty)

                                   and (not qp.max_qty or qty <= qp.max_qty)  # strict check

                    )

                    if qty_line:
                        price = qty_line[0].amount


                elif product.pricing_type == "lp_based":

                    qty_line = product.qty_lp_pricing_ids.filtered(

                        lambda qp: (not qp.min_qty or qty >= qp.min_qty)

                                   and (not qp.max_qty or qty <= qp.max_qty)  # strict check

                    )

                    if qty_line:
                        price = qty_line[0].amount

                elif product.pricing_type == "lp_based_purchase":

                    qty_line = product.qty_lp_purchase_ids.filtered(

                        lambda qp: (not qp.min_qty or qty >= qp.min_qty)

                                   and (not qp.max_qty or qty <= qp.max_qty)  # strict check

                    )

                    if qty_line:
                        price = qty_line[0].amount

            # If no price found → fallback to normal Odoo price
            if price:
                line.price_unit = price

