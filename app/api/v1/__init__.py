from flask import Blueprint
from flask_restx import Api

# 直接导入所有命名空间
from app.api.v1.auth.auth import auth_ns
from app.api.v1.system.users import user_ns
from app.api.v1.system.roles import role_ns
from app.api.v1.system.menus import menu_ns
from app.api.v1.system.factories import factory_ns
from app.api.v1.system.logs import log_ns
from app.api.v1.system.monitor import monitor_ns
from app.api.v1.base_data.sizes import size_ns
from app.api.v1.base_data.categories import category_ns
from app.api.v1.base_data.colors import color_ns
from app.api.v1.business.styles import style_ns
from app.api.v1.business.style_prices import style_price_ns
from app.api.v1.business.style_processes import style_process_ns
from app.api.v1.business.style_elastics import style_elastic_ns
from app.api.v1.business.style_splices import style_splice_ns
from app.api.v1.profile.profile import profile_ns
from app.utils.response import ApiResponse
from flask_jwt_extended.exceptions import NoAuthorizationError, JWTExtendedException
from jwt.exceptions import DecodeError

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

api = Api(bp, doc='/docs', title='ZGF ERP PC端API', version='1.0',
          description='ZGF ERP 系统 PC 端 API 文档')


# JWT 错误处理 - 修复版本
@api.errorhandler(NoAuthorizationError)
def handle_no_auth(error):
    """缺少token"""
    response, status_code = ApiResponse.unauthorized('请先登录获取token')
    return response, status_code


@api.errorhandler(DecodeError)
def handle_decode_error(error):
    """token格式错误"""
    response, status_code = ApiResponse.unauthorized('Token格式错误，请重新登录')
    return response, status_code


@api.errorhandler(JWTExtendedException)
def handle_jwt_error(error):
    """token过期或其他JWT错误"""
    if "Expired" in str(error):
        response, status_code = ApiResponse.unauthorized('登录已过期，请重新登录')
    else:
        response, status_code = ApiResponse.unauthorized('认证失败')
    return response, status_code


@api.errorhandler(Exception)
def handle_all_errors(error):
    """其他所有异常 - 返回详细错误信息便于调试"""
    # 打印日志便于调试
    import traceback
    traceback.print_exc()

    response, status_code = ApiResponse.error(f'服务器错误: {str(error)}', 500)
    return response, status_code


# 添加所有命名空间
api.add_namespace(auth_ns, path='/auth')
api.add_namespace(user_ns, path='/system/users')
api.add_namespace(role_ns, path='/system/roles')
api.add_namespace(menu_ns, path='/system/menus')
api.add_namespace(factory_ns, path='/system/factories')
api.add_namespace(log_ns, path='/system/logs')
api.add_namespace(monitor_ns, path='/system/monitor')
api.add_namespace(size_ns, path='/base/sizes')
api.add_namespace(category_ns, path='/base/categories')
api.add_namespace(color_ns, path='/base/colors')
api.add_namespace(style_ns, path='/business/styles')
api.add_namespace(style_price_ns, path='/business/style-prices')
api.add_namespace(style_process_ns, path='/business/style-processes')
api.add_namespace(style_elastic_ns, path='/business/style-elastics')
api.add_namespace(style_splice_ns, path='/business/style-splices')
api.add_namespace(profile_ns, path='/profile')
