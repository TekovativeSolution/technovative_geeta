from odoo import models, fields

class ResPartnerCustomerType(models.Model):
    _name = 'res.partner.customer.type'
    _description = "Customer Type"

    name = fields.Char("Customer Type", required=True)
