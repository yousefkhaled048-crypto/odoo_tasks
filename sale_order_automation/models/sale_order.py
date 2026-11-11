from odoo import _, api, fields, models
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_automated = fields.Boolean(
        string='Automated',
        copy=False,
        readonly=True,
        help='Set when the order was processed by the Automate Sale Order button.',
    )
    payment_ids = fields.Many2many(
        comodel_name='account.payment',
        string='Payments',
        compute='_compute_payment_ids',
    )
    payment_count = fields.Integer(
        string='Payment Count',
        compute='_compute_payment_ids',
    )

    @api.depends('invoice_ids', 'invoice_ids.payment_state')
    def _compute_payment_ids(self):
        for order in self:
            payments = order.invoice_ids._get_reconciled_payments()
            order.payment_ids = payments
            order.payment_count = len(payments)

    def action_view_payments(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_account_payments'
        )
        if len(self.payment_ids) == 1:
            action.update({
                'views': [(False, 'form')],
                'res_id': self.payment_ids.id,
            })
        else:
            action['domain'] = [('id', 'in', self.payment_ids.ids)]
        return action

    # -------------------------------------------------------------------------
    # VALIDATIONS
    # -------------------------------------------------------------------------
    def _check_automation_requirements(self):
        self.ensure_one()
        self._check_customer()
        self._check_order_lines()
        self._check_stock_availability()
        self._get_payment_journal()  # raises if none exists

    def _check_customer(self):
        if not self.partner_id:
            raise UserError(_("Please select a customer before automating the order."))

    def _check_order_lines(self):
        product_lines = self.order_line.filtered(
            lambda line: not line.display_type and line.product_id
        )
        if not product_lines:
            raise UserError(_("Please add at least one product to the order."))

    def _check_stock_availability(self):
        self.ensure_one()
        required = {}
        for line in self.order_line.filtered(
            lambda l: not l.display_type and l.product_id.is_storable
        ):
            product = line.product_id
            qty = line.product_uom_id._compute_quantity(
                line.product_uom_qty, product.uom_id
            )
            required[product] = required.get(product, 0.0) + qty

        for product, qty in required.items():
            available = product.with_context(
                warehouse_id=self.warehouse_id.id
            ).free_qty
            if qty > available:
                raise UserError(_(
                    "Not enough stock for product '%(product)s'.\n"
                    "Required: %(required)s, Available: %(available)s",
                    product=product.display_name,
                    required=qty,
                    available=available,
                ))

    def _get_payment_journal(self):
        self.ensure_one()
        journal = self.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', self.company_id.id),
            ('inbound_payment_method_line_ids', '!=', False),
        ], limit=1)
        if not journal:
            raise UserError(_(
                "No accounting journal (Bank or Cash) is available to register the payment."
            ))
        return journal

    # -------------------------------------------------------------------------
    # AUTOMATION
    # -------------------------------------------------------------------------
    def action_automate_sale_order(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_("Only quotations can be automated."))

            order._check_automation_requirements()

            order._automation_confirm_order()
            order._automation_validate_deliveries()
            invoices = order._automation_create_invoices()
            order._automation_post_invoices(invoices)
            order._automation_register_payments(invoices)

            order.is_automated = True
        return True

    def _automation_confirm_order(self):
        self.ensure_one()
        self.action_confirm()

    def _automation_validate_deliveries(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel')
        )
        for picking in pickings:
            picking.action_assign()  # reserve the quantities
            if picking.state != 'assigned':
                raise UserError(_(
                    "Delivery %(picking)s could not be fully reserved.",
                    picking=picking.name,
                ))
            result = picking.with_context(
                skip_backorder=True,
                skip_sms=True,
            ).button_validate()
            self._automation_process_wizard(result)
            if picking.state != 'done':
                raise UserError(_(
                    "Delivery %(picking)s could not be validated.",
                    picking=picking.name,
                ))

    def _automation_process_wizard(self, result):
        if not isinstance(result, dict) or not result.get('res_model'):
            return
        wizard = self.env[result['res_model']].with_context(
            **result.get('context', {})
        ).create({})
        if hasattr(wizard, 'process'):
            wizard.process()

    def _automation_create_invoices(self):
        self.ensure_one()
        invoices = self._create_invoices(final=True)
        if not invoices:
            raise UserError(_("No invoice could be generated for this order."))
        return invoices

    def _automation_post_invoices(self, invoices):
        invoices.filtered(lambda m: m.state == 'draft').action_post()

    def _automation_register_payments(self, invoices):
        self.ensure_one()
        journal = self._get_payment_journal()
        for invoice in invoices:
            self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=invoice.ids,
            ).create({
                'journal_id': journal.id,
            })._create_payments()