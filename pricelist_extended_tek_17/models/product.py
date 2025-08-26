from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_pricelist_user = fields.Boolean(
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    pricing_type = fields.Selection([
        ('regular', 'Regular'),
        ('lp_based', 'LP Based(Manufacture))'),
        ('lp_based_purchase', 'LP Based(Purchase)')
    ], string="Pricing Type", default='regular')

    last_purchase_price = fields.Float("Last Purchase Price")
    mrp_price = fields.Float("MRP Price")
    operational_margin = fields.Float("Operational Margin (%)")
    landing_price = fields.Float("Landing Price", compute="_compute_landing_price", store=True)

    qty_pricing_ids = fields.One2many(
        'product.qty.pricing', 'product_tmpl_id', string="Quantity Pricing"
    )
    customer_pricing_ids = fields.One2many(
        'product.customer.pricing', 'product_tmpl_id', string="Customer Type Pricing"
    )

    qty_lp_pricing_ids = fields.One2many(
        'product.qty.lp.pricing', 'product_tmpl_id', string="Quantity LP Pricing"
    )
    customer_lp_pricing_ids = fields.One2many(
        'product.customer.lp.pricing', 'product_tmpl_id', string="Customer Type LP Pricing"
    )
    qty_lp_purchase_ids = fields.One2many(
        'product.lp.purchase', 'product_tmpl_id', string="Quantity LP Purchase Pricing"
    )
    customer_lp_purchase_ids = fields.One2many(
        'product.customer.lp.purchase', 'product_tmpl_id', string="Customer Type LP Purchase Pricing"
    )

    # New field to control auto-sync
    auto_sync_to_variants = fields.Boolean(
        string="Auto Sync to Variants",
        default=True,
        help="Automatically sync pricing data to all product variants"
    )

    @api.depends('last_purchase_price', 'operational_margin')
    def _compute_landing_price(self):
        for rec in self:
            rec.landing_price = rec.last_purchase_price * (
                    1 + (rec.operational_margin / 100)) if rec.last_purchase_price else 0.0

    def write(self, vals):
        """Override write to sync changes to variants"""
        result = super(ProductTemplate, self).write(vals)

        # Fields that should be synced to variants
        sync_fields = [
            'pricing_type', 'last_purchase_price', 'operational_margin', 'mrp_price',
            'landing_price', 'auto_sync_to_variants'
        ]

        # Check if any sync field was modified or any pricing tables were modified
        should_sync = (
                any(field in vals for field in sync_fields) or
                'qty_pricing_ids' in vals or
                'customer_pricing_ids' in vals or
                'qty_lp_pricing_ids' in vals or
                'customer_lp_pricing_ids' in vals or
                'qty_lp_purchase_ids' in vals or
                'customer_lp_purchase_ids' in vals
        )

        if should_sync:
            for template in self:
                if template.auto_sync_to_variants:
                    template._sync_pricing_to_variants()

        return result

    @api.model
    def create(self, vals):
        """Override create to sync initial data to variants"""
        template = super(ProductTemplate, self).create(vals)
        if template.auto_sync_to_variants:
            template._sync_pricing_to_variants()
        return template

    def _sync_pricing_to_variants(self):
        """Sync pricing data from template to all variants"""
        for template in self:
            variants = template.product_variant_ids.filtered(lambda v: not v.has_custom_pricing)
            if not variants:
                continue

            # Sync basic pricing fields with context to avoid marking as custom
            variant_vals = {
                'pricing_type': template.pricing_type,
                'last_purchase_price': template.last_purchase_price,
                'operational_margin': template.operational_margin,
                'landing_price': template.landing_price,
                'mrp_price': template.mrp_price,
            }

            # Use context to indicate this is template sync
            variants.with_context(sync_from_template=True).write(variant_vals)

            # Sync all pricing types
            template._sync_qty_pricing_to_variants(variants)
            template._sync_customer_pricing_to_variants(variants)
            template._sync_lp_purchase_pricing_to_variants(variants)

    def _sync_qty_pricing_to_variants(self, variants):
        """Sync quantity pricing to variants"""
        for variant in variants:
            # Remove existing variant quantity pricing
            variant.qty_pricing_ids.unlink()
            variant.qty_lp_pricing_ids.unlink()
            variant.qty_lp_purchase_ids.unlink()

            # Sync regular quantity pricing
            if self.qty_pricing_ids:
                for qty_pricing in self.qty_pricing_ids:
                    self.env['product.qty.pricing'].with_context(sync_from_template=True).create({
                        'product_id': variant.id,
                        'product_tmpl_id': False,  # Clear template reference
                        'min_qty': qty_pricing.min_qty,
                        'max_qty': qty_pricing.max_qty,
                        'margin_per': qty_pricing.margin_per,
                    })

            # Sync LP quantity pricing
            if self.qty_lp_pricing_ids:
                for qty_pricing in self.qty_lp_pricing_ids:
                    self.env['product.qty.lp.pricing'].with_context(sync_from_template=True).create({
                        'product_id': variant.id,
                        'product_tmpl_id': False,  # Clear template reference
                        'min_qty': qty_pricing.min_qty,
                        'max_qty': qty_pricing.max_qty,
                        'margin_per': qty_pricing.margin_per,
                    })

            # Sync LP Purchase quantity pricing
            if self.qty_lp_purchase_ids:
                for qty_pricing in self.qty_lp_purchase_ids:
                    self.env['product.lp.purchase'].with_context(sync_from_template=True).create({
                        'product_id': variant.id,
                        'product_tmpl_id': False,  # Clear template reference
                        'min_qty': qty_pricing.min_qty,
                        'max_qty': qty_pricing.max_qty,
                        'margin_per': qty_pricing.margin_per,
                    })

    def _sync_customer_pricing_to_variants(self, variants):
        """Sync customer pricing to variants"""
        for variant in variants:
            # Remove existing variant customer pricing
            variant.customer_pricing_ids.unlink()
            variant.customer_lp_pricing_ids.unlink()
            variant.customer_lp_purchase_ids.unlink()

            # Sync regular customer pricing
            if self.customer_pricing_ids:
                for customer_pricing in self.customer_pricing_ids:
                    self.env['product.customer.pricing'].with_context(sync_from_template=True).create({
                        'product_id': variant.id,
                        'product_tmpl_id': False,  # Clear template reference
                        'customer_type_id': customer_pricing.customer_type_id.id,
                        'margin_per': customer_pricing.margin_per,
                    })

            # Sync LP customer pricing
            if self.customer_lp_pricing_ids:
                for customer_pricing in self.customer_lp_pricing_ids:
                    self.env['product.customer.lp.pricing'].with_context(sync_from_template=True).create({
                        'product_id': variant.id,
                        'product_tmpl_id': False,  # Clear template reference
                        'customer_type_id': customer_pricing.customer_type_id.id,
                        'margin_per': customer_pricing.margin_per,
                    })

    def _sync_lp_purchase_pricing_to_variants(self, variants):
        """Sync LP Purchase customer pricing to variants"""
        for variant in variants:
            # Remove existing variant LP Purchase customer pricing (already done in _sync_customer_pricing_to_variants)
            # This method is called for additional LP Purchase pricing logic if needed

            # Sync LP Purchase customer pricing
            if self.customer_lp_purchase_ids:
                for customer_pricing in self.customer_lp_purchase_ids:
                    self.env['product.customer.lp.purchase'].with_context(sync_from_template=True).create({
                        'product_id': variant.id,
                        'product_tmpl_id': False,  # Clear template reference
                        'customer_type_id': customer_pricing.customer_type_id.id,
                        'margin_per': customer_pricing.margin_per,
                    })

    def action_sync_all_variants(self):
        """Manual action to sync all variants"""
        self._sync_pricing_to_variants()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Pricing data synced to {len(self.product_variant_ids)} variants',
                'type': 'success',
            }
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_pricelist_admin_user = fields.Boolean(
        compute="_compute_is_pricelist_admin_user",
        store=False
    )

    def _compute_is_pricelist_admin_user(self):
        for user in self:
            user.is_pricelist_admin_user = self.env.user.has_group(
                "pricelist_extended_tek_17.group_admin_pricelist_user")

    pricing_type = fields.Selection([
        ('regular', 'Regular'),
        ('lp_based', 'LP Based(Manufacture))'),
        ('lp_based_purchase', 'LP Based(Purchase)')
    ], string="Pricing Type", default='regular')

    mrp_price = fields.Float("MRP Price")
    last_purchase_price = fields.Float("Last Purchase Price")
    operational_margin = fields.Float("Operational Margin (%)")
    landing_price = fields.Float("Landing Price", compute="_compute_landing_price", store=True)

    qty_pricing_ids = fields.One2many(
        'product.qty.pricing', 'product_id', string="Quantity Pricing"
    )
    customer_pricing_ids = fields.One2many(
        'product.customer.pricing', 'product_id', string="Customer Pricing"
    )

    qty_lp_pricing_ids = fields.One2many(
        'product.qty.lp.pricing', 'product_id', string="Quantity LP Pricing"
    )
    customer_lp_pricing_ids = fields.One2many(
        'product.customer.lp.pricing', 'product_id', string="Customer Type LP Pricing"
    )

    qty_lp_purchase_ids = fields.One2many(
        'product.lp.purchase', 'product_id', string="Quantity LP Purchase Pricing"
    )
    customer_lp_purchase_ids = fields.One2many(
        'product.customer.lp.purchase', 'product_id', string="Customer Type LP Purchase Pricing"
    )

    # Field to track if variant has custom pricing
    has_custom_pricing = fields.Boolean(
        string="Has Custom Pricing",
        default=False,
        help="If True, this variant has custom pricing and won't be auto-synced from template"
    )

    @api.depends('last_purchase_price', 'operational_margin')
    def _compute_landing_price(self):
        for rec in self:
            rec.landing_price = rec.last_purchase_price * (
                    1 + (rec.operational_margin / 100)) if rec.last_purchase_price else 0.0

    def write(self, vals):
        """Override write to mark variant as having custom pricing if manually modified"""
        pricing_fields = [
            'pricing_type', 'last_purchase_price', 'operational_margin', 'mrp_price',
            'qty_pricing_ids', 'customer_pricing_ids',
            'qty_lp_pricing_ids', 'customer_lp_pricing_ids',
            'qty_lp_purchase_ids', 'customer_lp_purchase_ids'
        ]

        # If user manually modifies pricing, mark as custom (but not during template sync)
        if any(field in vals for field in pricing_fields) and not self._context.get('sync_from_template'):
            vals['has_custom_pricing'] = True

        return super(ProductProduct, self).write(vals)

    def action_reset_to_template_pricing(self):
        """Action to reset variant pricing to template pricing"""
        for variant in self:
            if variant.product_tmpl_id.auto_sync_to_variants:
                variant.with_context(sync_from_template=True).write({'has_custom_pricing': False})
                variant.product_tmpl_id._sync_pricing_to_variants()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Variant pricing reset to template pricing',
                'type': 'success',
            }
        }


# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     is_pricelist_user = fields.Boolean(
#         compute="_compute_is_pricelist_user",
#         store=False
#     )
#
#     def _compute_is_pricelist_user(self):
#         for user in self:
#             user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")
#
#     pricing_type = fields.Selection([
#         ('regular', 'Regular'),
#         ('lp_based', 'LP Based(Manufacture))'),
#         ('lp_based_purchase', 'LP Based(Purchase)')
#     ], string="Pricing Type", default='regular')
#
#     last_purchase_price = fields.Float("Last Purchase Price")
#     mrp_price = fields.Float("MRP Price")
#     operational_margin = fields.Float("Operational Margin (%)")
#     landing_price = fields.Float("Landing Price", compute="_compute_landing_price", store=True)
#
#     qty_pricing_ids = fields.One2many(
#         'product.qty.pricing', 'product_tmpl_id', string="Quantity Pricing"
#     )
#     customer_pricing_ids = fields.One2many(
#         'product.customer.pricing', 'product_tmpl_id', string="Customer Type Pricing"
#     )
#
#     qty_lp_pricing_ids = fields.One2many(
#         'product.qty.lp.pricing', 'product_tmpl_id', string="Quantity LP Pricing"
#     )
#     customer_lp_pricing_ids = fields.One2many(
#         'product.customer.lp.pricing', 'product_tmpl_id', string="Customer Type LP Pricing"
#     )
#     qty_lp_purchase_ids = fields.One2many(
#         'product.lp.purchase', 'product_id', string="Quantity LP Pricing"
#     )
#     customer_lp_purchase_ids = fields.One2many(
#         'product.customer.lp.purchase', 'product_id', string="Customer Type LP Pricing"
#     )
#
#     # New field to control auto-sync
#     auto_sync_to_variants = fields.Boolean(
#         string="Auto Sync to Variants",
#         default=True,
#         help="Automatically sync pricing data to all product variants"
#     )
#
#     @api.depends('last_purchase_price', 'operational_margin')
#     def _compute_landing_price(self):
#         for rec in self:
#             rec.landing_price = rec.last_purchase_price * (
#                         1 + (rec.operational_margin / 100)) if rec.last_purchase_price else 0.0
#
#     def write(self, vals):
#         """Override write to sync changes to variants"""
#         result = super(ProductTemplate, self).write(vals)
#
#         # Fields that should be synced to variants
#         sync_fields = [
#             'pricing_type', 'last_purchase_price', 'operational_margin', 'mrp_price',  # Fixed missing comma
#             'landing_price', 'auto_sync_to_variants'
#         ]
#
#         # Check if any sync field was modified or any pricing tables were modified
#         should_sync = (
#             any(field in vals for field in sync_fields) or
#             'qty_pricing_ids' in vals or
#             'customer_pricing_ids' in vals or
#             'qty_lp_pricing_ids' in vals or
#             'customer_lp_pricing_ids' in vals
#         )
#
#         if should_sync:
#             for template in self:
#                 if template.auto_sync_to_variants:
#                     template._sync_pricing_to_variants()
#
#         return result
#
#     @api.model
#     def create(self, vals):
#         """Override create to sync initial data to variants"""
#         template = super(ProductTemplate, self).create(vals)
#         if template.auto_sync_to_variants:
#             template._sync_pricing_to_variants()
#         return template
#
#     def _sync_pricing_to_variants(self):
#         """Sync pricing data from template to all variants"""
#         for template in self:
#             variants = template.product_variant_ids.filtered(lambda v: not v.has_custom_pricing)
#             if not variants:
#                 continue
#
#             # Sync basic pricing fields with context to avoid marking as custom
#             variant_vals = {
#                 'pricing_type': template.pricing_type,
#                 'last_purchase_price': template.last_purchase_price,
#                 'operational_margin': template.operational_margin,
#                 'landing_price': template.landing_price,
#                 'mrp_price': template.mrp_price,
#             }
#
#             # Use context to indicate this is template sync
#             variants.with_context(sync_from_template=True).write(variant_vals)
#
#             # Sync quantity pricing
#             template._sync_qty_pricing_to_variants(variants)
#
#             # Sync customer pricing
#             template._sync_customer_pricing_to_variants(variants)
#
#     def _sync_qty_pricing_to_variants(self, variants):
#         """Sync quantity pricing to variants"""
#         for variant in variants:
#             # Remove existing variant quantity pricing
#             variant.qty_pricing_ids.unlink()
#             variant.qty_lp_pricing_ids.unlink()
#
#             # Sync regular quantity pricing
#             if self.qty_pricing_ids:
#                 for qty_pricing in self.qty_pricing_ids:
#                     self.env['product.qty.pricing'].with_context(sync_from_template=True).create({
#                         'product_id': variant.id,
#                         'product_tmpl_id': False,  # Clear template reference
#                         'min_qty': qty_pricing.min_qty,
#                         'max_qty': qty_pricing.max_qty,
#                         'margin_per': qty_pricing.margin_per,
#                     })
#
#             # Sync LP quantity pricing
#             if self.qty_lp_pricing_ids:
#                 for qty_pricing in self.qty_lp_pricing_ids:
#                     self.env['product.qty.lp.pricing'].with_context(sync_from_template=True).create({
#                         'product_id': variant.id,
#                         'product_tmpl_id': False,  # Clear template reference
#                         'min_qty': qty_pricing.min_qty,
#                         'max_qty': qty_pricing.max_qty,
#                         'margin_per': qty_pricing.margin_per,
#                     })
#
#     def _sync_customer_pricing_to_variants(self, variants):
#         """Sync customer pricing to variants"""
#         for variant in variants:
#             # Remove existing variant customer pricing
#             variant.customer_pricing_ids.unlink()
#             variant.customer_lp_pricing_ids.unlink()
#
#             # Sync regular customer pricing
#             if self.customer_pricing_ids:
#                 for customer_pricing in self.customer_pricing_ids:
#                     self.env['product.customer.pricing'].with_context(sync_from_template=True).create({
#                         'product_id': variant.id,
#                         'product_tmpl_id': False,  # Clear template reference
#                         'customer_type_id': customer_pricing.customer_type_id.id,
#                         'margin_per': customer_pricing.margin_per,
#                     })
#
#             # Sync LP customer pricing
#             if self.customer_lp_pricing_ids:
#                 for customer_pricing in self.customer_lp_pricing_ids:
#                     self.env['product.customer.lp.pricing'].with_context(sync_from_template=True).create({
#                         'product_id': variant.id,
#                         'product_tmpl_id': False,  # Clear template reference
#                         'customer_type_id': customer_pricing.customer_type_id.id,
#                         'margin_per': customer_pricing.margin_per,
#                     })
#
#     def action_sync_all_variants(self):
#         """Manual action to sync all variants"""
#         self._sync_pricing_to_variants()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success',
#                 'message': f'Pricing data synced to {len(self.product_variant_ids)} variants',
#                 'type': 'success',
#             }
#         }
#
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     is_pricelist_admin_user = fields.Boolean(
#         compute="_compute_is_pricelist_admin_user",
#         store=False
#     )
#
#     def _compute_is_pricelist_admin_user(self):
#         for user in self:
#             user.is_pricelist_admin_user = self.env.user.has_group("pricelist_extended_tek_17.group_admin_pricelist_user")
#
#     pricing_type = fields.Selection([
#         ('regular', 'Regular'),
#         ('lp_based', 'LP Based(Manufacture))'),
#         ('lp_based_purchase', 'LP Based(Purchase)')
#     ], string="Pricing Type", default='regular')
#
#     mrp_price = fields.Float("MRP Price")
#     last_purchase_price = fields.Float("Last Purchase Price")
#     operational_margin = fields.Float("Operational Margin (%)")
#     landing_price = fields.Float("Landing Price", compute="_compute_landing_price", store=True)
#
#     qty_pricing_ids = fields.One2many(
#         'product.qty.pricing', 'product_id', string="Quantity Pricing"
#     )
#     customer_pricing_ids = fields.One2many(
#         'product.customer.pricing', 'product_id', string="Customer Pricing"
#     )
#
#     qty_lp_pricing_ids = fields.One2many(
#         'product.qty.lp.pricing', 'product_id', string="Quantity LP Pricing"
#     )
#     customer_lp_pricing_ids = fields.One2many(
#         'product.customer.lp.pricing', 'product_id', string="Customer Type LP Pricing"
#     )
#
#     qty_lp_purchase_ids = fields.One2many(
#         'product.lp.purchase', 'product_id', string="Quantity LP Pricing"
#     )
#     customer_lp_purchase_ids = fields.One2many(
#         'product.customer.lp.purchase', 'product_id', string="Customer Type LP Pricing"
#     )
#     # Field to track if variant has custom pricing
#     has_custom_pricing = fields.Boolean(
#         string="Has Custom Pricing",
#         default=False,
#         help="If True, this variant has custom pricing and won't be auto-synced from template"
#     )
#
#     @api.depends('last_purchase_price', 'operational_margin')
#     def _compute_landing_price(self):
#         for rec in self:
#             rec.landing_price = rec.last_purchase_price * (
#                         1 + (rec.operational_margin / 100)) if rec.last_purchase_price else 0.0
#
#     def write(self, vals):
#         """Override write to mark variant as having custom pricing if manually modified"""
#         pricing_fields = [
#             'pricing_type', 'last_purchase_price', 'operational_margin', 'mrp_price',  # Fixed comma
#             'qty_pricing_ids', 'customer_pricing_ids',  # Removed duplicates
#             'qty_lp_pricing_ids', 'customer_lp_pricing_ids'
#         ]
#
#         # If user manually modifies pricing, mark as custom (but not during template sync)
#         if any(field in vals for field in pricing_fields) and not self._context.get('sync_from_template'):
#             vals['has_custom_pricing'] = True
#
#         return super(ProductProduct, self).write(vals)
#
#     def action_reset_to_template_pricing(self):
#         """Action to reset variant pricing to template pricing"""
#         for variant in self:
#             if variant.product_tmpl_id.auto_sync_to_variants:
#                 variant.with_context(sync_from_template=True).write({'has_custom_pricing': False})
#                 variant.product_tmpl_id._sync_pricing_to_variants()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success',
#                 'message': 'Variant pricing reset to template pricing',
#                 'type': 'success',
#             }
#         }


class ProductQtyPricing(models.Model):
    _name = 'product.qty.pricing'
    _description = "Product Quantity Based Pricing"

    is_pricelist_user = fields.Boolean(
        string="Is Pricelist User",
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    wizard_id = fields.Many2one('price.details.wizard')
    product_id = fields.Many2one('product.product', string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")

    min_qty = fields.Float("Min Qty")
    max_qty = fields.Float("Max Qty")
    margin_per = fields.Float("Margin (%)")
    amount = fields.Float("Sale Price", compute="_compute_amount", store=True)
    margin = fields.Float("Margin (₹)", compute="_compute_margin", store=True)

    @api.depends('product_id.landing_price', 'product_tmpl_id.landing_price', 'margin_per')
    def _compute_amount(self):
        for rec in self:
            base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
            # rec.amount = base_price * (1 + (rec.margin_per / 100)) if base_price else 0.0
            if base_price:
                price = base_price * (1 + (rec.margin_per / 100))
                rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.amount = 0.0

    @api.depends('amount', 'product_id.landing_price', 'product_tmpl_id.landing_price')
    def _compute_margin(self):
        for rec in self:
            base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
            # rec.margin = rec.amount - base_price if base_price else 0.0
            if base_price:
                price = abs(rec.amount - base_price)
                rec.margin = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.margin = 0.0

    def write(self, vals):
        """Trigger sync to variants when template qty pricing is modified"""
        result = super(ProductQtyPricing, self).write(vals)

        # Only sync if this is a template record and sync is enabled
        for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
            if rec.product_tmpl_id.auto_sync_to_variants:
                variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: not v.has_custom_pricing
                )
                if variants_to_sync:
                    rec.product_tmpl_id._sync_qty_pricing_to_variants(variants_to_sync)
        return result


class ProductCustomerPricing(models.Model):
    _name = 'product.customer.pricing'
    _description = "Product Customer Type Pricing"

    is_pricelist_user = fields.Boolean(
        string="Is Pricelist User",
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    wizard_id = fields.Many2one('price.details.wizard')
    product_id = fields.Many2one('product.product', string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")

    customer_type_id = fields.Many2one(
        'res.partner.customer.type',
        string="Customer Type"
    )

    margin_per = fields.Float("Margin (%)")
    amount = fields.Float("Sale Price", compute="_compute_amount", store=True)
    margin = fields.Float("Margin (₹)", compute="_compute_margin", store=True)

    @api.depends('product_id.landing_price', 'product_tmpl_id.landing_price', 'margin_per')
    def _compute_amount(self):
        for rec in self:
            base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
            # rec.amount = base_price * (1 + (rec.margin_per / 100)) if base_price else 0.0
            if base_price:
                price = base_price * (1 + (rec.margin_per / 100))
                rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.amount = 0.0
    @api.depends('amount', 'product_id.landing_price', 'product_tmpl_id.landing_price')
    def _compute_margin(self):
        for rec in self:
            base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
            # rec.margin = rec.amount - base_price if base_price else 0.0
            if base_price:
                price = abs(rec.amount - base_price)
                rec.margin = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.margin = 0.0

    def write(self, vals):
        """Trigger sync to variants when template customer pricing is modified"""
        result = super(ProductCustomerPricing, self).write(vals)

        # Only sync if this is a template record and sync is enabled
        for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
            if rec.product_tmpl_id.auto_sync_to_variants:
                variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: not v.has_custom_pricing
                )
                if variants_to_sync:
                    rec.product_tmpl_id._sync_customer_pricing_to_variants(variants_to_sync)
        return result


class ProductQtyLpPricing(models.Model):
    _name = 'product.qty.lp.pricing'
    _description = "Product Quantity LP Based Pricing"

    wizard_id = fields.Many2one('price.details.wizard')
    product_id = fields.Many2one('product.product', string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")

    is_pricelist_user = fields.Boolean(
        string="Is Pricelist User",
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    min_qty = fields.Float("Min Qty")
    max_qty = fields.Float("Max Qty")
    margin_per = fields.Float("Discount (%)")
    amount = fields.Float("Sale Price", compute="_compute_lp_amount", store=True)
    margin = fields.Float("Margin (₹)", compute="_compute_lp_margin", store=True)

    @api.depends('product_id.mrp_price', 'product_tmpl_id.mrp_price', 'margin_per')
    def _compute_lp_amount(self):
        for rec in self:
            base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            # rec.amount = base_price * (1 - (rec.margin_per / 100)) if base_price else 0.0
            if base_price:
                price = base_price * (1 - (rec.margin_per / 100))
                rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.amount = 0.0

    @api.depends('amount', 'product_id.standard_price', 'product_tmpl_id.standard_price')
    def _compute_lp_margin(self):
        for rec in self:
            base_price = rec.product_id.standard_price or rec.product_tmpl_id.standard_price
            # rec.margin = abs(rec.amount - base_price) if base_price else 0.0
            if base_price:
                price = abs(rec.amount - base_price)
                rec.margin = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.margin = 0.0

    def write(self, vals):
        """Trigger sync to variants when template qty LP pricing is modified"""
        result = super(ProductQtyLpPricing, self).write(vals)

        # Only sync if this is a template record and sync is enabled
        for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
            if rec.product_tmpl_id.auto_sync_to_variants:
                variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: not v.has_custom_pricing
                )
                if variants_to_sync:
                    rec.product_tmpl_id._sync_qty_pricing_to_variants(variants_to_sync)
        return result


class ProductCustomerLpPricing(models.Model):
    _name = 'product.customer.lp.pricing'
    _description = "Product Customer Type LP Pricing"

    wizard_id = fields.Many2one('price.details.wizard')
    product_id = fields.Many2one('product.product', string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")

    is_pricelist_user = fields.Boolean(
        string="Is Pricelist User",
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    customer_type_id = fields.Many2one(
        'res.partner.customer.type',
        string="Customer Type"
    )

    margin_per = fields.Float("Discount (%)")
    amount = fields.Float("Sale Price", compute="_compute_lp_amount", store=True)
    margin = fields.Float("Margin  (₹)", compute="_compute_lp_margin", store=True)

    @api.depends('product_id.mrp_price', 'product_tmpl_id.mrp_price', 'margin_per')
    def _compute_lp_amount(self):
        for rec in self:
            # base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            # rec.amount = base_price * (1 - (rec.margin_per / 100)) if base_price else 0.0
            base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            if base_price:
                price = base_price * (1 - (rec.margin_per / 100))
                rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.amount = 0.0

    @api.depends('amount', 'product_id.standard_price', 'product_tmpl_id.standard_price')
    def _compute_lp_margin(self):
        for rec in self:

            base_price = rec.product_id.standard_price or rec.product_tmpl_id.standard_price
            if base_price:
                price = abs(rec.amount - base_price)
                rec.margin = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.margin = 0.0

    def write(self, vals):
        """Trigger sync to variants when template customer LP pricing is modified"""
        result = super(ProductCustomerLpPricing, self).write(vals)

        for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
            if rec.product_tmpl_id.auto_sync_to_variants:
                variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: not v.has_custom_pricing
                )
                if variants_to_sync:
                    rec.product_tmpl_id._sync_customer_pricing_to_variants(variants_to_sync)
        return result


class ProductLpPurchase(models.Model):
    _name = 'product.lp.purchase'
    _description = "Product LP Purchase"

    is_pricelist_user = fields.Boolean(
        string="Is Pricelist User",
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    product_id = fields.Many2one('product.product', string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")

    min_qty = fields.Float("Min Qty")
    max_qty = fields.Float("Max Qty")
    margin_per = fields.Float("Discount (%)")
    amount = fields.Float("Sale Price", compute="_compute_amount", store=True)
    margin = fields.Float("Margin (₹)", compute="_compute_margin", store=True)

    @api.depends('product_id.mrp_price', 'product_tmpl_id.mrp_price', 'margin_per')
    def _compute_amount(self):
        for rec in self:
            # base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            # rec.amount = base_price * (1 - (rec.margin_per / 100)) if base_price else 0.0
            base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            if base_price:
                price = base_price * (1 - (rec.margin_per / 100))
                rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.amount = 0.0

    @api.depends('amount', 'product_id.landing_price', 'product_tmpl_id.landing_price')
    def _compute_margin(self):
        for rec in self:
            base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
            if base_price:
                price = abs(rec.amount - base_price)
                rec.margin = float_round(price, precision_digits=2)
            else:
                rec.margin = 0.0

    def write(self, vals):
        """Trigger sync to variants when template qty pricing is modified"""
        result = super().write(vals)

        # Only sync if this is a template record and sync is enabled
        for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
            if rec.product_tmpl_id.auto_sync_to_variants:
                variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: not v.has_custom_pricing
                )
                if variants_to_sync:
                    rec.product_tmpl_id._sync_qty_pricing_to_variants(variants_to_sync)
        return result


class ProductCustomerLPPurchase(models.Model):
    _name = 'product.customer.lp.purchase'
    _description = "Product Customer LP Purchase"

    is_pricelist_user = fields.Boolean(
        string="Is Pricelist User",
        compute="_compute_is_pricelist_user",
        store=False
    )

    def _compute_is_pricelist_user(self):
        for user in self:
            user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")

    product_id = fields.Many2one('product.product', string="Product Variant")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template")

    customer_type_id = fields.Many2one(
        'res.partner.customer.type',
        string="Customer Type"
    )

    margin_per = fields.Float("Discount (%)")
    amount = fields.Float("Sale Price", compute="_compute_amount", store=True)
    margin = fields.Float("Margin (₹)", compute="_compute_margin", store=True)

    @api.depends('product_id.mrp_price', 'product_tmpl_id.mrp_price', 'margin_per')
    def _compute_amount(self):
        for rec in self:
            # base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            # rec.amount = base_price * (1 - (rec.margin_per / 100)) if base_price else 0.0
            base_price = rec.product_id.mrp_price or rec.product_tmpl_id.mrp_price
            if base_price:
                price = base_price * (1 - (rec.margin_per / 100))
                rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
            else:
                rec.amount = 0.0

    @api.depends('amount', 'product_id.landing_price', 'product_tmpl_id.landing_price')
    def _compute_margin(self):
        for rec in self:
            base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
            if base_price:
                price = abs(rec.amount - base_price)
                rec.margin = float_round(price, precision_digits=2)
            else:
                rec.margin = 0.0

    def write(self, vals):
        """Trigger sync to variants when template customer pricing is modified"""
        result = super().write(vals)

        # Only sync if this is a template record and sync is enabled
        for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
            if rec.product_tmpl_id.auto_sync_to_variants:
                variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: not v.has_custom_pricing
                )
                if variants_to_sync:
                    rec.product_tmpl_id._sync_customer_pricing_to_variants(variants_to_sync)
        return result


# class ProductLpPurchase(models.Model):
#     _name = 'product.lp.purchase'
#     _description = "Product LP Purchase"
#
#     is_pricelist_user = fields.Boolean(
#         string="Is Pricelist User",
#         compute="_compute_is_pricelist_user",
#         store=False
#     )
#
#     def _compute_is_pricelist_user(self):
#         for user in self:
#             user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")
#
#     product_id = fields.Many2one('product.product', string="Product Variant")
#     product_tmpl_id = fields.Many2one('product.template', string="Product Template")
#
#     min_qty = fields.Float("Min Qty")
#     max_qty = fields.Float("Max Qty")
#     margin_per = fields.Float("Margin (%)")
#     amount = fields.Float("Sale Price", compute="_compute_amount", store=True)
#     margin = fields.Float("Margin (₹)", compute="_compute_margin", store=True)
#
#     @api.depends('product_id.landing_price', 'product_tmpl_id.landing_price', 'margin_per')
#     def _compute_amount(self):
#         for rec in self:
#             base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
#             # rec.amount = base_price * (1 + (rec.margin_per / 100)) if base_price else 0.0
#             if base_price:
#                 price = base_price * (1 + (rec.margin_per / 100))
#                 rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
#             else:
#                 rec.amount = 0.0
#
#     @api.depends('amount', 'product_id.landing_price', 'product_tmpl_id.landing_price')
#     def _compute_margin(self):
#         for rec in self:
#             base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
#             # rec.margin = rec.amount - base_price if base_price else 0.0
#             if base_price:
#                 price = abs(rec.amount - base_price)
#                 rec.margin = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
#             else:
#                 rec.margin = 0.0
#
#     def write(self, vals):
#         """Trigger sync to variants when template qty pricing is modified"""
#         result = super(ProductQtyPricing, self).write(vals)
#
#         # Only sync if this is a template record and sync is enabled
#         for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
#             if rec.product_tmpl_id.auto_sync_to_variants:
#                 variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
#                     lambda v: not v.has_custom_pricing
#                 )
#                 if variants_to_sync:
#                     rec.product_tmpl_id._sync_qty_pricing_to_variants(variants_to_sync)
#         return result
#
#
# class ProductCustomerLPPurchase(models.Model):
#     _name = 'product.customer.lp.purchase'
#     _description = "Product Lp Purchase"
#
#     is_pricelist_user = fields.Boolean(
#         string="Is Pricelist User",
#         compute="_compute_is_pricelist_user",
#         store=False
#     )
#
#     def _compute_is_pricelist_user(self):
#         for user in self:
#             user.is_pricelist_user = self.env.user.has_group("pricelist_extended_tek_17.group_pricelist_user")
#
#     product_id = fields.Many2one('product.product', string="Product Variant")
#     product_tmpl_id = fields.Many2one('product.template', string="Product Template")
#
#     customer_type_id = fields.Many2one(
#         'res.partner.customer.type',
#         string="Customer Type"
#     )
#
#     margin_per = fields.Float("Margin (%)")
#     amount = fields.Float("Sale Price", compute="_compute_amount", store=True)
#     margin = fields.Float("Margin (₹)", compute="_compute_margin", store=True)
#
#     @api.depends('product_id.landing_price', 'product_tmpl_id.landing_price', 'margin_per')
#     def _compute_amount(self):
#         for rec in self:
#             base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
#             # rec.amount = base_price * (1 + (rec.margin_per / 100)) if base_price else 0.0
#             if base_price:
#                 price = base_price * (1 + (rec.margin_per / 100))
#                 rec.amount = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
#             else:
#                 rec.amount = 0.0
#     @api.depends('amount', 'product_id.landing_price', 'product_tmpl_id.landing_price')
#     def _compute_margin(self):
#         for rec in self:
#             base_price = rec.product_id.landing_price or rec.product_tmpl_id.landing_price
#             # rec.margin = rec.amount - base_price if base_price else 0.0
#             if base_price:
#                 price = abs(rec.amount - base_price)
#                 rec.margin = float_round(price, precision_digits=2)  # ✅ ensure 2-decimal consistency
#             else:
#                 rec.margin = 0.0
#
#     def write(self, vals):
#         """Trigger sync to variants when template customer pricing is modified"""
#         result = super(ProductCustomerPricing, self).write(vals)
#
#         # Only sync if this is a template record and sync is enabled
#         for rec in self.filtered(lambda r: r.product_tmpl_id and not self._context.get('sync_from_template')):
#             if rec.product_tmpl_id.auto_sync_to_variants:
#                 variants_to_sync = rec.product_tmpl_id.product_variant_ids.filtered(
#                     lambda v: not v.has_custom_pricing
#                 )
#                 if variants_to_sync:
#                     rec.product_tmpl_id._sync_customer_pricing_to_variants(variants_to_sync)
#         return result



