from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_tech_offer = fields.Boolean(
        string='Technical Offer Customer',
        help="Only partners with this flag can be selected on Technical Orders.",
    )