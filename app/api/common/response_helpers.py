"""接口响应辅助工具。"""

from marshmallow import ValidationError

from app.utils.response import ApiResponse
from app.utils.serializers import serialize_schema_list


def load_json_or_error(schema, payload):
    """使用 Marshmallow Schema 解析 JSON，失败时返回统一 400 响应。"""
    try:
        return schema.load(payload or {}), None
    except ValidationError as exc:
        return None, ApiResponse.error(str(exc.messages), 400)


def success_schema_page(result, schema, message='操作成功', extra=None, code=200):
    """序列化分页 items 后返回统一分页响应。"""
    return ApiResponse.success_page_result(
        result,
        serialize_schema_list(schema, result['items']),
        message=message,
        extra=extra,
        code=code,
    )


def success_mapped_page(result, items, message='操作成功', extra=None, code=200):
    """使用已转换好的 items 返回统一分页响应。"""
    return ApiResponse.success_mapped_page(result, items, message=message, extra=extra, code=code)


def infer_error_code(message, default=400):
    """根据常见业务错误文案推断 HTTP 状态码，避免接口层重复判断。"""
    if not message:
        return default
    if '不存在' in message:
        return 404
    if '无权限' in message or '不允许' in message or '请先登录' in message:
        return 403
    if '已存在' in message or '重复' in message or '冲突' in message:
        return 409
    return default


def business_error(message, default=400):
    """返回按业务文案推断状态码后的错误响应。"""
    return ApiResponse.error(message, infer_error_code(message, default))
