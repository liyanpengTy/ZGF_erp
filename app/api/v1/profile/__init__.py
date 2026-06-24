"""V1 个人中心接口导出。"""

from app.api.common.namespace_registry import build_namespace_routes
from app.api.v1.profile.profile import profile_ns

NAMESPACE_ROUTES = build_namespace_routes(
    (profile_ns, '/profile'),
)

__all__ = ['profile_ns', 'NAMESPACE_ROUTES']
