# 权限装饰器
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request
from app.utils.response import ApiResponse


def login_required(fn):
    """登录验证装饰器"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception:
            return ApiResponse.unauthorized()
    return wrapper


def permission_required(permission_code):
    """权限验证装饰器（后续实现）"""
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            # TODO: 验证用户是否有指定权限
            return fn(*args, **kwargs)
        return wrapper
    return decorator
