"""业务接口权限工具，统一承载按钮级权限装饰器。"""

from app.utils.permissions import permission_required


def button_permission(permission_code):
    """返回按钮级权限装饰器，避免业务接口散落直接依赖底层鉴权实现。"""
    return permission_required(permission_code)
