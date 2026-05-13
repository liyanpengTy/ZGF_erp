"""V1 个人中心接口导出。"""

from app.api.v1.profile.profile import profile_ns

NAMESPACE_ROUTES = [
    (profile_ns, '/profile'),
]

__all__ = ['profile_ns', 'NAMESPACE_ROUTES']
