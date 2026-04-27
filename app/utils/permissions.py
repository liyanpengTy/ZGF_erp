from functools import wraps
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.utils.response import ApiResponse


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

    # 保留原函数的文档字符串和属性（用于 Swagger）
    return wrapper


def permission_required(permission_code):
    """权限验证装饰器"""
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            # TODO: 实现权限验证逻辑
            return fn(*args, **kwargs)
        return wrapper
    return decorator