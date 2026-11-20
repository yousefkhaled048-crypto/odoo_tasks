from odoo import fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    barcode_scan = fields.Char(
        string='Barcode',
        copy=False,
    )

    def action_add_product_by_barcode(self):
        self.ensure_one()

        # 1. Validate Sales Order state.
        if self.state not in ('draft', 'sent'):
            raise UserError(_(
                "You can only scan products on a quotation."
            ))

        # 2. Read barcode.
        barcode = (self.barcode_scan or '').strip()

        if not barcode:
            raise UserError(_("Please scan or enter a barcode."))

        Product = self.env['product.product']
        ProductUom = self.env['product.uom']

        company_domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ]

        # 3. Search additional UoM barcode.
        uom_barcodes = ProductUom.search(
            [
                ('barcode', '=', barcode),
                ('product_id.active', '=', True),
                ('uom_id.active', '=', True),
            ] + company_domain,
            limit=2,
        )

        if len(uom_barcodes) > 1:
            raise UserError(_(
                "This barcode matches more than one UoM barcode."
            ))

        if uom_barcodes:
            barcode_record = uom_barcodes
            product = barcode_record.product_id
            uom = barcode_record.uom_id

        else:
            # 4. Search standard product barcode.
            products = Product.search(
                [
                    ('barcode', '=', barcode),
                    ('active', '=', True),
                    ('sale_ok', '=', True),
                ] + company_domain,
                limit=2,
            )

            if len(products) > 1:
                raise UserError(_(
                    "This barcode matches more than one product."
                ))

            if not products:
                raise UserError(_(
                    "No active product was found for barcode: %s",
                    barcode,
                ))

            product = products
            uom = product.uom_id

        # 5. Validate product.
        if not product.active:
            raise UserError(_("This product is archived."))

        if not product.sale_ok:
            raise UserError(_(
                "The product '%s' cannot be sold.",
                product.display_name,
            ))

        # 6. Validate UoM.
        if not uom.active:
            raise UserError(_(
                "The selected Unit of Measure is archived."
            ))

        if not uom._has_common_reference(product.uom_id):
            raise UserError(_(
                "The selected Unit of Measure is incompatible "
                "with the product."
            ))

        # 7. Get UoMs configured for this product.
        available_uoms = (
            product.uom_id
            | product.product_uom_ids.mapped('uom_id')
        )

        if uom not in available_uoms:
            raise UserError(_(
                "This Unit of Measure is not configured for this product."
            ))

        # 8. Find existing line with same product and UoM.
        existing_line = self.order_line.filtered(
            lambda line:
                not line.display_type
                and line.product_id == product
                and line.product_uom_id == uom
        )[:1]

        if existing_line:
            existing_line.product_uom_qty += 1

        else:
            # 9. Create Sales Order Line.
            self.env['sale.order.line'].with_company(
                self.company_id
            ).create({
                'order_id': self.id,
                'product_id': product.id,
                'product_uom_id': uom.id,
                'product_uom_qty': 1,
            })

        # 10. Clear barcode.
        self.barcode_scan = False

        return True