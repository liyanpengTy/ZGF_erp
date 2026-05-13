"""API 层公共认证上下文工具。"""

from flask_jwt_extended import get_jwt

from app.services import AuthService


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
