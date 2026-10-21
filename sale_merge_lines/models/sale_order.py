from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def merge_duplicate_lines(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue

            same_order = {}
            for line in order.order_line:
                if not line.product_id:
                    continue

                key = (line.product_id.id, line.product_uom.id)
                if key in same_order:
                    target = same_order[key]

                    target.product_uom_qty += line.product_uom_qty
                    line.unlink()
                else:
                    same_order[key] = line

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.merge_duplicate_lines()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'order_line' in vals:
            self.merge_duplicate_lines()
        return res



# from odoo import api, models
# from odoo.exceptions import UserError
#
# # Odoo 18 names. In Odoo 19 they become 'product_uom_id' and 'tax_ids'.
# UOM_FIELD = 'product_uom'
# TAX_FIELD = 'tax_id'
#
#
# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'
#
#     def _merge_key(self):
#         self.ensure_one()
#         return (
#             self.order_id.id,
#             self.product_id.id,
#             self[UOM_FIELD].id,
#             self.price_unit,
#             self.discount,
#             tuple(sorted(self[TAX_FIELD].ids)),
#             self.name,
#         )
#
#     def _is_mergeable(self):
#         self.ensure_one()
#         return bool(
#             not self.display_type
#             and self.product_id
#             and self.order_id.state in ('draft', 'sent')
#             and not self.qty_delivered
#             and not self.qty_invoiced
#         )
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         raise UserError("CREATE IS WORKING")
#         lines = super().create(vals_list)
#         if not self.env.context.get('skip_merge'):
#             lines._merge_duplicates()
#         return lines.exists()
#
#     def write(self, vals):
#         res = super().write(vals)
#         watched = {'product_id', UOM_FIELD, 'price_unit', 'discount',
#                    TAX_FIELD, 'name', 'product_uom_qty'}
#         if watched & set(vals) and not self.env.context.get('skip_merge'):
#             self._merge_duplicates()
#         return res
#
#     def _merge_duplicates(self):
#         for order in self.mapped('order_id'):
#             lines = order.order_line.filtered(lambda l: l._is_mergeable())
#             groups = {}
#             for line in lines.sorted('id'):            # oldest line first
#                 groups.setdefault(line._merge_key(), self.browse())
#                 groups[line._merge_key()] |= line
#
#             for dup in groups.values():
#                 if len(dup) < 2:
#                     continue
#                 keep, extra = dup[0], dup[1:]
#                 total = sum(dup.mapped('product_uom_qty'))
#                 keep.with_context(skip_merge=True).product_uom_qty = total
#                 extra.with_context(skip_merge=True).unlink()