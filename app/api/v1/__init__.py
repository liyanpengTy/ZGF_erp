from flask import Blueprint
from flask_restx import Api
# 导入所有命名空间
from app.api.v1.auth.auth import auth_ns
from app.api.v1.system import user_ns, role_ns, menu_ns, factory_ns, log_ns, monitor_ns
from app.api.v1.profile.profile import profile_ns
from app.api.v1.base_data import category_ns, color_ns, size_ns
from app.api.v1.business import style_ns, style_price_ns, style_process_ns, style_elastic_ns, process_ns, order_ns


bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

api = Api(bp, doc='/docs', title='ZGF_ERP_PC_API', version='1.0',
          description='ZGF_ERP_PC_API 文档')

# 添加所有命名空间
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(user_ns, path='/system/users')
api.add_namespace(role_ns, path='/system/roles')
api.add_namespace(menu_ns, path='/system/menus')
api.add_namespace(factory_ns, path='/system/factories')
api.add_namespace(log_ns, path='/system/logs')
api.add_namespace(monitor_ns, path='/system/monitor')
api.add_namespace(profile_ns, path='/profile')
api.add_namespace(size_ns, path='/base/sizes')
api.add_namespace(category_ns, path='/base/categories')
api.add_namespace(color_ns, path='/base/colors')
api.add_namespace(style_ns, path='/business/styles')
api.add_namespace(style_price_ns, path='/business/style-prices')
api.add_namespace(style_process_ns, path='/business/style-processes')
api.add_namespace(style_elastic_ns, path='/business/style-elastics')
api.add_namespace(process_ns, path='/business/processes')
api.add_namespace(order_ns, path='/business/order_ns')

