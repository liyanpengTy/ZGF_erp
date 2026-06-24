"""日期时间通用工具。"""


def safe_isoformat(value):
    """安全序列化日期/时间对象；为空时返回 None。"""
    return value.isoformat() if value else None
