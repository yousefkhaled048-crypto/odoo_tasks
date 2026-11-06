from odoo import _, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        """Online payment: do not auto-confirm a quotation that still needs credit
        approval. The payment is kept, the order stays a quotation and a note is
        logged so the approvers can complete the workflow and confirm it."""
        on_hold = self.env['payment.transaction']
        for tx in self:
            if len(tx.sale_order_ids) != 1:
                continue
            quotation = tx.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent'))
            if quotation and quotation._credit_confirmation_block_reason():
                on_hold |= tx
                quotation.message_post(body=_(
                    "Online payment received, but confirmation is on hold until the "
                    "credit approval is completed.",
                ))
        return super(PaymentTransaction, self - on_hold)._check_amount_and_confirm_order()
