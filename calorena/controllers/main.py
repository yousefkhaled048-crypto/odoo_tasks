import io

import xlsxwriter

from odoo import http
from odoo.http import request

GREEN = '#E2EFDA'


class CalorenaInvoiceExcel(http.Controller):

    @http.route('/calorena/invoice_excel/<int:order_id>', type='http', auth='user')
    def invoice_excel(self, order_id, **kw):
        order = request.env['sale.order'].browse(order_id)
        if not order.exists():
            return request.not_found()
        order.check_access('read')

        company = order.company_id
        bank = company.partner_id.bank_ids[:1]
        iban = (bank.sanitized_acc_number or bank.acc_number or '') if bank else ''
        acc_no = iban[8:] if iban else ''
        acc_name = (bank.acc_holder_name if bank else '') or company.name or ''

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Invoice')
        ws.right_to_left()
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        ws.set_margins(left=0.3, right=0.3, top=0.4, bottom=0.5)
        ws.set_footer('&C&P')

        def fmt(**kw):
            base = {'font_name': 'Arial', 'font_size': 10, 'valign': 'vcenter'}
            base.update(kw)
            return wb.add_format(base)

        f_name_en = fmt(bold=True, font_size=14, align='left')
        f_name_ar = fmt(bold=True, font_size=15, align='right')
        f_en = fmt(bold=True, font_size=11, align='left')
        f_ar = fmt(bold=True, font_size=11, align='right')
        f_logo = fmt(font_name='Times New Roman', font_size=24, align='center',
                     text_wrap=True)
        f_rule = fmt(top=2)
        f_title = fmt(bold=True, font_size=14, align='center')
        f_green_head = fmt(bold=True, align='center', bg_color=GREEN, border=1)
        f_cell = fmt(border=1, align='center', text_wrap=True)
        f_cell_b = fmt(border=1, align='center', bold=True)
        f_cell_l = fmt(border=1, align='left')
        f_cell_r = fmt(border=1, align='right')
        f_green = fmt(border=1, align='center', bg_color=GREEN)
        f_th = fmt(border=1, align='center', bold=True, bg_color=GREEN,
                   text_wrap=True, font_size=9)
        f_txt = fmt(border=1, align='center', font_size=9)
        f_txt_r = fmt(border=1, align='right', font_size=9)
        f_num = fmt(border=1, align='center', font_size=9, num_format='0.00')
        f_pct = fmt(border=1, align='center', font_size=9, num_format='0.##"%"')
        f_sec = fmt(border=1, bold=True, bg_color='#F2F2F2')
        f_note = fmt(border=1, italic=True)
        f_tot_lbl = fmt(border=1, bold=True, align='right', font_size=11)
        f_tot_val = fmt(border=1, align='center', font_size=11, num_format='#,##0.00')
        f_tot_val_b = fmt(border=1, align='center', font_size=11, bold=True,
                          bg_color=GREEN, num_format='#,##0.00')
        f_note_txt = fmt(align='right', font_size=11, valign='top', text_wrap=True)
        f_sign = fmt(bold=True, align='center', font_size=11)
        f_dots = fmt(bottom=4)
        f_ftr = fmt(bold=True, font_size=11, align='right')

        # Column widths (RTL: column A is on the right)
        widths = [6, 12, 17, 38, 9, 9, 8, 11, 8, 8, 14, 11, 13]
        for c, w in enumerate(widths):
            ws.set_column(c, c, w)
        LAST = 12

        # ===== Header (Arabic right | logo center | English left) =====
        ws.set_row(0, 24)
        ar = [('شركة كالورينا', f_name_ar),
              ('المملكة العربية السعودية', f_ar),
              ('الرقم الضريبي : %s' % (company.vat or ''), f_ar),
              ('هاتف رقم : %s' % (company.phone or ''), f_ar)]
        en = [('Calorena Company', f_name_en),
              ('Saudi Arabia', f_en),
              ('Tax ID : %s' % (company.vat or ''), f_en),
              ('Tel : %s' % (company.phone or ''), f_en)]
        for r in range(4):
            ws.merge_range(r, 0, r, 3, ar[r][0], ar[r][1])
            ws.merge_range(r, 9, r, 12, en[r][0], en[r][1])
        ws.merge_range(0, 4, 3, 8, 'CALORENA\nSECRET', f_logo)
        ws.merge_range(4, 0, 4, LAST, '', f_rule)

        # ===== Title =====
        ws.set_row(5, 24)
        ws.merge_range(5, 0, 5, LAST, 'فاتورة ضريبية Tax Invoice', f_title)

        # ===== Customer details =====
        ws.merge_range(6, 0, 6, LAST, 'Customer Details', f_green_head)
        ws.merge_range(7, 0, 7, 1, 'الاسم', f_cell_r)
        ws.merge_range(7, 2, 7, 10, order.partner_id.name or '', f_cell_b)
        ws.merge_range(7, 11, 7, 12, 'Name', f_cell_l)
        ws.merge_range(8, 0, 8, 1, 'الرقم الضريبي للعميل', f_cell_r)
        ws.merge_range(8, 2, 8, 10, order.partner_id.vat or '', f_cell)
        ws.merge_range(8, 11, 8, 12, 'Customer TRN', f_cell_l)

        # ===== Invoice info =====
        ws.set_row(10, 30)
        spans = [(0, 2, 'Invoice No.\nرقم الفاتورة', order.name or ''),
                 (3, 5, 'Date\nالتاريخ',
                  order.date_order.strftime('%m/%d/%Y') if order.date_order else ''),
                 (6, 8, 'Sales Person\nالمندوب', order.user_id.name or ''),
                 (9, 12, 'State\nالمنطقة', order.partner_id.state_id.name or '')]
        for c1, c2, head, val in spans:
            ws.merge_range(10, c1, 10, c2, head, f_cell)
            ws.merge_range(11, c1, 11, c2, val, f_green)

        # ===== Lines =====
        heads = ['رقم\nNO.', 'رقم الصنف\nItem No', 'رقم الباركود\nBarcode No',
                 'اسم الصنف\nItem Name', 'الوحدة\nUnit', 'الكمية\nQTY',
                 'تسانر\nTests', 'سعر الوحدة\nUnit price', 'خصم 1\nD1',
                 'خصم 2\nD2', 'الاجمالي قبل الضريبة\nEXCL VAT',
                 'الضريبة\nVAT 15%', 'الاجمالي\nAmount']
        row = 13
        ws.set_row(row, 40)
        for c, h in enumerate(heads):
            ws.write(row, c, h, f_th)
        ws.repeat_rows(row)

        idx = 0
        for line in order.order_line:
            row += 1
            if line.display_type == 'line_section':
                ws.merge_range(row, 0, row, LAST, line.name or '', f_sec)
                continue
            if line.display_type == 'line_note':
                ws.merge_range(row, 0, row, LAST, line.name or '', f_note)
                continue
            idx += 1
            ws.write_number(row, 0, idx, f_txt)
            ws.write(row, 1, line.item_no or '', f_txt)
            ws.write(row, 2, line.barcode_no or '', f_txt)
            ws.write(row, 3, line.product_id.display_name or '', f_txt_r)
            ws.write(row, 4, line.product_uom_id.name or '', f_txt)
            ws.write_number(row, 5, line.product_uom_qty, f_num)
            ws.write(row, 6, line.tests or '0.0', f_txt)
            ws.write_number(row, 7, line.price_unit, f_num)
            ws.write_number(row, 8, line.discount_1, f_pct)
            ws.write_number(row, 9, line.discount_2, f_pct)
            ws.write_number(row, 10, line.price_subtotal, f_num)
            ws.write_number(row, 11, line.vat_amount, f_num)
            ws.write_number(row, 12, line.amount_with_vat, f_num)

        # ===== Totals + notes (page 2 content) =====
        real = order.order_line.filtered(lambda l: not l.display_type)
        gross = sum(l.price_unit * l.product_uom_qty for l in real)
        discount = gross - order.custom_untaxed_total
        totals = [('الاجمالي قبل الخصم:', gross, False),
                  ('الخصم:', discount, False),
                  ('الاجمالي غير شامل ضريبة القيمة المضافة:',
                   order.custom_untaxed_total, False),
                  ('الضريبة:', order.custom_vat_total, False),
                  ('المجموع شامل الضريبة المضافة:', order.custom_grand_total, True)]
        row += 2
        ws.set_h_pagebreaks([row])
        start = row
        for i, (lbl, val, last) in enumerate(totals):
            ws.set_row(row + i, 22)
            ws.merge_range(row + i, 6, row + i, 9, lbl, f_tot_lbl)
            ws.merge_range(row + i, 10, row + i, 12, val,
                           f_tot_val_b if last else f_tot_val)
        ws.merge_range(
            start, 0, start + 2, 4,
            '* مدة استحقاق الفاتوره الأجله ٤٥ يوم من تاريخه\n'
            '* مدة السماح فى المرتجع ١٨٠ يوم من إصدار الفاتوره', f_note_txt)
        row += len(totals) + 2

        # ===== Signatures =====
        sign_spans = [(0, 2, 'العميل'), (3, 5, 'مندوب المبيعات'),
                      (6, 8, 'مدير المبيعات'), (9, 12, 'أمين المستودع')]
        for c1, c2, label in sign_spans:
            ws.merge_range(row, c1, row, c2, label, f_sign)
            ws.merge_range(row + 2, c1, row + 2, c2, '', f_dots)
        ws.set_row(row + 2, 28)
        row += 4

        # ===== Footer: bank details =====
        ws.merge_range(row, 0, row, 3, 'رقم الايبان: %s' % iban, f_ftr)
        ws.merge_range(row, 4, row, 8, 'رقم الحساب: %s' % acc_no, f_ftr)
        ws.merge_range(row, 9, row, 12, 'أسم الحساب: %s' % acc_name, f_ftr)

        wb.close()
        filename = 'Invoice_%s.xlsx' % (order.name or order.id).replace('/', '_')
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ])