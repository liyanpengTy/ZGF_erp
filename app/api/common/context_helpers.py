"""API 上下文解析公共工具。"""

from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context


def get_factory_request_context(
    query_factory_id=None,
    require_write=False,
    allow_internal_without_factory=True,
    allow_internal_write_without_factory=False,
):
    """统一解析当前请求的用户与工厂上下文。"""
    if not require_write:
        return resolve_read_factory_context(
            query_factory_id=query_factory_id,
            allow_internal_without_factory=allow_internal_without_factory,
        )

    if not allow_internal_write_without_factory:
        return resolve_write_factory_context()

    current_user, current_factory_id, error_response_data = resolve_read_factory_context(
        query_factory_id=query_factory_id,
        allow_internal_without_factory=allow_internal_without_factory,
    )
    if error_response_data:
        return None, None, error_response_data

    if current_user and current_user.is_internal_user and not current_factory_id:
        return current_user, current_factory_id, None

    return resolve_write_factory_context()
