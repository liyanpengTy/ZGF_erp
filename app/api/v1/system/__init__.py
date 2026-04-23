from flask import Blueprint
# 导入命名空间以确保模块被加载（但不创建 Api）
from app.api.v1.system.users import user_ns
from app.api.v1.system.roles import role_ns
from app.api.v1.system.menus import menu_ns
from app.api.v1.system.factories import factory_ns
from app.api.v1.system.logs import log_ns
from app.api.v1.system.monitor import monitor_ns

bp = Blueprint('system', __name__, url_prefix='/system')
