from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    analytic_distribution_amount = fields.Json(
        string="Analytic Distribution Amounts",
        compute="_compute_analytic_distribution_amount",
        store=True,
        readonly=False,
        copy=True,
        help="Fixed amounts keyed by analytic accounts as entered in the "
             "Analytic Distribution widget (Amount mode). Computed from the "
             "untaxed subtotal. Percentages in analytic_distribution remain "
             "the source of truth for analytic entries at posting.",
    )

    @api.depends("analytic_distribution", "price_subtotal")
    def _compute_analytic_distribution_amount(self):
        for line in self:
            distribution = line.analytic_distribution or {}
            subtotal = line.price_subtotal or 0.0
            if not distribution:
                line.analytic_distribution_amount = False
                continue
            line.analytic_distribution_amount = {
                account_key: round((percentage or 0.0) / 100.0 * subtotal, 2)
                for account_key, percentage in distribution.items()
            }