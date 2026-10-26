from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from collections import defaultdict


class HoldSequence(models.Model):
    _name = 'hold.sequence'
    _order = 'id desc'

    name = fields.Char(
        string='Hold Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'hold.sequence.line',
        'sequence_id',
        string='Lines',
        copy=True,
    )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('hold.sequence')
                    or _('New')
                )
        return super().create(vals_list)

    # workflow buttons
    def _check_available_qty(self):
        Line = self.env['hold.sequence.line']
        for rec in self:
            # نجمع الكمية لكل منتج، لأن نفس المنتج ممكن يتكرر في أكتر من سطر
            totals = defaultdict(float)
            for line in rec.line_ids:
                totals[line.product_id] += line.hold_qty

            products = self.env['product.product'].browse(
                [p.id for p in totals]
            )
            held = Line._get_confirmed_hold_qty(products)

            for product, requested in totals.items():
                available = product.qty_available - held.get(product.id, 0.0)
                if requested > available:
                    raise ValidationError(_(
                        "Cannot hold %(requested)s of '%(product)s'. "
                        "Only %(available)s available (On Hand: %(on_hand)s, "
                        "already held: %(held)s).",
                        requested=requested,
                        product=product.display_name,
                        available=available,
                        on_hand=product.qty_available,
                        held=held.get(product.id, 0.0),
                    ))

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(
                    _("Please add at least one line before confirming.")
                )
        self._check_available_qty()
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})