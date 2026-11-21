from odoo import http
from odoo.http import request
from ast import literal_eval
import io
import xlsxwriter


class XlsxTaskReport(http.Controller):

    @http.route('/task/excel/report/<string:task_ids>', type='http', auth='user')
    def download_task_excel_report(self, task_ids):

        task_ids = request.env['todo.task'].browse(literal_eval(task_ids))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('tasks')

        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        string_format = workbook.add_format({'border': 1, 'align': 'center'})
        datetime_format = workbook.add_format({'border': 1,'align': 'center','num_format': 'yyyy-mm-dd'})

        headers = ['Name', 'Assigned To', 'Due Date']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        row_num = 1
        for task in task_ids:
            worksheet.write(row_num, 0, task.name, string_format)
            worksheet.write(row_num, 1, task.user_id.name or '', string_format)
            worksheet.write(row_num, 2, task.due_date, datetime_format)
            row_num += 1

        workbook.close()
        output.seek(0)

        file_name = 'task_report.xlsx'

        return request.make_response(
            output.getvalue(),
            headers = [
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename = {file_name}'),
            ]
        )