"""接口查询参数解析工具。"""

from datetime import datetime

from flask import request
from flask_restx import reqparse
from werkzeug.datastructures import MultiDict


def positive_int(value):
    """校验正整数。"""
    try:
        parsed = int(value)
        if parsed < 1:
            raise ValueError()
        return parsed
    except ValueError as exc:
        raise ValueError("必须为正整数") from exc


def range_int(min_val, max_val):
    """返回一个用于校验整数范围的解析函数。"""

    def checker(value):
        try:
            parsed = int(value)
            if parsed < min_val or parsed > max_val:
                raise ValueError()
            return parsed
        except ValueError as exc:
            raise ValueError(f"必须是 {min_val} - {max_val} 之间的整数") from exc

    return checker


def validate_date(value):
    """校验日期格式 YYYY-MM-DD。"""
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError as exc:
        raise ValueError("日期格式必须为 YYYY-MM-DD") from exc


def is_empty_query(args, fields):
    """判断指定查询字段是否全部未传或为空字符串。"""
    return all(args.get(field) in (None, "") for field in fields)


def normalize_page_args(args, default_page=1, default_page_size=10, max_page_size=100):
    """规范化分页参数，兼容空字符串并校验范围。"""
    raw_page = args.get("page")
    raw_page_size = args.get("page_size")

    try:
        page = int(raw_page or default_page)
        page_size = int(raw_page_size or default_page_size)
    except (TypeError, ValueError) as exc:
        raise ValueError("page 和 page_size 必须为整数") from exc

    if page < 1:
        raise ValueError("page 必须大于等于 1")
    if page_size < 1 or page_size > max_page_size:
        raise ValueError(f"page_size 必须在 1 到 {max_page_size} 之间")

    return page, page_size


def _strip_blank_query_args(query_args):
    """移除值为空字符串的查询参数，避免空值触发类型转换报错。"""
    cleaned_args = MultiDict()
    for key in query_args.keys():
        for value in query_args.getlist(key):
            if value not in (None, ""):
                cleaned_args.add(key, value)
    return cleaned_args


class _RequestArgsProxy:
    """仅覆盖 request.args 的代理对象，其余属性透传原始 request。"""

    def __init__(self, raw_request):
        self._raw_request = raw_request
        self.args = _strip_blank_query_args(raw_request.args)

    def __getattr__(self, item):
        return getattr(self._raw_request, item)


class BlankFriendlyRequestParser(reqparse.RequestParser):
    """把空字符串查询参数统一按“未传”处理的解析器。"""

    def parse_args(self, req=None, strict=False):
        raw_request = req or request
        if hasattr(raw_request, "args") and not isinstance(raw_request, _RequestArgsProxy):
            raw_request = _RequestArgsProxy(raw_request)
        return super().parse_args(req=raw_request, strict=strict)


def new_query_parser():
    """创建支持空查询参数兼容的解析器。"""
    return BlankFriendlyRequestParser()


page_parser = new_query_parser()
page_parser.add_argument("page", type=positive_int, default=1, location="args", help="页码")
page_parser.add_argument("page_size", type=range_int(1, 100), default=10, location="args", help="每页数量")

id_parser = new_query_parser()
id_parser.add_argument("id", type=positive_int, required=True, location="args", help="ID")

status_parser = new_query_parser()
status_parser.add_argument("status", type=positive_int, location="args", help="状态", choices=[0, 1])

date_range_parser = new_query_parser()
date_range_parser.add_argument("start_date", type=validate_date, location="args", help="开始日期（YYYY-MM-DD）")
date_range_parser.add_argument("end_date", type=validate_date, location="args", help="结束日期（YYYY-MM-DD）")

page_with_date_parser = new_query_parser()
page_with_date_parser.add_argument("page", type=positive_int, default=1, location="args", help="页码")
page_with_date_parser.add_argument("page_size", type=range_int(1, 100), default=10, location="args", help="每页数量")
page_with_date_parser.add_argument("start_date", type=validate_date, location="args", help="开始日期（YYYY-MM-DD）")
page_with_date_parser.add_argument("end_date", type=validate_date, location="args", help="结束日期（YYYY-MM-DD）")
