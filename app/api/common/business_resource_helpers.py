"""业务资源访问公共工具。"""

from app.api.common.context_helpers import get_factory_request_context
from app.utils.response import ApiResponse


def get_business_request_context(query_factory_id=None, require_write=False, allow_internal_without_factory=True):
    """统一解析业务接口的当前用户与工厂上下文。"""
    return get_factory_request_context(
        query_factory_id=query_factory_id,
        require_write=require_write,
        allow_internal_without_factory=allow_internal_without_factory,
    )


def get_accessible_business_resource_or_error(
    resource_id,
    loader,
    permission_checker,
    not_found_message,
    query_factory_id=None,
    allow_internal_without_factory=True,
):
    """查询当前上下文可访问的业务资源。"""
    current_user, current_factory_id, error_response_data = get_business_request_context(
        query_factory_id=query_factory_id,
        allow_internal_without_factory=allow_internal_without_factory,
    )
    if error_response_data:
        return None, None, None, error_response_data

    resource = loader(resource_id)
    if not resource:
        return None, None, None, ApiResponse.error(not_found_message, 404)

    has_permission, error = permission_checker(current_user, current_factory_id, resource)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, resource, None


def get_writable_business_resource_or_error(
    resource_id,
    loader,
    permission_checker,
    not_found_message,
    scope_matcher=None,
):
    """查询当前工厂上下文下可写入的业务资源。"""
    current_user, current_factory_id, error_response_data = get_business_request_context(require_write=True)
    if error_response_data:
        return None, None, None, error_response_data

    resource = loader(resource_id)
    if not resource:
        return None, None, None, ApiResponse.error(not_found_message, 404)

    if scope_matcher is None:
        scope_matcher = lambda item, scope_id: getattr(item, 'factory_id', None) == scope_id

    if not scope_matcher(resource, current_factory_id):
        return None, None, None, ApiResponse.error(not_found_message, 404)

    has_permission, error = permission_checker(current_user, current_factory_id, resource)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, resource, None
