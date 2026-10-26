from collections import defaultdict

from odoo import _, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_hold_availability(self):
        for order in self:
            # نجمع الكمية لكل منتج بوحدة قياس المنتج الأساسية
            totals = defaultdict(float)
            for line in order.order_line:
                product = line.product_id
                if line.display_type or not product or not product.is_storable:
                    continue
                totals[product] += line.product_uom._compute_quantity(
                    line.product_uom_qty, product.uom_id
                )

            for product, requested in totals.items():
                # نفحص المنتجات اللي عليها Hold فقط
                if not product.hold_qty_total:
                    continue
                available = product.sale_available_qty
                rounding = product.uom_id.rounding
                if float_compare(requested, available, precision_rounding=rounding) > 0:
                    raise ValidationError(_(
                        "Cannot confirm order %(order)s.\n"
                        "Product '%(product)s': requested %(requested)s, "
                        "but only %(available)s available for sale "
                        "(held: %(held)s).",
                        order=order.name,
                        product=product.display_name,
                        requested=requested,
                        available=max(available, 0.0),
                        held=product.hold_qty_total,
                    ))

    def action_confirm(self):
        self._check_hold_availability()
        return super().action_confirm()