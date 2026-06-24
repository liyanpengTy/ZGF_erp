"""应用启动注册入口。"""

from app.bootstrap.blueprints import register_blueprints
from app.bootstrap.commands import register_commands
from app.bootstrap.errors import register_error_handlers
from app.bootstrap.extensions import register_extensions

__all__ = [
    'register_extensions',
    'register_blueprints',
    'register_commands',
    'register_error_handlers',
]
