/* @odoo-module */

import { Component, useState, onWillUnmount  } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { FormView } from "@todo/components/formView/formView"


export class TodoListView extends Component{

    static template = 'todo.ListView';
    static components = { FormView, };

    setup(){
        this.state = useState({
             records: [],
             showCreateTask: false,
             editingRecord: null,
        });
        this.orm = useService('orm');
        this.loadRecords();
        this.onRecordCreated = this.onRecordCreated.bind(this);
        this.interval = setInterval(() => {this.loadRecords()},3000);
        onWillUnmount(() => clearInterval(this.interval));
    };

    // async loadRecords() {
    //     const result = await this.orm.searchRead('todo.task', [], []);
    //     console.log(result);
    //     this.state.records = result;
    // };

    async loadRecords() {
        const result = await rpc("/web/dataset/call_kw", {
            model: "todo.task",
            method: "search_read",
            args: [[]],
            kwargs: {
                fields: ["id", "name", "user_id", "due_date", "is_done", "is_done"],
            },
        });
        this.state.records = result;
    };

    // not used now (used for add static record)
    async createTask() {
        await rpc("/web/dataset/call_kw", {
            model: "todo.task",
            method: "create",
            args: [{
                name: "New Task",
                is_done: false,
            }],
            kwargs: {},
        });
        await this.loadRecords();
    };

    async deleteTask(taskId) {
        await rpc("/web/dataset/call_kw", {
            model: "todo.task",
            method: "unlink",
            args: [[taskId]],
            kwargs: {},
        });
        await this.loadRecords();
    };

    toggleCreateTask() {
        this.state.editingRecord = null;
        this.state.showCreateTask = !this.state.showCreateTask;
    }

    onRecordCreated() {
        this.state.editingRecord = null;
        this.state.showCreateTask = false;
        this.loadRecords();
    }

    editTask(record) {
        this.state.editingRecord = record;
        this.state.showCreateTask = true;
    }

}
registry.category("actions").add("todo.action_list_view", TodoListView);