from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    hold_qty_total = fields.Float(
        string='Held Qty',
        compute='_compute_hold_qty',
        digits='Product Unit of Measure',
    )
    sale_available_qty = fields.Float(
        string='Available for Sale',
        compute='_compute_hold_qty',
        digits='Product Unit of Measure',
    )

    def _compute_hold_qty(self):
        held = self.env['hold.sequence.line']._get_confirmed_hold_qty(self)
        for product in self:
            qty = held.get(product.id, 0.0)
            product.hold_qty_total = qty
            product.sale_available_qty = product.free_qty - qty