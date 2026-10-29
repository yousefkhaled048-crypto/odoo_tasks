from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    analytic_distribution_amount = fields.Json(
        string="Analytic Distribution Amounts",
        compute="_compute_analytic_distribution_amount",
        store=True,
        readonly=False,
        copy=True,
        help="Fixed amounts keyed by analytic accounts as entered in the "
             "Analytic Distribution widget (Amount mode). Computed from the "
             "untaxed amount. Percentages in analytic_distribution remain "
             "the source of truth for analytic entries at posting.",
    )

    @api.depends("analytic_distribution", "untaxed_amount_currency")
    def _compute_analytic_distribution_amount(self):
        for expense in self:
            distribution = expense.analytic_distribution or {}
            subtotal = expense.untaxed_amount_currency or 0.0
            if not distribution:
                expense.analytic_distribution_amount = False
                continue
            expense.analytic_distribution_amount = {
                account_key: round((percentage or 0.0) / 100.0 * subtotal, 2)
                for account_key, percentage in distribution.items()
            }