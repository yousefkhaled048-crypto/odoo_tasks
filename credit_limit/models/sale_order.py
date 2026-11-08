from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    credit_check_enabled = fields.Boolean(
        related='partner_id.commercial_partner_id.credit_check',
    )

    credit_info_message = fields.Text(compute='_compute_credit_info_message')

    credit_exceeded = fields.Boolean(compute='_compute_credit_exceeded')

    credit_approved_1 = fields.Boolean(string='Approved 1', copy=False, default=False)
    credit_approved_2 = fields.Boolean(string='Approved 2', copy=False, default=False)

    credit_stage = fields.Selection(
        selection=[
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('approved_1', 'Approve 1'),
            ('approved_2', 'Approve 2'),
            ('sale', 'Sales Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        compute='_compute_credit_stage',
    )

    @api.depends('state', 'credit_approved_1', 'credit_approved_2')
    def _compute_credit_stage(self):
        for order in self:
            stage = order.state
            # Approval steps only apply while the order is still a quotation
            if order.state in ('draft', 'sent'):
                if order.credit_approved_2:
                    stage = 'approved_2'
                elif order.credit_approved_1:
                    stage = 'approved_1'
            order.credit_stage = stage

    @api.depends(
        'partner_id.commercial_partner_id.credit_check',
        'partner_id.commercial_partner_id.customer_credit_limit',
        'partner_id.commercial_partner_id.due_amount',
    )
    def _compute_credit_info_message(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id

            if not partner or not partner.credit_check:
                order.credit_info_message = False
                continue

            currency = partner.currency_id
            limit = formatLang(self.env, partner.customer_credit_limit, currency_obj=currency)
            due = formatLang(self.env, partner.due_amount, currency_obj=currency)

            order.credit_info_message = _(
                'Credit Limit for this customer is %(limit)s '
                'and Due Amount is %(due)s.',
                limit=limit,
                due=due,
            )

    @api.depends(
        'state',
        'amount_total',
        'partner_id.commercial_partner_id.credit_check',
        'partner_id.commercial_partner_id.customer_credit_limit',
        'partner_id.commercial_partner_id.due_amount',
    )
    def _compute_credit_exceeded(self):
        for order in self:
            partner = order.partner_id.commercial_partner_id

            # Only check quotations; no check if the customer has no Credit Check
            if order.state not in ('draft', 'sent') or not partner or not partner.credit_check:
                order.credit_exceeded = False
                continue

            available = partner.customer_credit_limit - partner.due_amount
            order.credit_exceeded = order.amount_total > available

    def action_credit_approve_1(self):
        for order in self:
            if not order.credit_exceeded:
                raise UserError(_('Approve 1 is only needed when the order exceeds the credit limit.'))
            order.credit_approved_1 = True

    def action_credit_approve_2(self):
        for order in self:
            if order.credit_exceeded and not order.credit_approved_1:
                raise UserError(_('Please do Approve 1 first.'))
            order.credit_approved_2 = True

    def action_confirm(self):
        if not self.env.context.get('skip_credit_approval'):
            for order in self:
                if order.credit_check_enabled and not order.credit_approved_2:
                    raise UserError(_('This order must be approved before confirming.'))
        return super().action_confirm()

    def write(self, vals):
        approval_keys = {'credit_approved_1', 'credit_approved_2'}
        if not (approval_keys & set(vals)) and ('partner_id' in vals or 'order_line' in vals):
            vals['credit_approved_1'] = False
            vals['credit_approved_2'] = False
        return super().write(vals)