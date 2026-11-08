from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_check = fields.Boolean(
        string='Credit Check',
    )

    customer_credit_limit = fields.Monetary(
        string='Customer Credit Limit',
        currency_field='currency_id',
    )

    due_amount = fields.Monetary(
        string='Due Amount',
        compute='_compute_due_amount',
        currency_field='currency_id',
    )

    @api.depends('credit')
    def _compute_due_amount(self):
        SaleOrder = self.env['sale.order']
        for partner in self:
            commercial = partner.commercial_partner_id

            # 1) Posted invoices not paid yet (standard receivable of the customer)
            unpaid_invoices = commercial.credit

            # 2) Confirmed sale orders that are not invoiced yet
            orders = SaleOrder.search([
                ('partner_id', 'child_of', commercial.id),
                ('state', '=', 'sale'),
            ])
            not_invoiced = sum(orders.mapped('amount_to_invoice'))

            partner.due_amount = unpaid_invoices + not_invoiced