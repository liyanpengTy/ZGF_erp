"""系统管理接口模块"""
from app.api.v1.system.users import user_ns
from app.api.v1.system.roles import role_ns
from app.api.v1.system.menus import menu_ns
from app.api.v1.system.factories import factory_ns
from app.api.v1.system.logs import log_ns
from app.api.v1.system.monitor import monitor_ns

__all__ = [
    'user_ns',
    'role_ns',
    'menu_ns',
    'factory_ns',
    'log_ns',
    'monitor_ns'
]
