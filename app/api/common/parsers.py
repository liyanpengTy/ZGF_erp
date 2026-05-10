from flask_restx import reqparse
from datetime import datetime


def positive_int(value):
    """校验正整数"""
    try:
        ival = int(value)
        if ival < 1:
            raise ValueError()
        return ival
    except ValueError:
        raise ValueError('必须为正整数')


def range_int(min_val, max_val):
    """校验范围内的整数"""
    def checker(value):
        try:
            ival = int(value)
            if ival < min_val or ival > max_val:
                raise ValueError(f'取值范围 {min_val} - {max_val}')
            return ival
        except ValueError:
            raise ValueError(f'必须为 {min_val} - {max_val} 之间的整数')
    return checker


def validate_date(value):
    """校验日期格式 YYYY-MM-DD"""
    from datetime import datetime
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return value
    except ValueError:
        raise ValueError('日期格式必须为 YYYY-MM-DD')


# 通用分页解析器
page_parser = reqparse.RequestParser()
page_parser.add_argument('page', type=positive_int, default=1, location='args', help='页码')
page_parser.add_argument('page_size', type=range_int(1, 100), default=10, location='args', help='每页数量')

# 通用 ID 解析器
id_parser = reqparse.RequestParser()
id_parser.add_argument('id', type=positive_int, required=True, location='args', help='ID')

# 通用状态解析器
status_parser = reqparse.RequestParser()
status_parser.add_argument('status', type=positive_int, location='args', help='状态', choices=[0, 1])

# 日期范围解析器
date_range_parser = reqparse.RequestParser()
date_range_parser.add_argument('start_date', type=validate_date, location='args', help='开始日期(YYYY-MM-DD)')
date_range_parser.add_argument('end_date', type=validate_date, location='args', help='结束日期(YYYY-MM-DD)')

# 日期范围分页解析器
page_with_date_parser = reqparse.RequestParser()
page_with_date_parser.add_argument('page', type=positive_int, default=1, location='args', help='页码')
page_with_date_parser.add_argument('page_size', type=range_int(1, 100), default=10, location='args', help='每页数量')
page_with_date_parser.add_argument('start_date', type=validate_date, location='args', help='开始日期(YYYY-MM-DD)')
page_with_date_parser.add_argument('end_date', type=validate_date, location='args', help='结束日期(YYYY-MM-DD)')
