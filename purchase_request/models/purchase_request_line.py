# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'
    _order = 'sequence, id'
    _rec_name = 'product_id'

    sequence = fields.Integer(default=10, index=True)
    request_id = fields.Many2one(
        comodel_name='purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        related='request_id.company_id',
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain=[('purchase_ok', '=', True)],
        index=True,
    )
    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        index=True,
        domain=[('supplier_rank', '>', 0)],
        help="Vendor to order this product from. Lines sharing the same vendor"
             " are grouped into the same RFQ when the request is confirmed.")
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        default=1.0,
    )
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id',
        string='Product UoM Category',
        depends=['product_id'],
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        compute='_compute_product_uom_id',
        store=True,
        readonly=False,
        precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]",
    )

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        # Same logic as purchase.order.line: suggest the product's purchase
        # UoM, unless the currently selected UoM already belongs to the same
        # category as the product.
        for line in self:
            if not line.product_uom_id or line.product_uom_id.category_id != line.product_id.uom_id.category_id:
                line.product_uom_id = line.product_id.uom_po_id or line.product_id.uom_id

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_(
                    "The quantity of product %s must be strictly positive.",
                    line.product_id.display_name))

    # ------------------------------------------------------------------
    # CRUD overrides: lock the lines of confirmed requests
    # ------------------------------------------------------------------

    def write(self, vals):
        self._check_not_confirmed()
        return super().write(vals)

    def unlink(self):
        self._check_not_confirmed()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_not_confirmed()
        return lines

    def _check_not_confirmed(self):
        # Superuser bypass: keep module operations (install/upgrade) working.
        if self.env.su:
            return
        for line in self:
            if line.request_id.state == 'confirmed':
                raise UserError(_(
                    "You cannot modify the lines of the confirmed purchase"
                    " request %s. Reset it to draft first.",
                    line.request_id.name))