"""V1 系统管理接口导出。"""

from app.api.v1.system.employee_wages import employee_wage_ns
from app.api.v1.system.factories import factory_ns
from app.api.v1.system.logs import log_ns
from app.api.v1.system.menus import menu_ns
from app.api.v1.system.monitor import monitor_ns
from app.api.v1.system.rewards import reward_ns
from app.api.v1.system.roles import role_ns
from app.api.v1.system.users import user_ns

NAMESPACE_ROUTES = [
    (user_ns, '/system/users'),
    (role_ns, '/system/roles'),
    (menu_ns, '/system/menus'),
    (factory_ns, '/system/factories'),
    (log_ns, '/system/logs'),
    (monitor_ns, '/system/monitor'),
    (reward_ns, '/system/rewards'),
    (employee_wage_ns, '/system/employee-wage'),
]

__all__ = [
    'user_ns',
    'role_ns',
    'menu_ns',
    'factory_ns',
    'log_ns',
    'monitor_ns',
    'reward_ns',
    'employee_wage_ns',
    'NAMESPACE_ROUTES',
]
