# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    analytic_distribution_amount = fields.Json(
        string="Analytic Distribution Amounts",
        compute="_compute_analytic_distribution_amount",
        store=True,
        readonly=False,
        copy=True,
        help="Fixed amounts of the analytic distribution, per analytic account, "
             "computed on the untaxed subtotal of the line. Amounts can be entered "
             "in the Analytic Distribution widget (Amount mode) and are kept in "
             "sync with the percentages stored in 'Analytic Distribution', which "
             "remain the source of truth used by Odoo when posting the analytic "
             "entries.",
    )

    @api.depends("analytic_distribution", "price_subtotal")
    def _compute_analytic_distribution_amount(self):
        """Derive the fixed amounts from the distribution percentages.

        The percentages of ``analytic_distribution`` remain the source of truth
        for posting analytic entries. This field stores the equivalent fixed
        amounts (percentage / 100 * untaxed subtotal). It is written directly by
        the widget when the user enters amounts in the popup; it is recomputed
        here whenever the distribution or the untaxed subtotal changes (e.g.
        after a quantity or unit price update), so it can never drift away from
        the stored percentages.
        """
        for line in self:
            distribution = line.analytic_distribution or {}
            subtotal = line.price_subtotal or 0.0
            if not distribution:
                line.analytic_distribution_amount = False
                continue
            line.analytic_distribution_amount = {
                account_key: round(percentage / 100.0 * subtotal, 2)
                for account_key, percentage in distribution.items()
            }