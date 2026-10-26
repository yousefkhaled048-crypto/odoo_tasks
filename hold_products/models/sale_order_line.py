from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _check_hold_extra_qty(self, extra_by_product):
        """extra_by_product: {product: extra qty in product base UoM}"""
        for product, extra in extra_by_product.items():
            if extra <= 0 or not product.is_storable:
                continue
            # نفحص المنتجات اللي عليها Hold فقط
            if not product.hold_qty_total:
                continue
            available = product.sale_available_qty
            if float_compare(
                extra, available, precision_rounding=product.uom_id.rounding
            ) > 0:
                raise ValidationError(_(
                    "Cannot increase the quantity of '%(product)s' by %(extra)s.\n"
                    "Only %(available)s available for sale (held: %(held)s).",
                    product=product.display_name,
                    extra=extra,
                    available=max(available, 0.0),
                    held=product.hold_qty_total,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        extra = defaultdict(float)
        Order = self.env['sale.order']
        Product = self.env['product.product']
        Uom = self.env['uom.uom']
        for vals in vals_list:
            if (vals.get('display_type') or not vals.get('order_id')
                    or not vals.get('product_id')):
                continue
            # سطر جديد على طلب مؤكد بس
            if Order.browse(vals['order_id']).state != 'sale':
                continue
            product = Product.browse(vals['product_id'])
            uom = (Uom.browse(vals['product_uom'])
                   if vals.get('product_uom') else product.uom_id)
            qty = vals.get('product_uom_qty', 1.0)
            extra[product] += uom._compute_quantity(qty, product.uom_id)
        self._check_hold_extra_qty(extra)
        return super().create(vals_list)

    def write(self, vals):
        if 'product_uom_qty' in vals:
            extra = defaultdict(float)
            for line in self:
                if (line.order_id.state != 'sale' or line.display_type
                        or not line.product_id):
                    continue
                delta = vals['product_uom_qty'] - line.product_uom_qty
                if delta > 0:
                    extra[line.product_id] += line.product_uom._compute_quantity(
                        delta, line.product_id.uom_id
                    )
            self._check_hold_extra_qty(extra)
        return super().write(vals)