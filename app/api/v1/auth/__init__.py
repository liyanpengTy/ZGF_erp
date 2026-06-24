"""V1 认证接口导出。"""

from app.api.common.namespace_registry import build_namespace_routes
from app.api.v1.auth.auth import auth_ns

NAMESPACE_ROUTES = build_namespace_routes(
    (auth_ns, '/auth'),
)

__all__ = ['auth_ns', 'NAMESPACE_ROUTES']
