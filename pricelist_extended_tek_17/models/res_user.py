from odoo import models, fields


class GroupsImplied(models.Model):
    _inherit = 'res.groups'

    show_price_list = fields.Boolean(string="Price List User")
    show_admin_price_list = fields.Boolean(string="Price List Admin User")

