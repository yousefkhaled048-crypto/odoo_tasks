from odoo import _, fields, models
from odoo.exceptions import UserError


class TechnicalOrderRejectionWizard(models.TransientModel):
    _name = 'technical.order.rejection.wizard'
    _description = 'Technical Order Rejection Wizard'

    technical_order_id = fields.Many2one(
        'technical.order', string='Technical Order', required=True, readonly=True,
    )
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        order = self.technical_order_id
        if order.state != 'to_approve':
            raise UserError(_("Only technical orders waiting for approval can be rejected."))
        order.write({
            'rejection_reason': self.rejection_reason,
            'state': 'rejected',
        })
        return {'type': 'ir.actions.act_window_close'}