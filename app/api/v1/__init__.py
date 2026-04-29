from flask import Blueprint
from flask_restx import Api
# 导入所有命名空间
from app.api.v1.auth.auth import auth_ns
from app.api.v1.system import user_ns, role_ns, menu_ns, factory_ns, log_ns, monitor_ns
from app.api.v1.profile.profile import profile_ns
from app.api.v1.base_data import category_ns, color_ns, size_ns
from app.api.v1.business import style_ns, style_price_ns, style_process_ns, style_elastic_ns

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

api = Api(bp, doc='/docs', title='ZGF_ERP_PC_API', version='1.0',
          description='ZGF_ERP_PC_API 文档')

# 添加所有命名空间
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(user_ns, path='/users')
api.add_namespace(role_ns, path='/roles')
api.add_namespace(menu_ns, path='/menus')
api.add_namespace(factory_ns, path='/factories')
api.add_namespace(log_ns, path='/logs')
api.add_namespace(monitor_ns, path='/monitor')
api.add_namespace(profile_ns, path='/profile')
api.add_namespace(size_ns, path='/sizes')
api.add_namespace(category_ns, path='/categories')
api.add_namespace(color_ns, path='/colors')
api.add_namespace(style_ns, path='/styles')
api.add_namespace(style_price_ns, path='/style-prices')
api.add_namespace(style_process_ns, path='/style-processes')
api.add_namespace(style_elastic_ns, path='/style-elastics')

