"""员工计酬序列化器"""
from marshmallow import Schema, fields, validate


class EmployeeWageSchema(Schema):
    """员工计酬序列化器"""
    id = fields.Int()
    user_id = fields.Int()
    username = fields.Str()
    nickname = fields.Str()
    process_id = fields.Int()
    process_name = fields.Str()
    wage_type = fields.Str()
    wage_type_label = fields.Str()
    monthly_salary = fields.Float()
    piece_rate = fields.Float()
    base_salary = fields.Float()
    base_piece_rate = fields.Float()
    hourly_rate = fields.Float()
    effective_date = fields.DateTime(format='%Y-%m-%d')
    remark = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class EmployeeWageCreateSchema(Schema):
    """创建员工计酬参数"""
    user_id = fields.Int(required=True)
    process_id = fields.Int(required=True)
    wage_type = fields.Str(required=True, validate=validate.OneOf(['monthly', 'piece', 'base_piece', 'hourly']))
    monthly_salary = fields.Float(default=0)
    piece_rate = fields.Float(default=0)
    base_salary = fields.Float(default=0)
    base_piece_rate = fields.Float(default=0)
    hourly_rate = fields.Float(default=0)
    effective_date = fields.Str(required=True, validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str()


class EmployeeWageUpdateSchema(Schema):
    """更新员工计酬参数"""
    wage_type = fields.Str(validate=validate.OneOf(['monthly', 'piece', 'base_piece', 'hourly']))
    monthly_salary = fields.Float()
    piece_rate = fields.Float()
    base_salary = fields.Float()
    base_piece_rate = fields.Float()
    hourly_rate = fields.Float()
    effective_date = fields.Str(validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str()
