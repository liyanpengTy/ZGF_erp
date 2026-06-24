"""个人中心服务导出。"""

from app.services.profile.profile_service import ProfileService

PROFILE_SERVICE_EXPORTS = (
    'ProfileService',
)

__all__ = list(PROFILE_SERVICE_EXPORTS)
