from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .technical_order import LOCKED_STATES


class TechnicalOrderLine(models.Model):
    _name = 'technical.order.line'
    _description = 'Technical Order Line'
    _order = 'id'

    technical_order_id = fields.Many2one(
        'technical.order', string='Technical Order',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain=[('sale_ok', '=', True)],
    )
    description = fields.Char(
        string='Description', compute='_compute_description',
        store=True, readonly=False, precompute=True,
    )
    quantity = fields.Float(
        string='Quantity', default=1.0, digits='Product Unit of Measure',
    )
    price = fields.Float(
        string='Price', compute='_compute_price', store=True, readonly=True,
        precompute=True, digits='Product Price',
    )
    total = fields.Float(
        string='Total', compute='_compute_total', store=True, digits='Product Price',
    )
    remaining_quantity = fields.Float(
        string='Remaining Qty', compute='_compute_remaining_quantity',
        digits='Product Unit of Measure',
        help="Quantity of this product still available for new sales orders.",
    )

    # ------------------------------------------------------------------
    # Computes / constraints
    # ------------------------------------------------------------------
    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            line.description = line.product_id.name or False

    @api.depends('product_id')
    def _compute_price(self):
        # Depends on the product only: a later change of list price does not
        # silently alter the price of an existing technical order line.
        for line in self:
            line.price = line.product_id.list_price

    @api.depends('quantity', 'price')
    def _compute_total(self):
        for line in self:
            line.total = line.quantity * line.price

    @api.depends('technical_order_id.state', 'technical_order_id.sale_order_ids.state',
                 'product_id', 'quantity')
    def _compute_remaining_quantity(self):
        for order, lines in self.grouped('technical_order_id').items():
            origin = order._origin
            remaining = origin._get_remaining_quantities() \
                if origin and origin.state == 'approved' else {}
            for line in lines:
                line.remaining_quantity = remaining.get(line.product_id, 0.0)

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("The quantity must be greater than zero."))

    # ------------------------------------------------------------------
    # Server-side readonly enforcement
    # ------------------------------------------------------------------
    @api.model
    def _check_parent_editable(self, orders):
        if any(order.state in LOCKED_STATES for order in orders):
            raise UserError(_(
                "The lines of an approved, rejected or cancelled technical order "
                "cannot be modified."))

    @api.model_create_multi
    def create(self, vals_list):
        order_ids = {vals['technical_order_id'] for vals in vals_list
                     if vals.get('technical_order_id')}
        self._check_parent_editable(self.env['technical.order'].browse(order_ids))
        return super().create(vals_list)

    def write(self, vals):
        self._check_parent_editable(self.technical_order_id)
        if vals.get('technical_order_id'):
            self._check_parent_editable(
                self.env['technical.order'].browse(vals['technical_order_id']))
        return super().write(vals)

    def unlink(self):
        self._check_parent_editable(self.technical_order_id)
        return super().unlink()