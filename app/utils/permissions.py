from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.utils.response import ApiResponse
from app.extensions import db
from app.models.auth.user import User
from app.models.system.role import role_menu
from app.models.system.user_factory_role import UserFactoryRole
from app.models.system.menu import Menu


def login_required(fn):
    """登录验证装饰器（捕获 JWT 异常，兼容 Swagger）"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except ExpiredSignatureError:
            return ApiResponse.unauthorized('登录已过期，请重新登录')
        except InvalidTokenError:
            return ApiResponse.unauthorized('无效的认证信息，请重新登录')
        except Exception as e:
            error_str = str(e)
            if "Missing" in error_str:
                return ApiResponse.unauthorized('请登录')
            if "CSRF" in error_str:
                return ApiResponse.unauthorized('CSRF 验证失败')
            return ApiResponse.unauthorized(f'认证失败: {error_str}')

    return wrapper


def refresh_required(fn):
    """刷新Token专用装饰器（验证 refresh_token）"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # 关键：设置 refresh=True
            verify_jwt_in_request(refresh=True)
            return fn(*args, **kwargs)
        except ExpiredSignatureError:
            return ApiResponse.unauthorized('refresh_token已过期，请重新登录')
        except InvalidTokenError:
            return ApiResponse.unauthorized('无效的refresh_token，请重新登录')
        except Exception as e:
            error_str = str(e)
            if "Missing" in error_str:
                return ApiResponse.unauthorized('请提供refresh_token')
            if "CSRF" in error_str:
                return ApiResponse.unauthorized('CSRF 验证失败')
            if "Only non-refresh tokens are allowed" in error_str:
                return ApiResponse.unauthorized('请使用refresh_token')
            return ApiResponse.unauthorized(f'认证失败: {error_str}')
    return wrapper


def get_current_user():
    """获取当前登录用户"""
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        if isinstance(current_user_id, dict):
            current_user_id = current_user_id.get('user_id')
        else:
            current_user_id = int(current_user_id)
        return User.query.filter_by(id=current_user_id, is_deleted=0).first()
    except:
        return None


def get_current_factory_id():
    """获取当前用户所在工厂ID"""
    try:
        claims = get_jwt()
        return claims.get('factory_id')
    except:
        return None


def permission_required(permission_code):
    """
    权限验证装饰器
    检查当前用户是否拥有指定权限
    使用方式: @permission_required('system:user:add')
    """

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            # 获取当前用户
            current_user_id = get_jwt_identity()
            if isinstance(current_user_id, dict):
                current_user_id = current_user_id.get('user_id')
            else:
                current_user_id = int(current_user_id)

            user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

            if not user:
                return ApiResponse.unauthorized('用户不存在')

            if user.status != 1:
                return ApiResponse.unauthorized('账号已被禁用')

            # 超级管理员（is_admin=1）拥有所有权限
            if user.is_admin == 1:
                return fn(*args, **kwargs)

            # 获取用户在当前工厂下的角色
            from flask_jwt_extended import get_jwt
            claims = get_jwt()
            factory_id = claims.get('factory_id')

            if not factory_id:
                return ApiResponse.forbidden('无权限访问')

            # 查询用户在该工厂下的所有角色
            role_records = UserFactoryRole.query.filter_by(
                user_id=user.id,
                factory_id=factory_id,
                is_deleted=0
            ).all()

            role_ids = [r.role_id for r in role_records]

            if not role_ids:
                return ApiResponse.forbidden('无权限访问')

            # 查询角色关联的所有菜单权限
            menu_records = db.session.query(role_menu).filter(
                role_menu.c.role_id.in_(role_ids)
            ).all()

            menu_ids = list(set([r.menu_id for r in menu_records]))

            if not menu_ids:
                return ApiResponse.forbidden('无权限访问')

            # 查询是否有匹配的权限标识
            menus = Menu.query.filter(
                Menu.id.in_(menu_ids),
                Menu.permission == permission_code,
                Menu.status == 1,
                Menu.is_deleted == 0
            ).all()

            if not menus:
                return ApiResponse.forbidden(f'无权限: {permission_code}')

            return fn(*args, **kwargs)

        return wrapper

    return decorator


