import json
import math
from urllib.parse import parse_qs
from odoo import http
from odoo.http import request


def valid_response(data, status, pagination_info=None):
    response_body = {
        'message': 'Successfully',
        'data': data,
    }
    if pagination_info:
        response_body['pagination_info'] = pagination_info
    return request.make_json_response(response_body, status= status)

def invalid_response(error, status):
    response_body = {
        'error': error,
    }
    return request.make_json_response(response_body, status= status)


class TodoTaskApi(http.Controller):

    # create
    @http.route("/v1/todo_task", methods=["POST"],type="http", auth="none", csrf=False)
    def post_todo_task(self):
        args = request.httprequest.data.decode()
        vals = json.loads(args)
        if not vals.get('name'):
            return invalid_response("Name is required",status=400)
        try:
            res = request.env['todo.task'].sudo().create(vals)
            if res:
                return valid_response({
                    "id": res.id,
                    "name": res.name,
                }, status=201)
        except Exception as e:
            return invalid_response(str(e), status=400)


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
                return invalid_response("Task not found", status=400)
            args = request.httprequest.data.decode()
            vals = json.loads(args)
            task_id.write(vals)
            return valid_response({
                "id": task_id.id,
                "name": task_id.name,
            }, status=200)
        except Exception as e:
            return invalid_response(str(e), status=400)

    # read
    @http.route("/v1/todo_task/<int:task_id>", methods=["GET"], type="http", auth="none", csrf=False)
    def read_todo_task(self, task_id):
        try:
            task_id = request.env['todo.task'].sudo().search([('id', '=', task_id)])
            if not task_id:
                return invalid_response("Task not found",status=400)
            return valid_response({
                "id": task_id.id,
                "name": task_id.name,
                "due_date": task_id.due_date,
                "assigned_to": task_id.user_id.name,
                "is_done": task_id.is_done,
            }, status=200)
        except Exception as e:
            return invalid_response(str(e), status=400)

    # delete
    @http.route("/v1/todo_task/<int:task_id>", methods=["DELETE"], type="http", auth="none", csrf=False)
    def delete_todo_task(self, task_id):
        try:
            task_id = request.env['todo.task'].sudo().search([('id', '=', task_id)])
            if not task_id:
                return invalid_response("Task not found", status=400)
            task_id.unlink()
            return valid_response("Task deleted successfully", status=200)
        except Exception as e:
            return invalid_response(str(e), status=400)

    # get all
    @http.route("/v1/todo_tasks", methods=["GET"], type="http", auth="none", csrf=False)
    def read_all_todo_tasks(self):
        try:
            params = parse_qs(request.httprequest.query_string.decode('utf-8'))
            # pagination
            task_domain = []
            page = offset = None
            limit = 5
            if params:
                if params.get('page'):
                    page = int(params.get('page')[0])
                if params.get('limit'):
                    limit = int(params.get('limit')[0])

            if page:
                offset = (page * limit) - limit

            # filter
            if params.get('is_done'):
                task_domain += [('is_done', '=', params.get('is_done')[0])]
            task_ids = request.env['todo.task'].sudo().search(task_domain, offset = offset, limit = limit)
            task_count = request.env['todo.task'].sudo().search_count(task_domain)

            if not task_ids:
                return invalid_response("No tasks found", status=400)
            return valid_response([{
                "id": task_id.id,
                "name": task_id.name,
                "due_date": task_id.due_date,
                "assigned_to": task_id.user_id.name,
                "is_done": task_id.is_done,
            } for task_id in task_ids], pagination_info = {
                'page': page,
                'limit': limit,
                'pages': math.ceil((task_count / limit)) if limit else 1,
                'count': task_count
            }, status=200)
        except Exception as e:
            return invalid_response(str(e), status=400)

