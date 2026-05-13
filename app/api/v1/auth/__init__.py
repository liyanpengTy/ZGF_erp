"""V1 认证接口导出。"""

from app.api.v1.auth.auth import auth_ns

NAMESPACE_ROUTES = [
    (auth_ns, '/auth'),
]

__all__ = ['auth_ns', 'NAMESPACE_ROUTES']
