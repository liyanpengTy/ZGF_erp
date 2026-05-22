"""接口资源查询与权限结果的公共处理工具。"""

from app.utils.response import ApiResponse


def get_resource_or_error(loader, not_found_message='资源不存在', not_found_code=404):
    """执行资源查询，并在结果为空时返回统一错误响应。"""
    resource = loader()
    if not resource:
        return None, ApiResponse.error(not_found_message, not_found_code)
    return resource, None


def ensure_permission_or_error(has_permission, error_message='无权限', error_code=403):
    """将布尔权限结果转换为统一错误响应。"""
    if has_permission:
        return None
    return ApiResponse.error(error_message, error_code)
