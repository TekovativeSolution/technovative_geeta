from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

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
        string="Customer Type",
    )

    @api.constrains('pricing_type', 'customer_type_id')
    def _check_customer_type_required(self):
        for rec in self:
            if rec.pricing_type == 'fixed' and not rec.customer_type_id:
                raise ValidationError(_("Customer Type is required when Pricing Type is Fixed."))
