"""API 层公共认证上下文工具。"""

from flask_jwt_extended import get_jwt

from app.services import AuthService
from app.utils.response import ApiResponse


def get_current_user():
    """获取当前登录用户对象。"""
    return AuthService.get_current_user()


def get_current_factory_id():
    """获取当前 token 中的工厂上下文 ID。"""
    return AuthService.get_current_factory_id()


def get_current_claims():
    """获取当前 token 的完整 claims。"""
    try:
        return get_jwt()
    except Exception:
        return {}


def require_current_user(message='用户不存在', code=401):
    """获取当前登录用户，不存在时返回统一错误响应。"""
    current_user = get_current_user()
    if not current_user:
        return None, ApiResponse.error(message, code)
    return current_user, None
