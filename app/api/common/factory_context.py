"""业务接口工厂上下文解析工具。"""

from app.api.common.auth import get_current_factory_id, get_current_user
from app.services import FactoryService
from app.utils.response import ApiResponse


def resolve_factory_context(require_write=False, query_factory_id=None, allow_internal_without_factory=False):
    """解析当前请求的工厂上下文，并按读写场景校验访问权限。"""
    current_user = get_current_user()
    current_factory_id = get_current_factory_id()

    if not current_user:
        return None, None, ApiResponse.error("用户不存在", 401)

    if require_write:
        if not current_factory_id:
            return None, None, ApiResponse.error("当前缺少工厂上下文，请先切换工厂", 400)
        has_permission, error = FactoryService.check_factory_permission(
            current_user,
            current_factory_id,
            require_write=True,
        )
        if not has_permission:
            status_code = 403 if "无权限" in error or "续期" in error else 404
            return None, None, ApiResponse.error(error, status_code)
        return current_user, current_factory_id, None

    target_factory_id = query_factory_id or current_factory_id
    if target_factory_id:
        has_permission, error = FactoryService.check_factory_permission(
            current_user,
            target_factory_id,
            require_write=False,
        )
        if not has_permission:
            status_code = 403 if "无权限" in error or "续期" in error else 404
            return None, None, ApiResponse.error(error, status_code)
        return current_user, target_factory_id, None

    if allow_internal_without_factory and current_user.is_internal_user:
        return current_user, None, None

    return None, None, ApiResponse.error("当前缺少工厂上下文，请先切换工厂", 400)
