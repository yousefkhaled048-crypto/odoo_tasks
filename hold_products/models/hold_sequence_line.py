from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HoldSequenceLine(models.Model):
    _name = 'hold.sequence.line'
    _description = 'Hold and Take Sequence Line'

    sequence_id = fields.Many2one(
        'hold.sequence',
        string='Hold Reference',
        required=True,
        ondelete='cascade',
        index=True,
    )
    state = fields.Selection(
        related='sequence_id.state',
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('is_storable', '=', True)],
    )
    product_uom_id = fields.Many2one(
        related='product_id.uom_id',
        string='Unit of Measure',
    )
    available_qty = fields.Float(
        string='Available Qty',
        compute='_compute_available_qty',
        digits='Product Unit of Measure',
    )
    hold_qty = fields.Float(
        string='Hold Qty',
        required=True,
        default=0.0,
        digits='Product Unit of Measure',
    )

    @api.model
    def _get_confirmed_hold_qty(self, products, exclude_lines=None):
        """Return {product_id: total confirmed hold qty}."""
        domain = [
            ('product_id', 'in', products.ids),
            ('state', '=', 'confirmed'),
        ]
        if exclude_lines and exclude_lines.ids:
            domain.append(('id', 'not in', exclude_lines.ids))
        groups = self.sudo()._read_group(
            domain, ['product_id'], ['hold_qty:sum']
        )
        return {product.id: qty for product, qty in groups}

    @api.depends('product_id', 'state')
    def _compute_available_qty(self):
        for line in self:
            if not line.product_id:
                line.available_qty = 0.0
                continue
            held = self._get_confirmed_hold_qty(
                line.product_id, exclude_lines=line
            ).get(line.product_id.id, 0.0)
            line.available_qty = line.product_id.qty_available - held

    @api.constrains('hold_qty')
    def _check_hold_qty_positive(self):
        for line in self:
            if line.hold_qty <= 0:
                raise ValidationError(_("Hold quantity must be greater than zero."))