# Sales Credit Limit Approval (Odoo 19)

Credit limit per partner and a two-phase Sales Order approval workflow.

## Install

1. Copy `sale_credit_limit_approval` into your addons path.
2. Update the Apps list and install **Sales Credit Limit Approval** (depends on `sale`, `account`).
3. Settings > Users: set **Credit Limit Approval = Approver** for the approvers
   (the admin user gets it on install). The group implies *Sales: User - All Documents*.

## Configuration (Contact > Sales & Purchase > Credit Limit)

| Field | Meaning |
|---|---|
| Partner Limit (`partner_limit`) | Enables the credit check for the partner (customers and vendors). |
| Credit Limit (`partner_credit_limit`) | Monetary limit, shown only when Partner Limit is on. |
| Credit Limit Currency | Currency of the limit (multi-currency users only; defaults to the company currency). |

Only approvers can edit these fields (enforced in `create`/`write`, not just in the view).
For contacts that belong to a company, the parent company's limit is used.

## Credit calculation

* **Outstanding Invoice Amount** = sum of `amount_residual_signed` of **posted** `out_invoice`
  and `out_refund` moves of the order's company for the commercial partner.
  Draft/cancelled moves are excluded, paid invoices have zero residual, partial payments
  and open credit notes are reflected, amounts are in company currency.
* **Available Credit** = Credit Limit − Outstanding Invoice Amount.
* **Current Quotation Amount** = order total converted to company currency
  (for confirmed orders, the part already invoiced is subtracted to avoid double counting).
* **Potential Exposure** = Outstanding + Current Quotation Amount.
  Exposure > Limit → **Exceeded Limit** (red banner), otherwise **Within Limit** (green banner).

## Workflow (only when Partner Limit is enabled)

| Situation | Buttons |
|---|---|
| Within limit, Draft | Approve 1 (visible, disabled), **Approve 2** → Approved |
| Exceeded, Draft | **Request Approval** → Waiting for Approval 1 |
| Waiting for Approval 1 | **Approve 1** → Waiting for Approval 2, Reject |
| Waiting for Approval 2 | **Approve 2** → Approved, Reject |
| Approved | Confirm |
| Rejected | Reset Approval → Draft |

* The same approver may perform Approve 1 and Approve 2; the order of the steps is always enforced.
* Confirm is hidden until Approved and blocked in `_confirmation_error_message` on the backend.
* Changing a partner's credit limit sends pending orders (Waiting 1, Waiting 2, Approved but
  not confirmed) back to **Waiting for Approval 1** (back to Draft if the credit check is disabled).
* Raising the order total, or changing customer/company/currency after the process started,
  resets the approval to Draft. Confirmation is also refused if the total grew after Approve 2,
  or if an order approved "within limit" now exceeds it (use Reset Approval).
* Cancel → Cancelled; Set to Quotation from Cancelled → Draft.
* Workflow fields can only be written by the approval methods (normal `write`/`create`
  attempts, including `default_*` context keys, are refused).
* Online signature or payment does not auto-confirm an order still waiting for credit approval;
  a note is logged instead.

Approvers get a **Sales > Orders > Credit Approvals** menu and new search filters
(Pending Credit Approval, Waiting for Approval 1/2, Credit Approved/Rejected).
