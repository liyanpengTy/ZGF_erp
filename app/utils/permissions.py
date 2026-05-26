"""权限校验工具。"""

from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.constants.identity import (
    ROLE_SCOPE_FACTORY,
    ROLE_SCOPE_PLATFORM,
    is_internal_platform_identity,
    is_write_permission,
)
from app.extensions import db
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.user_factory_role import UserFactoryRole
from app.utils.response import ApiResponse


def login_required(fn):
    """登录验证装饰器。"""

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
            if 'Missing' in error_str:
                return ApiResponse.unauthorized('请登录')
            if 'CSRF' in error_str:
                return ApiResponse.unauthorized('CSRF 验证失败')
            return ApiResponse.unauthorized(f'认证失败: {error_str}')

    return wrapper


def refresh_required(fn):
    """refresh token 专用装饰器。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request(refresh=True)
            return fn(*args, **kwargs)
        except ExpiredSignatureError:
            return ApiResponse.unauthorized('refresh_token 已过期，请重新登录')
        except InvalidTokenError:
            return ApiResponse.unauthorized('无效的 refresh_token，请重新登录')
        except Exception as e:
            error_str = str(e)
            if 'Missing' in error_str:
                return ApiResponse.unauthorized('请提供 refresh_token')
            if 'CSRF' in error_str:
                return ApiResponse.unauthorized('CSRF 验证失败')
            if 'Only non-refresh tokens are allowed' in error_str:
                return ApiResponse.unauthorized('请使用 refresh_token')
            return ApiResponse.unauthorized(f'认证失败: {error_str}')

    return wrapper


def get_current_user():
    """在需要直接取当前用户对象的场景下复用 JWT 解析逻辑。"""
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        if isinstance(current_user_id, dict):
            current_user_id = current_user_id.get('user_id')
        else:
            current_user_id = int(current_user_id)
        return User.query.filter_by(id=current_user_id, is_deleted=0).first()
    except Exception:
        return None


def get_current_factory_id():
    """在请求上下文中快捷获取当前工厂 ID。"""
    try:
        return get_jwt().get('factory_id')
    except Exception:
        return None


def _get_platform_role_ids(user_id):
    """获取用户绑定的平台级角色 ID 列表。"""
    role_records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
        UserFactoryRole.user_id == user_id,
        UserFactoryRole.factory_id == 0,
        UserFactoryRole.is_deleted == 0,
        Role.scope_type == ROLE_SCOPE_PLATFORM,
        Role.scope_id == 0,
        Role.status == 1,
        Role.is_deleted == 0
    ).all()
    return [record.role_id for record in role_records]


def _get_factory_role_ids(user_id, factory_id):
    """获取用户在指定工厂上下文下的角色 ID 列表。"""
    role_records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
        UserFactoryRole.user_id == user_id,
        UserFactoryRole.factory_id == factory_id,
        UserFactoryRole.is_deleted == 0,
        Role.scope_type == ROLE_SCOPE_FACTORY,
        Role.scope_id == factory_id,
        Role.status == 1,
        Role.is_deleted == 0
    ).all()
    return [record.role_id for record in role_records]


def _has_menu_permission(role_ids, permission_code):
    """根据角色集合判断是否命中目标菜单权限编码。"""
    if not role_ids:
        return False

    menu_records = db.session.query(role_menu).filter(role_menu.c.role_id.in_(role_ids)).all()
    menu_ids = list(set(record.menu_id for record in menu_records))
    if not menu_ids:
        return False

    menus = Menu.query.filter(
        Menu.id.in_(menu_ids),
        Menu.permission == permission_code,
        Menu.status == 1,
        Menu.is_deleted == 0
    ).all()
    return bool(menus)


def has_any_permission(user, permission_codes, factory_id=None):
    """校验当前用户是否至少拥有一项指定权限编码。"""
    permission_codes = [code for code in (permission_codes or []) if code]
    if not user:
        return False, '用户不存在'
    if user.status != 1:
        return False, '账号已被禁用'
    if user.is_platform_admin:
        return True, None
    if not permission_codes:
        return False, '未指定权限编码'

    claims = get_jwt()
    platform_identity = claims.get('platform_identity') or user.platform_identity

    if is_internal_platform_identity(platform_identity):
        role_ids = _get_platform_role_ids(user.id)
        if any(_has_menu_permission(role_ids, permission_code) for permission_code in permission_codes):
            return True, None
        return False, f"无权限: {' / '.join(permission_codes)}"

    target_factory_id = factory_id or claims.get('factory_id')
    if not target_factory_id:
        return False, '当前未选择工厂上下文'

    factory = Factory.query.filter_by(id=target_factory_id, is_deleted=0).first()
    if not factory:
        return False, '工厂不存在'

    if any(is_write_permission(permission_code) for permission_code in permission_codes):
        if factory.service_status in {'expired', 'disabled'}:
            return False, '当前工厂已过期或被禁用，续期后可继续操作'

    role_ids = _get_factory_role_ids(user.id, target_factory_id)
    if any(_has_menu_permission(role_ids, permission_code) for permission_code in permission_codes):
        return True, None
    return False, f"无权限: {' / '.join(permission_codes)}"


def permission_required(permission_code):
    """权限验证装饰器。"""

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            """统一做用户状态、平台角色、工厂角色和过期写入拦截。"""
            current_user_id = get_jwt_identity()
            if isinstance(current_user_id, dict):
                current_user_id = current_user_id.get('user_id')
            else:
                current_user_id = int(current_user_id)

            user = User.query.filter_by(id=current_user_id, is_deleted=0).first()
            has_permission, error = has_any_permission(user, [permission_code])
            if not has_permission:
                if error in {'用户不存在', '账号已被禁用'}:
                    return ApiResponse.unauthorized(error)
                return ApiResponse.forbidden(error)

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def permission_required_any(permission_codes):
    """权限装饰器，命中任一权限编码即可访问。"""

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            if isinstance(current_user_id, dict):
                current_user_id = current_user_id.get('user_id')
            else:
                current_user_id = int(current_user_id)

            user = User.query.filter_by(id=current_user_id, is_deleted=0).first()
            has_permission, error = has_any_permission(user, permission_codes)
            if not has_permission:
                if error in {'用户不存在', '账号已被禁用'}:
                    return ApiResponse.unauthorized(error)
                return ApiResponse.forbidden(error)

            return fn(*args, **kwargs)

        return wrapper

    return decorator
