# -*- coding: utf-8 -*-
from odoo import _, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_request_id = fields.Many2one(
        comodel_name='purchase.request',
        string='Purchase Request',
        copy=False,
        index=True,
        readonly=True,
        help="Purchase request this order was generated from.")

    def action_view_purchase_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Request'),
            'res_model': 'purchase.request',
            'res_id': self.purchase_request_id.id,
            'view_mode': 'form',
        }