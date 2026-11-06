from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .res_partner import APPROVER_GROUP

CREDIT_APPROVAL_STATES = [
    ('draft', "Draft"),
    ('waiting_1', "Waiting for Approval 1"),
    ('waiting_2', "Waiting for Approval 2"),
    ('approved', "Approved"),
    ('rejected', "Rejected"),
    ('cancelled', "Cancelled"),
]

CREDIT_STATUS = [
    ('within', "Within Limit"),
    ('exceeded', "Exceeded Limit"),
]

# Sales order states in which the credit workflow is active.
OPEN_ORDER_STATES = ('draft', 'sent')

# Approval states that represent work in progress or a granted approval.
IN_PROGRESS_APPROVAL_STATES = ('waiting_1', 'waiting_2', 'approved')

# Only the workflow methods (running as superuser) may write these fields.
CREDIT_PROTECTED_FIELDS = frozenset({
    'credit_approval_state',
    'credit_approver_1_id',
    'credit_approval_1_date',
    'credit_approver_2_id',
    'credit_approval_2_date',
    'credit_approved_amount',
    'credit_rejected_by_id',
    'credit_rejection_date',
})

# Writing one of these fields may change the credit exposure of the order.
CREDIT_SENSITIVE_FIELDS = frozenset({
    'order_line', 'partner_id', 'company_id', 'currency_id', 'pricelist_id',
})


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Approval workflow (stored)
    # ------------------------------------------------------------------
    credit_approval_state = fields.Selection(
        selection=CREDIT_APPROVAL_STATES,
        string="Credit Approval",
        default='draft',
        required=True,
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
    )
    credit_approver_1_id = fields.Many2one(
        'res.users', string="Approved 1 By", readonly=True, copy=False, tracking=True)
    credit_approval_1_date = fields.Datetime(
        string="Approval 1 Date", readonly=True, copy=False)
    credit_approver_2_id = fields.Many2one(
        'res.users', string="Approved 2 By", readonly=True, copy=False, tracking=True)
    credit_approval_2_date = fields.Datetime(
        string="Approval 2 Date", readonly=True, copy=False)
    credit_rejected_by_id = fields.Many2one(
        'res.users', string="Rejected By", readonly=True, copy=False, tracking=True)
    credit_rejection_date = fields.Datetime(
        string="Rejection Date", readonly=True, copy=False)
    credit_approved_amount = fields.Monetary(
        string="Approved Order Total",
        currency_field='currency_id',
        readonly=True,
        copy=False,
        help="Order total at the time of the final approval. Confirmation is "
             "blocked if the order total grows beyond this amount.",
    )

    # ------------------------------------------------------------------
    # Credit information (computed, company currency of the order)
    # ------------------------------------------------------------------
    credit_currency_id = fields.Many2one(
        'res.currency', string="Credit Currency", compute='_compute_credit_info')
    credit_check_required = fields.Boolean(
        string="Credit Check", compute='_compute_credit_info')
    credit_limit_amount = fields.Monetary(
        string="Credit Limit", currency_field='credit_currency_id',
        compute='_compute_credit_info')
    credit_outstanding_amount = fields.Monetary(
        string="Outstanding Invoices", currency_field='credit_currency_id',
        compute='_compute_credit_info')
    credit_available_amount = fields.Monetary(
        string="Available Credit", currency_field='credit_currency_id',
        compute='_compute_credit_info')
    credit_order_amount = fields.Monetary(
        string="Current Quotation Amount", currency_field='credit_currency_id',
        compute='_compute_credit_info')
    credit_exposure_amount = fields.Monetary(
        string="Potential Exposure", currency_field='credit_currency_id',
        compute='_compute_credit_info')
    credit_status = fields.Selection(
        selection=CREDIT_STATUS, string="Credit Status", compute='_compute_credit_info')

    # ------------------------------------------------------------------
    # UI helpers (button visibility mirrors the backend rules)
    # ------------------------------------------------------------------
    credit_can_request = fields.Boolean(compute='_compute_credit_actions')
    credit_can_approve_1 = fields.Boolean(compute='_compute_credit_actions')
    credit_show_approve_1_disabled = fields.Boolean(compute='_compute_credit_actions')
    credit_can_approve_2 = fields.Boolean(compute='_compute_credit_actions')
    credit_can_reject = fields.Boolean(compute='_compute_credit_actions')
    credit_can_reset = fields.Boolean(compute='_compute_credit_actions')
    credit_confirm_blocked = fields.Boolean(compute='_compute_credit_actions')
    credit_next_step = fields.Char(string="Next Step", compute='_compute_credit_actions')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends(
        'partner_id',
        'partner_id.commercial_partner_id',
        'partner_id.commercial_partner_id.partner_limit',
        'partner_id.commercial_partner_id.partner_credit_limit',
        'partner_id.commercial_partner_id.partner_credit_currency_id',
        'company_id',
        'currency_id',
        'date_order',
        'state',
        'amount_total',
        'amount_invoiced',
    )
    def _compute_credit_info(self):
        today = fields.Date.context_today(self)
        outstanding_cache = {}
        for order in self:
            company = order.company_id or self.env.company
            company_currency = company.currency_id
            commercial = order.partner_id.commercial_partner_id
            order.credit_currency_id = company_currency

            if not commercial or not commercial.partner_limit:
                order.credit_check_required = False
                order.credit_limit_amount = 0.0
                order.credit_outstanding_amount = 0.0
                order.credit_available_amount = 0.0
                order.credit_order_amount = 0.0
                order.credit_exposure_amount = 0.0
                order.credit_status = False
                continue

            key = (commercial._origin.id, company.id)
            if key not in outstanding_cache:
                outstanding_cache[key] = self.env['res.partner']._credit_get_outstanding_map(
                    commercial, company,
                ).get(commercial._origin.id, 0.0)
            outstanding = outstanding_cache[key]
            limit = commercial._credit_get_limit_in_company_currency(company, today)
            order_amount = order._credit_get_order_amount(company)
            exposure = outstanding + order_amount

            order.credit_check_required = True
            order.credit_limit_amount = limit
            order.credit_outstanding_amount = outstanding
            order.credit_available_amount = limit - outstanding
            order.credit_order_amount = order_amount
            order.credit_exposure_amount = exposure
            order.credit_status = (
                'exceeded' if company_currency.compare_amounts(exposure, limit) > 0 else 'within'
            )

    def _credit_get_order_amount(self, company):
        """Amount of this order not yet in posted invoices, in company currency.

        For quotations this is the full total. For confirmed orders the part that
        was already invoiced is subtracted, because it is counted in the
        outstanding invoices (no double counting).
        """
        self.ensure_one()
        if self.state == 'cancel':
            return 0.0
        amount = self.amount_total
        if self.state == 'sale':
            amount = max(amount - self.amount_invoiced, 0.0)
        currency = self.currency_id or company.currency_id
        date = fields.Date.to_date(self.date_order) if self.date_order else fields.Date.context_today(self)
        return currency._convert(amount, company.currency_id, company, date)

    @api.depends(
        'credit_check_required',
        'credit_status',
        'credit_approval_state',
        'credit_approver_1_id',
        'credit_approved_amount',
        'amount_total',
        'currency_id',
        'state',
    )
    def _compute_credit_actions(self):
        for order in self:
            order.credit_can_request = order._credit_can_request()
            order.credit_can_approve_1 = order._credit_can_approve_1()
            order.credit_show_approve_1_disabled = (
                order.credit_check_required
                and order.state in OPEN_ORDER_STATES
                and order.credit_approval_state == 'draft'
                and order.credit_status == 'within'
            )
            order.credit_can_approve_2 = order._credit_can_approve_2()
            order.credit_can_reject = order._credit_can_reject()
            order.credit_can_reset = order._credit_can_reset()
            order.credit_confirm_blocked = bool(order._credit_confirmation_block_reason())
            order.credit_next_step = order._credit_get_next_step()

    # ------------------------------------------------------------------
    # Workflow rules (single source of truth for UI and backend)
    # ------------------------------------------------------------------
    def _credit_is_open(self):
        self.ensure_one()
        return self.credit_check_required and self.state in OPEN_ORDER_STATES

    def _credit_can_request(self):
        self.ensure_one()
        return (
            self._credit_is_open()
            and self.credit_status == 'exceeded'
            and self.credit_approval_state == 'draft'
        )

    def _credit_can_approve_1(self):
        self.ensure_one()
        return self._credit_is_open() and self.credit_approval_state == 'waiting_1'

    def _credit_can_approve_2(self):
        self.ensure_one()
        return self._credit_is_open() and (
            self.credit_approval_state == 'waiting_2'
            or (self.credit_approval_state == 'draft' and self.credit_status == 'within')
        )

    def _credit_can_reject(self):
        self.ensure_one()
        return self._credit_is_open() and self.credit_approval_state in ('waiting_1', 'waiting_2')

    def _credit_can_reset(self):
        self.ensure_one()
        if self.state not in OPEN_ORDER_STATES:
            return False
        if self.credit_approval_state == 'rejected':
            return True
        return self.credit_approval_state == 'approved' and bool(self._credit_confirmation_block_reason())

    def _credit_confirmation_block_reason(self):
        """Return why the order cannot be confirmed yet, or False."""
        self.ensure_one()
        if not self._credit_is_open():
            return False
        if self.credit_approval_state != 'approved':
            return _(
                "Sales Order %(order)s is subject to a credit check and must be approved "
                "before confirmation (current credit approval status: %(status)s).",
                order=self.name,
                status=dict(
                    self._fields['credit_approval_state']._description_selection(self.env),
                ).get(self.credit_approval_state, self.credit_approval_state),
            )
        if self.credit_status == 'exceeded' and not self.credit_approver_1_id:
            return _(
                "Sales Order %(order)s was approved while within the credit limit, but the "
                "customer's exposure now exceeds it. Reset the approval and request a new "
                "approval (Approve 1 and Approve 2).",
                order=self.name,
            )
        if self.currency_id.compare_amounts(self.amount_total, self.credit_approved_amount) > 0:
            return _(
                "The total of Sales Order %(order)s increased after it was approved. "
                "Reset the approval and have it approved again.",
                order=self.name,
            )
        return False

    def _credit_get_next_step(self):
        self.ensure_one()
        if not self.credit_check_required:
            return False
        if self.state == 'sale':
            return _("Order confirmed.")
        if self.state == 'cancel' or self.credit_approval_state == 'cancelled':
            return _("Order cancelled.")
        state = self.credit_approval_state
        if state == 'draft':
            if self.credit_status == 'within':
                return _("Within limit: Approve 2 by a Credit Limit Approver is required before confirmation.")
            return _("Limit exceeded: click Request Approval to start the approval process.")
        if state == 'waiting_1':
            return _("Waiting for Approve 1 by a Credit Limit Approver.")
        if state == 'waiting_2':
            return _("Approve 1 done. Waiting for Approve 2 by a Credit Limit Approver.")
        if state == 'rejected':
            return _("Approval rejected. Adjust the order, then click Reset Approval.")
        if state == 'approved':
            reason = self._credit_confirmation_block_reason()
            return reason or _("Approved: the order can be confirmed.")
        return False

    def _credit_reset_values(self, state):
        return {
            'credit_approval_state': state,
            'credit_approver_1_id': False,
            'credit_approval_1_date': False,
            'credit_approver_2_id': False,
            'credit_approval_2_date': False,
            'credit_approved_amount': 0.0,
            'credit_rejected_by_id': False,
            'credit_rejection_date': False,
        }

    def _credit_write(self, vals):
        """Write workflow fields. Runs as superuser so that the protection in
        ``write`` (which refuses these fields from normal users) is bypassed only
        by the workflow itself; callers must have checked rights beforehand."""
        return self.sudo().write(vals)

    def _credit_check_approver(self):
        if not self.env.su and not self.env.user.has_group(APPROVER_GROUP):
            raise AccessError(_(
                "Only members of the 'Credit Limit Approval / Approver' group can "
                "approve or reject credit approvals.",
            ))

    def _credit_amount_str(self, amount):
        self.ensure_one()
        return self.credit_currency_id.format(amount) if self.credit_currency_id else str(amount)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_credit_request_approval(self):
        self.check_access('write')
        for order in self:
            if not order._credit_can_request():
                raise UserError(_(
                    "Approval can only be requested for a quotation in Draft credit approval "
                    "status whose potential exposure exceeds the credit limit (%(order)s).",
                    order=order.name,
                ))
            order._credit_write(order._credit_reset_values('waiting_1'))
            order.message_post(body=_(
                "Credit approval requested: potential exposure %(exposure)s exceeds the "
                "credit limit %(limit)s.",
                exposure=order._credit_amount_str(order.credit_exposure_amount),
                limit=order._credit_amount_str(order.credit_limit_amount),
            ))
        return True

    def action_credit_approve_1(self):
        self._credit_check_approver()
        self.check_access('write')
        for order in self:
            if not order._credit_can_approve_1():
                raise UserError(_(
                    "Approve 1 is only possible when the order is Waiting for Approval 1 (%(order)s).",
                    order=order.name,
                ))
            order._credit_write({
                'credit_approval_state': 'waiting_2',
                'credit_approver_1_id': self.env.uid,
                'credit_approval_1_date': fields.Datetime.now(),
            })
            order.message_post(body=_("Credit Approval 1 granted."))
        return True

    def action_credit_approve_2(self):
        self._credit_check_approver()
        self.check_access('write')
        for order in self:
            if not order._credit_can_approve_2():
                raise UserError(_(
                    "Approve 2 is only possible after Approve 1 (Waiting for Approval 2), or "
                    "directly from Draft when the order is within the credit limit (%(order)s).",
                    order=order.name,
                ))
            order._credit_write({
                'credit_approval_state': 'approved',
                'credit_approver_2_id': self.env.uid,
                'credit_approval_2_date': fields.Datetime.now(),
                'credit_approved_amount': order.amount_total,
            })
            order.message_post(body=_("Credit Approval 2 granted. The order can now be confirmed."))
        return True

    def action_credit_reject(self):
        self._credit_check_approver()
        self.check_access('write')
        for order in self:
            if not order._credit_can_reject():
                raise UserError(_(
                    "Only orders waiting for Approval 1 or Approval 2 can be rejected (%(order)s).",
                    order=order.name,
                ))
            order._credit_write({
                'credit_approval_state': 'rejected',
                'credit_rejected_by_id': self.env.uid,
                'credit_rejection_date': fields.Datetime.now(),
            })
            order.message_post(body=_("Credit approval rejected."))
        return True

    def action_credit_reset_approval(self):
        self.check_access('write')
        for order in self:
            if not order._credit_can_reset():
                raise UserError(_(
                    "The credit approval of %(order)s cannot be reset in its current status.",
                    order=order.name,
                ))
            order._credit_write(order._credit_reset_values('draft'))
            order.message_post(body=_("Credit approval reset to Draft."))
        return True

    def _credit_restart_after_limit_change(self):
        """Called when the partner's credit limit changes (see res.partner)."""
        for order in self:
            new_state = 'waiting_1' if order.credit_check_required else 'draft'
            order._credit_write(order._credit_reset_values(new_state))
            if new_state == 'waiting_1':
                body = _("The customer's credit limit was modified: the credit approval restarts "
                         "at Waiting for Approval 1.")
            else:
                body = _("The customer's credit check was disabled: the credit approval was reset.")
            order.message_post(body=body)

    # ------------------------------------------------------------------
    # Sale flow overrides
    # ------------------------------------------------------------------
    def _confirmation_error_message(self):
        error = super()._confirmation_error_message()
        if error:
            return error
        return self._credit_confirmation_block_reason()

    def _validate_order(self):
        """Portal signature: keep the quotation open when credit approval is missing
        instead of failing the customer's signature."""
        blocked = self.filtered(lambda o: o._credit_confirmation_block_reason())
        for order in blocked:
            order.message_post(body=_(
                "The customer validated the quotation online, but confirmation is on hold "
                "until the credit approval is completed.",
            ))
        remaining = self - blocked
        if remaining:
            return super(SaleOrder, remaining)._validate_order()
        return None

    def _action_cancel(self):
        res = super()._action_cancel()
        cancelled = self.filtered(lambda o: o.state == 'cancel' and o.credit_approval_state != 'cancelled')
        if cancelled:
            cancelled._credit_write({'credit_approval_state': 'cancelled'})
        return res

    def action_draft(self):
        cancelled = self.filtered(lambda o: o.state == 'cancel')
        res = super().action_draft()
        restored = cancelled.filtered(lambda o: o.state == 'draft')
        if restored:
            restored._credit_write(self._credit_reset_values('draft'))
        return res

    # ------------------------------------------------------------------
    # ORM overrides: protect workflow fields, invalidate stale approvals
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                forbidden = [
                    fname for fname in CREDIT_PROTECTED_FIELDS & vals.keys()
                    if vals[fname] and not (fname == 'credit_approval_state' and vals[fname] == 'draft')
                ]
                if forbidden:
                    raise AccessError(_("Credit approval fields can only be set by the approval workflow."))
            # Also ignore context defaults (default_credit_approval_state=...) sent by clients.
            context = {
                key: value for key, value in self.env.context.items()
                if not (key.startswith('default_') and key[len('default_'):] in CREDIT_PROTECTED_FIELDS)
            }
            if len(context) != len(self.env.context):
                return self.with_context(context).create(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and CREDIT_PROTECTED_FIELDS & vals.keys():
            raise AccessError(_(
                "Credit approval fields can only be changed through the approval buttons.",
            ))

        snapshots = {}
        if CREDIT_SENSITIVE_FIELDS & vals.keys():
            snapshots = {
                order.id: order._credit_exposure_snapshot()
                for order in self
                if order.state in OPEN_ORDER_STATES
                and order.credit_approval_state in IN_PROGRESS_APPROVAL_STATES
            }

        res = super().write(vals)

        if snapshots:
            stale = self.filtered(
                lambda o: o.id in snapshots
                and o.state in OPEN_ORDER_STATES
                and o._credit_exposure_increased(snapshots[o.id]),
            )
            for order in stale:
                order._credit_write(order._credit_reset_values('draft'))
                order.message_post(body=_(
                    "The order was modified (higher total, other customer, company or "
                    "currency): the credit approval was reset to Draft.",
                ))
        return res

    def _credit_exposure_snapshot(self):
        self.ensure_one()
        return (
            self.partner_id.commercial_partner_id.id,
            self.company_id.id,
            self.currency_id.id,
            self.amount_total,
        )

    def _credit_exposure_increased(self, snapshot):
        self.ensure_one()
        partner_id, company_id, currency_id, amount_total = snapshot
        if (
            self.partner_id.commercial_partner_id.id != partner_id
            or self.company_id.id != company_id
            or self.currency_id.id != currency_id
        ):
            return True
        return self.currency_id.compare_amounts(self.amount_total, amount_total) > 0
