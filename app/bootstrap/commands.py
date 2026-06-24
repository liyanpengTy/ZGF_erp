"""CLI 命令注册。"""

from app.commands import register_commands as register_cli_commands


def register_commands(app):
    """注册 Flask CLI 命令。"""
    register_cli_commands(app)
