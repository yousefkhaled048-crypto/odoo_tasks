from collections import defaultdict

from odoo import _, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if picking.state == 'done' and picking.picking_type_code == 'incoming':
                picking._create_hold_from_purchase_receipt()
        return res

    def _create_hold_from_purchase_receipt(self):
        self.ensure_one()
        Hold = self.env['hold.sequence'].sudo()
        # نمنع التكرار لو اتنده مرتين
        if Hold.search_count([('picking_id', '=', self.id)]):
            return

        # الكمية المستلمة لكل منتج، بوحدة قياس المنتج الأساسية
        totals = defaultdict(float)
        for move in self.move_ids:
            product = move.product_id
            if (move.state != 'done' or not move.purchase_line_id
                    or not product.is_storable):
                continue
            totals[product] += move.product_uom._compute_quantity(
                move.quantity, product.uom_id
            )

        lines = [
            (0, 0, {'product_id': product.id, 'hold_qty': qty})
            for product, qty in totals.items() if qty > 0
        ]
        if not lines:
            return

        hold = Hold.create({
            'picking_id': self.id,
            'company_id': self.company_id.id,
            'line_ids': lines,
        })
        # نأكد الـ Hold مباشرة من غير فحص الكمية، لأن البضاعة دخلت فعلًا
        hold.write({'state': 'confirmed'})
