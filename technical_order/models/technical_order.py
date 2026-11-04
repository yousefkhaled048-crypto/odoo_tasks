from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

LOCKED_STATES = ('approved', 'rejected', 'cancelled')
CONFIRMED_SALE_STATES = ('sale', 'done')
BUSINESS_FIELDS = {
    'request_name', 'requested_by', 'customer_id',
    'start_date', 'end_date', 'order_line_ids',
}


class TechnicalOrder(models.Model):
    _name = 'technical.order'
    _description = 'Technical Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    request_name = fields.Char(string='Request Name', required=True, tracking=True)
    requested_by = fields.Many2one(
        'res.users', string='Requested By', required=True, tracking=True,
        default=lambda self: self.env.user,
    )
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        domain=[('is_tech_offer', '=', True)],
    )
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date')
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False)
    order_line_ids = fields.One2many(
        'technical.order.line', 'technical_order_id', string='Order Lines', copy=True,
    )
    total_price = fields.Float(
        string='Total Price', compute='_compute_total_price', store=True,
        digits='Product Price',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('to_approve', 'To Be Approved'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status', default='draft', required=True, readonly=True,
        copy=False, tracking=True,
    )
    sale_order_ids = fields.One2many(
        'sale.order', 'technical_order_id', string='Sales Orders', readonly=True,
    )
    sale_order_count = fields.Integer(compute='_compute_sale_order_count')
    show_create_so = fields.Boolean(compute='_compute_show_create_so')

    # ------------------------------------------------------------------
    # Computes / constraints
    # ------------------------------------------------------------------
    @api.depends('order_line_ids.total')
    def _compute_total_price(self):
        for order in self:
            order.total_price = sum(order.order_line_ids.mapped('total'))

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for order in self:
            order.sale_order_count = len(order.sale_order_ids)

    @api.depends('state', 'order_line_ids.product_id', 'order_line_ids.quantity',
                 'sale_order_ids.state')
    def _compute_show_create_so(self):
        for order in self:
            order.show_create_so = bool(
                order.state == 'approved'
                and any(order._get_remaining_quantities().values())
            )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for order in self:
            if order.start_date and order.end_date and order.end_date < order.start_date:
                raise ValidationError(_("The end date cannot be before the start date."))

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('technical.order') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        # Server-side counterpart of the readonly attributes of the form view.
        if BUSINESS_FIELDS.intersection(vals) and any(
                order.state in LOCKED_STATES for order in self):
            raise UserError(_(
                "Approved, rejected or cancelled technical orders cannot be modified."))
        return super().write(vals)

    def unlink(self):
        if any(order.state not in ('draft', 'cancelled') for order in self):
            raise UserError(_("Only draft or cancelled technical orders can be deleted."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _check_state(self, expected):
        for order in self:
            if order.state != expected:
                raise UserError(_(
                    "%(name)s must be in state '%(state)s' for this action.",
                    name=order.name, state=dict(self._fields['state'].selection)[expected]))

    def action_submit(self):
        self._check_state('draft')
        for order in self:
            if not order.order_line_ids:
                raise UserError(_("Please add at least one line to %s.", order.name))
        self.write({'state': 'to_approve'})

    def action_cancel(self):
        self._check_state('draft')
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self._check_state('cancelled')
        self.write({'state': 'draft'})

    def action_approve(self):
        self._check_state('to_approve')
        self.write({'state': 'approved'})
        self._notify_sales_managers_approved()

    def action_reject(self):
        self.ensure_one()
        self._check_state('to_approve')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Technical Order'),
            'res_model': 'technical.order.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_technical_order_id': self.id},
        }

    def _notify_sales_managers_approved(self):
        template = self.env.ref('technical_order.mail_template_technical_order_approved')
        group = self.env.ref('sales_team.group_sale_manager')
        managers = self.env['res.users'].search([
            ('groups_id', 'in', group.ids),
            ('share', '=', False),
            ('partner_id.email', '!=', False),
        ])
        if not managers:
            return
        email_to = ','.join(managers.partner_id.mapped('email_formatted'))
        for order in self:
            # Queued (force_send=False): an SMTP problem never blocks the approval.
            template.send_mail(order.id, force_send=False, email_values={'email_to': email_to})
            order.message_post(
                body=_("Approval notification sent to: %s",
                       ', '.join(managers.mapped('name'))),
                subtype_xmlid='mail.mt_note',
            )

    # ------------------------------------------------------------------
    # Quantity logic (requested / consumed / remaining)
    # ------------------------------------------------------------------
    def _get_requested_quantities(self):
        """{product: requested quantity}, in the product's own UoM."""
        self.ensure_one()
        requested = defaultdict(float)
        for line in self.order_line_ids:
            requested[line.product_id] += line.quantity
        return requested

    @api.model
    def _sum_sale_lines_quantities(self, lines):
        """{product: quantity} of sale lines, converted to the product UoM.
        Section/note/display lines and non-countable lines are ignored."""
        totals = defaultdict(float)
        for line in lines:
            if not line._is_technical_order_countable():
                continue
            product = line.product_id
            totals[product] += line.product_uom._compute_quantity(
                line.product_uom_qty, product.uom_id)
        return totals

    def _get_consumed_quantities(self, exclude_orders=None):
        """Quantities already used by CONFIRMED sales orders only
        (draft, sent and cancelled orders are ignored)."""
        self.ensure_one()
        origin = self._origin
        if not origin:
            return defaultdict(float)
        domain = [
            ('order_id.technical_order_id', '=', origin.id),
            ('order_id.state', 'in', CONFIRMED_SALE_STATES),
        ]
        if exclude_orders:
            domain.append(('order_id', 'not in', exclude_orders.ids))
        # sudo() is deliberate and read-only: consumption must include the confirmed
        # orders of every salesperson, even those hidden from the current user by
        # record rules, otherwise the quantity check could be bypassed.
        lines = self.env['sale.order.line'].sudo().search(domain)
        return self._sum_sale_lines_quantities(lines)

    def _get_remaining_quantities(self):
        """{product: remaining quantity}, never negative."""
        self.ensure_one()
        consumed = self._get_consumed_quantities()
        remaining = {}
        for product, requested in self._get_requested_quantities().items():
            rest = requested - consumed.get(product, 0.0)
            if float_compare(rest, 0.0, precision_rounding=product.uom_id.rounding) > 0:
                remaining[product] = rest
            else:
                remaining[product] = 0.0
        return remaining

    def _lock_for_update(self):
        """Serialize concurrent confirmations linked to the same technical order.
        The no-op UPDATE takes the row lock; a concurrent transaction that touched
        the row first makes this one fail with a serialization error, which Odoo
        retries automatically, so the quantities are re-read after the other
        confirmation is committed."""
        self.env.cr.execute(
            f'UPDATE "{self._table}" SET write_date = write_date WHERE id IN %s',
            [tuple(self.ids)],
        )

    def _check_sale_quantities(self, orders):
        """Raise if confirming `orders` (sale orders linked to self) would consume
        more than the requested quantities."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_(
                "Technical Order %s is not approved: its sales orders cannot be confirmed.",
                self.name))
        self._lock_for_update()
        requested = self._get_requested_quantities()
        consumed = self._get_consumed_quantities(exclude_orders=orders)
        current = self._sum_sale_lines_quantities(orders.order_line)
        errors = []
        for product, quantity in current.items():
            requested_qty = requested.get(product, 0.0)
            already = consumed.get(product, 0.0)
            if float_compare(already + quantity, requested_qty,
                             precision_rounding=product.uom_id.rounding) > 0:
                errors.append(_(
                    "- %(product)s: requested %(requested)s, already confirmed %(already)s, "
                    "this order %(current)s, remaining %(remaining)s (%(uom)s).",
                    product=product.display_name, requested=requested_qty,
                    already=already, current=quantity,
                    remaining=max(requested_qty - already, 0.0), uom=product.uom_id.name))
        if errors:
            raise UserError(_(
                "Cannot confirm: the quantities exceed Technical Order %(name)s.\n%(errors)s",
                name=self.name, errors="\n".join(errors)))

    # ------------------------------------------------------------------
    # Sales order integration
    # ------------------------------------------------------------------
    def action_create_so(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("Sales orders can only be created from approved technical orders."))
        remaining = self._get_remaining_quantities()
        line_commands = []
        for line in self.order_line_ids:
            product = line.product_id
            qty = min(line.quantity, remaining.get(product, 0.0))
            if float_compare(qty, 0.0, precision_rounding=product.uom_id.rounding) <= 0:
                continue
            remaining[product] -= qty
            line_commands.append(Command.create({
                'product_id': product.id,
                'name': line.description or product.display_name,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'price_unit': line.price,
            }))
        if not line_commands:
            raise UserError(_("All requested quantities have already been consumed."))
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'technical_order_id': self.id,
            'origin': self.name,
            'order_line': line_commands,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('technical_order_id', '=', self.id)],
            'context': {'create': False},
        }