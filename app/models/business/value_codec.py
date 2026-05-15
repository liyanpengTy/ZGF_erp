"""业务模型动态值编解码工具。"""

from decimal import Decimal


def encode_dynamic_value(value):
    """把动态值编码成数据库可持久化的类型和值。"""
    if value is None:
        return 'null', ''
    if isinstance(value, bool):
        return 'bool', '1' if value else '0'
    if isinstance(value, int):
        return 'int', str(value)
    if isinstance(value, (float, Decimal)):
        return 'float', str(value)
    return 'str', str(value)


def decode_dynamic_value(value_type, raw_value):
    """把数据库中的动态值还原成接口层使用的 Python 值。"""
    if value_type == 'null':
        return None
    if value_type == 'bool':
        return raw_value == '1'
    if value_type == 'int':
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return 0
    if value_type == 'float':
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return 0.0
    return raw_value


def is_scalar_value(value):
    """判断值是否适合按标量写入属性明细表。"""
    return value is None or isinstance(value, (bool, int, float, Decimal, str))
