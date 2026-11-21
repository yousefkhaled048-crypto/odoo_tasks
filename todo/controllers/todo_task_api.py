import json
from odoo import http
from odoo.addons.test_import_export.tests.test_load import message
from odoo.http import request


class TodoTaskApi(http.Controller):

    # create
    @http.route("/v1/todo_task", methods=["POST"],type="http", auth="none", csrf=False)
    def post_todo_task(self):
        args = request.httprequest.data.decode()
        vals = json.loads(args)
        if not vals.get('name'):
            return request.make_json_response({
                "message": "Name is required",
            }, status=400)
        try:
            res = request.env['todo.task'].sudo().create(vals)
            if res:
                return request.make_json_response({
                    "message": "Task created successfully",
                    "id": res.id,
                    "name": res.name,
                }, status=201)
        except Exception as e:
            return request.make_json_response({
                "message": str(e),
            }, status=400)


    @http.route("/v1/todo_task/json", methods=["POST"], type="json", auth="none", csrf=False)
    def create_todo_task_json(self):
        args = request.httprequest.data.decode()
        vals = json.loads(args)
        res = request.env['todo.task'].sudo().create(vals)
        if res:
            return {
                "message": "Task created successfully",
            }

    # update
    @http.route("/v1/todo_task/<int:task_id>", methods=["PUT"], type="http", auth="none", csrf=False)
    def update_todo_task(self, task_id):
        try:
            task_id = request.env['todo.task'].sudo().search([('id', '=', task_id)])
            if not task_id:
                return request.make_json_response({
                    "message": "Task not found",
                },status=400)
            args = request.httprequest.data.decode()
            vals = json.loads(args)
            task_id.write(vals)
            return request.make_json_response({
                "message": "Task updated successfully",
                "id": task_id.id,
                "name": task_id.name,
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                "message": str(e),
            }, status=400)

    # read
    @http.route("/v1/todo_task/<int:task_id>", methods=["GET"], type="http", auth="none", csrf=False)
    def read_todo_task(self, task_id):
        try:
            task_id = request.env['todo.task'].sudo().search([('id', '=', task_id)])
            if not task_id:
                return request.make_json_response({
                    "message": "Task not found",
                }, status=400)
            return request.make_json_response({
                "id": task_id.id,
                "name": task_id.name,
                "due_date": task_id.due_date,
                "assigned_to": task_id.user_id.name,
                "is_done": task_id.is_done,
            })
        except Exception as e:
            return request.make_json_response({
                "message": str(e),
            }, status=400)

    # delete
    @http.route("/v1/todo_task/<int:task_id>", methods=["DELETE"], type="http", auth="none", csrf=False)
    def delete_todo_task(self, task_id):
        try:
            task_id = request.env['todo.task'].sudo().search([('id', '=', task_id)])
            if not task_id:
                return request.make_json_response({
                    "message": "Task not found",
                }, status=400)
            task_id.unlink()
            return request.make_json_response({
                "message": "Task deleted successfully",
            }, status=200)
        except Exception as e:
            return request.make_json_response({
                "message": str(e),
            }, status=400)
