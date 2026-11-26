from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    item_no = fields.Char(
        string='Item No', related='product_id.default_code',
        store=True, readonly=True)
    barcode_no = fields.Char(
        string='Barcode No', related='product_id.barcode',
        store=True, readonly=True)
    tests = fields.Char(string='Tests')

    discount_1 = fields.Float(string='D1', digits=(16, 2))
    discount_2 = fields.Float(string='D2', digits=(16, 2))

    vat_rate = fields.Float(string='VAT %', default=15.0)
    vat_amount = fields.Monetary(
        string='VAT 15%', compute='_compute_custom_vat',
        store=True, currency_field='currency_id')
    amount_with_vat = fields.Monetary(
        string='Amount', compute='_compute_custom_vat',
        store=True, currency_field='currency_id')

    @api.constrains('discount_1', 'discount_2')
    def _check_custom_discounts(self):
        for line in self:
            if not 0 <= line.discount_1 <= 100:
                raise ValidationError('Discount 1 must be between 0 and 100%.')
            if not 0 <= line.discount_2 <= 100:
                raise ValidationError('Discount 2 must be between 0 and 100%.')

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty',
                 'discount_1', 'discount_2')
    def _compute_discount(self):
        # 1) Reset: no old D1/D2 effect can ever be compounded again
        for line in self:
            line.discount = 0.0

        # 2) Standard Odoo (sets a value only if a pricelist rule gives a discount)
        super()._compute_discount()

        # 3) Apply D1 then D2 on top of the clean pricelist discount
        for line in self:
            if line.display_type:
                continue
            d1 = line.discount_1 or 0.0
            d2 = line.discount_2 or 0.0
            pricelist_discount = line.discount or 0.0
            factor = (1 - pricelist_discount / 100.0) \
                * (1 - d1 / 100.0) * (1 - d2 / 100.0)
            line.discount = 100.0 * (1 - factor)

    @api.depends('price_subtotal', 'vat_rate', 'currency_id')
    def _compute_custom_vat(self):
        for line in self:
            if line.display_type:
                line.vat_amount = 0.0
                line.amount_with_vat = 0.0
                continue
            subtotal = line.price_subtotal or 0.0
            vat = line.currency_id.round(subtotal * (line.vat_rate or 0.0) / 100.0)
            line.vat_amount = vat
            line.amount_with_vat = line.currency_id.round(subtotal + vat)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    custom_untaxed_total = fields.Monetary(
        string='Total Before VAT', compute='_compute_custom_totals',
        store=True, currency_field='currency_id')
    custom_vat_total = fields.Monetary(
        string='Total VAT', compute='_compute_custom_totals',
        store=True, currency_field='currency_id')
    custom_grand_total = fields.Monetary(
        string='Grand Total', compute='_compute_custom_totals',
        store=True, currency_field='currency_id')

    @api.depends('order_line.price_subtotal',
                 'order_line.vat_amount',
                 'order_line.amount_with_vat')
    def _compute_custom_totals(self):
        for order in self:
            lines = order.order_line.filtered(lambda l: not l.display_type)
            order.custom_untaxed_total = sum(lines.mapped('price_subtotal'))
            order.custom_vat_total = sum(lines.mapped('vat_amount'))
            order.custom_grand_total = sum(lines.mapped('amount_with_vat'))

    def action_print_invoice_pdf(self):
        self.ensure_one()
        return self.env.ref(
            'calorena.action_report_sale_invoice_simple'
        ).report_action(self)

    def action_export_invoice_excel(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/calorena/invoice_excel/%s' % self.id,
            'target': 'self',
        }


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    local_acc_number = fields.Char(string='Local Account Number')