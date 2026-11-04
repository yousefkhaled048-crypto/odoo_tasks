from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    technical_order_id = fields.Many2one(
        'technical.order', string='Technical Order',
        readonly=True, copy=False, index=True, ondelete='restrict',
    )

    def _check_technical_order_quantities(self):
        orders = self.filtered('technical_order_id')
        # Grouping by technical order makes a batch confirmation count every
        # order of the batch once, and the already-confirmed ones separately.
        for technical_order, sale_orders in orders.grouped('technical_order_id').items():
            technical_order._check_sale_quantities(sale_orders)

    def action_confirm(self):
        self._check_technical_order_quantities()
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_technical_order_countable(self):
        """Lines that consume technical order quantities."""
        self.ensure_one()
        if self.display_type or not self.product_id or self.is_downpayment:
            return False
        # Delivery lines (delivery module) are not part of a technical order.
        return not (self._fields.get('is_delivery') and self.is_delivery)