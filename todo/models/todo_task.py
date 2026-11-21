from odoo import models, fields


class TodoTask(models.Model):
    _name = 'todo.task'
    _description = 'To Do Task'

    name = fields.Char(string='Task Name', required=True)
    description = fields.Text(string='Description')
    due_date = fields.Date(string='Due Date')
    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        default=lambda self: self.env.user,
    )
    is_done = fields.Boolean(string='Done', default=False)

    def task_xlsx_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/task/excel/report/{self.env.context.get("active_ids")}',
            'target': 'new',
        }