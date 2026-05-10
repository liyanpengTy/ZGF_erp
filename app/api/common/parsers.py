from flask_restx import reqparse
from datetime import datetime


def validate_date(value):
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return value
    except ValueError:
        raise ValueError('日期格式必须为 YYYY-MM-DD')


# 通用分页解析器
page_parser = reqparse.RequestParser()
page_parser.add_argument('page', type=int, default=1, location='args', help='页码', min=1)
page_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量', min=1, max=100)

# 通用 ID 解析器
id_parser = reqparse.RequestParser()
id_parser.add_argument('id', type=int, required=True, location='args', help='ID', min=1)

# 通用状态解析器
status_parser = reqparse.RequestParser()
status_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

# 日期范围解析器
date_range_parser = reqparse.RequestParser()
date_range_parser.add_argument('start_date', type=validate_date, location='args', help='开始日期(YYYY-MM-DD)')
date_range_parser.add_argument('end_date', type=validate_date, location='args', help='结束日期(YYYY-MM-DD)')

# 日期范围分页解析器
page_with_date_parser = reqparse.RequestParser()
page_with_date_parser.add_argument('page', type=int, default=1, min=1)
page_with_date_parser.add_argument('page_size', type=int, default=10, min=1, max=100)
page_with_date_parser.add_argument('start_date', type=validate_date, location='args', help='开始日期(YYYY-MM-DD)')
page_with_date_parser.add_argument('end_date', type=validate_date, location='args', help='结束日期(YYYY-MM-DD)')