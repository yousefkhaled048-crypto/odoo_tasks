
/* @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class FormView extends Component {
    static template = "todo.FormView";
    static props = {
        record: { type: Object, optional: true },
        onRecordCreated: { type: Function, optional: true },
        onCancel: { type: Function, optional: true },
    };

    setup() {
        const rec = this.props.record;
        this.state = useState({
            name: rec ? rec.name : "",
            user_id: rec && rec.user_id ? rec.user_id[0] : "",
            due_date: rec && rec.due_date ? rec.due_date : "",
            is_done: rec ? rec.is_done : false,
            users: [],
        });

        onWillStart(async () => {
            await this.loadUsers();
        });
    }

    async loadUsers() {
        this.state.users = await rpc("/web/dataset/call_kw/res.users/search_read", {
            model: "res.users",
            method: "search_read",
            args: [[]],
            kwargs: { fields: ["name"] },
        });
    }

    async createTask() {
        if (!this.state.name) {
            return;
        }

        const vals = {
            name: this.state.name,
            user_id: this.state.user_id ? parseInt(this.state.user_id) : false,
            due_date: this.state.due_date || false,
            is_done: this.state.is_done,
        };

        if (this.props.record) {
            await rpc("/web/dataset/call_kw/todo.task/write", {
                model: "todo.task",
                method: "write",
                args: [[this.props.record.id], vals],
                kwargs: {},
            });
        } else {
            await rpc("/web/dataset/call_kw/todo.task/create", {
                model: "todo.task",
                method: "create",
                args: [vals],
                kwargs: {},
            });
        }

        if (this.props.onRecordCreated) {
            this.props.onRecordCreated();
        }
    }

    cancel() {
        this.state.name = "";
        this.state.user_id = "";
        this.state.due_date = "";

        this.props.onCancel();
    }
}
