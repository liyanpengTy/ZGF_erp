"""款号关联配置接口公共工具。"""

from app.api.common.context_helpers import get_factory_request_context
from app.utils.response import ApiResponse


def build_style_relation_access_error(error):
    """将款号关联模块的访问错误统一映射为接口响应。"""
    return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)


def get_style_relation_request_context(require_write=False):
    """获取款号关联接口所需的当前用户与工厂上下文。"""
    return get_factory_request_context(
        require_write=require_write,
        allow_internal_without_factory=True,
    )


def get_accessible_style_or_error(style_id, style_checker, require_write=False):
    """校验当前上下文是否可访问指定款号。"""
    current_user, current_factory_id, error_response_data = get_style_relation_request_context(
        require_write=require_write,
    )
    if error_response_data:
        return None, None, None, error_response_data

    style, error = style_checker(current_user, current_factory_id, style_id)
    if error:
        return None, None, None, build_style_relation_access_error(error)
    return current_user, current_factory_id, style, None


def get_accessible_style_resource_or_error(
    resource_id,
    resource_loader,
    permission_checker,
    not_found_message,
    require_write=False,
):
    """校验当前上下文是否可访问指定款号关联记录。"""
    current_user, current_factory_id, error_response_data = get_style_relation_request_context(
        require_write=require_write,
    )
    if error_response_data:
        return None, None, None, error_response_data

    resource = resource_loader(resource_id)
    if not resource:
        return None, None, None, ApiResponse.error(not_found_message, 404)

    has_permission, error = permission_checker(current_user, current_factory_id, resource)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, resource, None
