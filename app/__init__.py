"""应用工厂。"""

from flask import Flask

from app.bootstrap import (
    register_blueprints,
    register_commands,
    register_error_handlers,
    register_extensions,
)
from app.config import get_config


def create_app():
    """创建并初始化 Flask 应用。"""
    app = Flask(__name__)
    app.config.from_object(get_config())
    app.config['JSON_AS_ASCII'] = False

    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    register_error_handlers(app)

    return app
