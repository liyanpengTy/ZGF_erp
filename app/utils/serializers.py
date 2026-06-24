"""通用序列化工具。"""

from app.utils.datetime_helper import safe_isoformat


def _apply_enricher(payload, obj, enricher=None):
    """对基础序列化结果做二次补充，避免各接口重复拼装字段。"""
    if not enricher:
        return payload
    enriched_payload = enricher(payload, obj)
    return payload if enriched_payload is None else enriched_payload


def serialize_schema(schema, obj, enricher=None):
    """基于 Marshmallow Schema 序列化单个对象。"""
    payload = schema.dump(obj)
    return _apply_enricher(payload, obj, enricher=enricher)


def serialize_schema_list(schema, items, enricher=None):
    """基于 Marshmallow Schema 批量序列化对象列表。"""
    return [serialize_schema(schema, item, enricher=enricher) for item in items]


def serialize_object_list(items, serializer):
    """使用指定序列化函数批量转换对象列表。"""
    return [serializer(item) for item in items]


def _resolve_mapping_value(obj, resolver):
    """解析映射序列化配置，支持属性名、格式化元组和回调函数。"""
    if callable(resolver):
        return resolver(obj)

    if isinstance(resolver, tuple):
        attr_name, formatter = resolver
        value = getattr(obj, attr_name, None)
        return formatter(value) if formatter else value

    return getattr(obj, resolver, None)


def build_mapping_serializer(field_mapping, enricher=None):
    """构建轻量对象序列化函数，适合 options 和摘要结构。"""

    def serializer(obj):
        payload = {
            field_name: _resolve_mapping_value(obj, resolver)
            for field_name, resolver in field_mapping.items()
        }
        return _apply_enricher(payload, obj, enricher=enricher)

    return serializer
