{
    'name': 'Simple To Do',
    'version': '19.0.1.0.0',
    'summary': 'Simple To Do tasks',
    'category': 'Productivity',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/todo_task_data.xml',
        'views/todo_task_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'todo\static\src\components\listView\listView.css',
            'todo\static\src\components\listView\listView.js',
            'todo\static\src\components\listView\listView.xml',
            'todo/static/src/components/formView/formView.css',
            'todo/static/src/components/formView/formView.js',
            'todo/static/src/components/formView/formView.xml',
        ]
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}