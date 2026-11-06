from odoo import _, api, fields, models
from odoo.exceptions import AccessError

APPROVER_GROUP = 'sale_credit_limit_approval.group_credit_limit_approver'

# Fields whose modification is restricted to approvers and restarts pending approvals.
CREDIT_LIMIT_FIELDS = ('partner_limit', 'partner_credit_limit', 'partner_credit_currency_id')

# States of sales orders whose approval must restart when the credit limit changes.
PENDING_APPROVAL_STATES = ('waiting_1', 'waiting_2', 'approved')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # Configuration fields
    # ------------------------------------------------------------------
    partner_limit = fields.Boolean(
        string="Partner Limit",
        tracking=True,
        help="Enable the credit check for this partner (customer or vendor). "
             "Sales Orders of this partner then go through the credit approval "
             "workflow before they can be confirmed.",
    )
    partner_credit_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string="Credit Limit Currency",
        default=lambda self: self.env.company.currency_id,
        help="Currency in which the credit limit is expressed. It is converted "
             "to the company currency of each Sales Order.",
    )
    partner_credit_limit = fields.Monetary(
        string="Credit Limit",
        currency_field='partner_credit_currency_id',
        tracking=True,
        help="Maximum amount this partner may owe on outstanding customer invoices "
             "plus the current quotation.",
    )

    # ------------------------------------------------------------------
    # Informative / UI fields (current company)
    # ------------------------------------------------------------------
    credit_company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_credit_amounts',
    )
    credit_outstanding_amount = fields.Monetary(
        string="Outstanding Invoices",
        currency_field='credit_company_currency_id',
        compute='_compute_credit_amounts',
        help="Unpaid residual of posted customer invoices minus open credit notes, "
             "in the current company's currency.",
    )
    credit_available_amount = fields.Monetary(
        string="Available Credit",
        currency_field='credit_company_currency_id',
        compute='_compute_credit_amounts',
        help="Credit Limit - Outstanding Invoices (current company).",
    )
    credit_managed_by_parent = fields.Boolean(
        compute='_compute_credit_managed_by_parent',
    )
    credit_limit_editable = fields.Boolean(
        compute='_compute_credit_limit_editable',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('parent_id', 'is_company', 'commercial_partner_id')
    def _compute_credit_managed_by_parent(self):
        for partner in self:
            partner.credit_managed_by_parent = (
                partner.commercial_partner_id._origin != partner._origin
                or (bool(partner.parent_id) and not partner.is_company)
            )

    @api.depends_context('uid')
    def _compute_credit_limit_editable(self):
        editable = self.env.su or self.env.user.has_group(APPROVER_GROUP)
        for partner in self:
            partner.credit_limit_editable = editable

    @api.depends_context('company')
    @api.depends(
        'commercial_partner_id',
        'commercial_partner_id.partner_limit',
        'commercial_partner_id.partner_credit_limit',
        'commercial_partner_id.partner_credit_currency_id',
    )
    def _compute_credit_amounts(self):
        company = self.env.company
        outstanding_map = self._credit_get_outstanding_map(self.commercial_partner_id, company)
        for partner in self:
            commercial = partner.commercial_partner_id
            outstanding = outstanding_map.get(commercial._origin.id, 0.0)
            partner.credit_company_currency_id = company.currency_id
            partner.credit_outstanding_amount = outstanding
            partner.credit_available_amount = (
                commercial._credit_get_limit_in_company_currency(company) - outstanding
                if commercial else -outstanding
            )

    # ------------------------------------------------------------------
    # Credit helpers (shared with sale.order)
    # ------------------------------------------------------------------
    @api.model
    def _credit_get_outstanding_map(self, commercial_partners, company):
        """Return {commercial_partner_id: outstanding amount in company currency}.

        Outstanding = sum of ``amount_residual_signed`` of POSTED customer invoices
        and credit notes of ``company``:

        * draft / cancelled moves are excluded (state = posted);
        * fully paid invoices have a zero residual and do not count;
        * partial payments are reflected in the residual;
        * unreconciled credit notes have a negative signed residual and reduce
          the total; credit notes reconciled with an invoice already reduced
          that invoice's residual, so nothing is counted twice;
        * ``amount_residual_signed`` is expressed in the company currency at the
          accounting rates of each move, so foreign-currency invoices are converted;
        * only moves of the given company are considered (multi-company).

        The aggregation runs as superuser on purpose: salespeople must get the
        correct total even if record rules hide some invoices from them; only the
        aggregate is exposed.
        """
        partner_ids = [pid for pid in {p._origin.id for p in commercial_partners} if pid]
        if not partner_ids or not company:
            return {}
        rows = self.env['account.move'].sudo()._read_group(
            domain=[
                ('commercial_partner_id', 'in', partner_ids),
                ('company_id', '=', company.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('amount_residual', '!=', 0.0),
            ],
            groupby=['commercial_partner_id'],
            aggregates=['amount_residual_signed:sum'],
        )
        return {partner.id: amount or 0.0 for partner, amount in rows}

    def _credit_get_limit_in_company_currency(self, company, date=None):
        """Credit limit of the commercial entity converted to ``company`` currency."""
        self.ensure_one()
        commercial = self.commercial_partner_id
        company_currency = company.currency_id
        limit_currency = commercial.partner_credit_currency_id or company_currency
        return limit_currency._convert(
            commercial.partner_credit_limit,
            company_currency,
            company,
            date or fields.Date.context_today(self),
        )

    def _credit_limit_snapshot(self):
        self.ensure_one()
        currency = self.partner_credit_currency_id
        amount = currency.round(self.partner_credit_limit) if currency else self.partner_credit_limit
        return (bool(self.partner_limit), currency.id, amount)

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and not self.env.user.has_group(APPROVER_GROUP):
            ctx = self.env.context
            for vals in vals_list:
                if (
                    vals.get('partner_limit', ctx.get('default_partner_limit'))
                    or vals.get('partner_credit_limit', ctx.get('default_partner_credit_limit'))
                ):
                    raise AccessError(_(
                        "Only Credit Limit Approvers can set a credit limit on a contact.",
                    ))
        return super().create(vals_list)

    def write(self, vals):
        if not set(CREDIT_LIMIT_FIELDS) & vals.keys():
            return super().write(vals)

        before = {partner.id: partner._credit_limit_snapshot() for partner in self}
        res = super().write(vals)
        changed = self.filtered(lambda p: p._credit_limit_snapshot() != before[p.id])
        if changed:
            if not self.env.su and not self.env.user.has_group(APPROVER_GROUP):
                raise AccessError(_(
                    "Only Credit Limit Approvers can change a contact's credit limit.",
                ))
            changed._credit_restart_pending_approvals()
        return res

    def _credit_restart_pending_approvals(self):
        """Credit limit changed: pending Sales Orders restart at Waiting for Approval 1.

        Only the commercial entity's limit is used by the credit check, so only
        changes on commercial entities affect orders.
        """
        commercials = self.filtered(lambda p: p.commercial_partner_id == p)
        if not commercials:
            return
        orders = self.env['sale.order'].sudo().search([
            ('partner_id.commercial_partner_id', 'in', commercials.ids),
            ('state', 'in', ('draft', 'sent')),
            ('credit_approval_state', 'in', PENDING_APPROVAL_STATES),
        ])
        orders._credit_restart_after_limit_change()
