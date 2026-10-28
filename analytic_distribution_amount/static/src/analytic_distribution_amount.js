/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { formatCurrency } from "@web/core/currency";
import { roundDecimals } from "@web/core/utils/numbers";
import { formatPercentage } from "@web/views/fields/formatters";
import { useState } from "@odoo/owl";

import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";

const ADA_MODE_STORAGE_KEY = "sale_analytic_distribution_amount_mode";

/**
 * Adds fixed amount entry to the analytic distribution widget.
 *
 * - A [% | Amount] toggle in the popup header switches between percentage
 *   entry (core behaviour) and fixed amount entry. The last used mode is
 *   remembered per browser (localStorage).
 * - In Amount mode the percentage column is replaced by an editable amount
 *   column based on the amount field of the record (price_subtotal on sale
 *   order lines), with the resulting percentage shown as a hint. Editing an
 *   amount converts it back to a percentage for 'analytic_distribution', which
 *   remains the source of truth.
 * - The exact amounts entered are stored in the 'analytic_distribution_amount'
 *   JSON field of the record whenever that field is present in the view
 *   (added on sale.order.line by this module). On other models the widget
 *   keeps working and simply skips the persistence part.
 */
patch(AnalyticDistribution.prototype, {
    setup() {
        super.setup(...arguments);
        this.adaState = useState({ mode: this.adaReadStoredMode() });
    },

    // ------------------------------------------------------------------
    // Mode management
    // ------------------------------------------------------------------
    adaReadStoredMode() {
        try {
            return browser.localStorage.getItem(ADA_MODE_STORAGE_KEY) === "amount" ? "amount" : "percentage";
        } catch {
            return "percentage";
        }
    },

    setAdaMode(mode) {
        this.adaState.mode = mode === "amount" ? "amount" : "percentage";
        try {
            browser.localStorage.setItem(ADA_MODE_STORAGE_KEY, this.adaState.mode);
        } catch {
            // storage unavailable: the mode simply won't be persisted
        }
    },

    /**
     * Effective mode: Amount mode requires a usable value column (an
     * 'amount_field' option set on the widget and a non-zero base amount).
     */
    get adaMode() {
        return this.adaState.mode === "amount" && this.valueColumnEnabled ? "amount" : "percentage";
    },

    // ------------------------------------------------------------------
    // Amount helpers
    // ------------------------------------------------------------------
    adaSubtotal() {
        if (!this.props.amount_field) {
            return 0;
        }
        return this.props.record.data[this.props.amount_field] || 0;
    },

    /**
     * Fixed amount of a distribution line: the amount typed by the user when
     * available, otherwise the amount derived from the line percentage.
     */
    adaAmountFor(line) {
        if (line.adaAmount != null) {
            return line.adaAmount;
        }
        return roundDecimals(line.percentage * this.adaSubtotal(), 2);
    },

    adaAccountKey(line) {
        return line.analyticAccounts.reduce((p, n) => p.concat(n.accountId ? n.accountId : []), []).join(",");
    },

    adaTotals() {
        const subtotal = this.adaSubtotal();
        let distributed = 0;
        for (const line of this.state.formattedData) {
            if (this.accountCount(line)) {
                distributed += this.adaAmountFor(line);
            }
        }
        distributed = roundDecimals(distributed, 2);
        return {
            subtotal,
            distributed,
            remaining: roundDecimals(subtotal - distributed, 2),
            percentage: subtotal ? roundDecimals((distributed / subtotal) * 100, 2) : 0,
        };
    },

    adaFormatAmount(value) {
        const currencyId = this.props.record.data.currency_id && this.props.record.data.currency_id[0];
        return formatCurrency(value || 0, currencyId);
    },

    adaFormatPercentage(fraction) {
        return formatPercentage(fraction || 0, this.decimalPrecision);
    },

    // ------------------------------------------------------------------
    // Hooks into the core widget behaviour
    // ------------------------------------------------------------------
    /**
     * Display the exact amount typed by the user instead of the amount
     * re-derived from the rounded percentage (avoids the input value changing
     * under the user's fingers while typing, e.g. 333.33 becoming 333.30).
     */
    recordProps(line) {
        const props = super.recordProps(line);
        if (this.valueColumnEnabled && line.adaAmount != null) {
            props.values[this.props.amount_field] = line.adaAmount;
        }
        return props;
    },

    lineChanged(record, changes, line) {
        super.lineChanged(record, changes, line);
        if (this.valueColumnEnabled && changes[this.props.amount_field] !== undefined) {
            // the user typed a fixed amount: keep it as-is for storage/display
            line.adaAmount = changes[this.props.amount_field] ?? 0;
        } else if (changes.percentage !== undefined && line.adaAmount != null) {
            // the user edited the percentage: realign the stored amount
            line.adaAmount = roundDecimals(line.percentage * this.adaSubtotal(), 2);
        }
    },

    async save() {
        await super.save(...arguments);
        if (this.props.multi_edit) {
            // amounts cannot be reliably set in multi edit mode
            return;
        }
        const record = this.props.record;
        if (!record.fields.analytic_distribution_amount) {
            // the amounts field is not present in this view (not a sale order
            // line, or the module view inheritance is not applied): skip the
            // persistence part, percentages are already saved by the core.
            return;
        }
        const amounts = {};
        for (const line of this.state.formattedData) {
            if (!this.accountCount(line)) {
                continue;
            }
            const key = this.adaAccountKey(line);
            const amount = this.adaAmountFor(line);
            if (amount) {
                amounts[key] = roundDecimals((amounts[key] || 0) + amount, 2);
            }
        }
        await record.update({
            analytic_distribution_amount: Object.keys(amounts).length ? amounts : false,
        });
    },
});