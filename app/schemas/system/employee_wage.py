"""员工计薪相关序列化定义。"""

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


WAGE_TYPE_CHOICES = ['monthly', 'piece', 'base_piece', 'hourly']


class EmployeeWageSchema(Schema):
    """员工计薪返回结构。"""

    id = fields.Int()
    factory_id = fields.Int()
    factory_name = fields.Str()
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
    effective_date = fields.Date(format='%Y-%m-%d')
    remark = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class EmployeeWageCreateSchema(Schema):
    """创建员工计薪入参。"""

    factory_id = fields.Int(required=True, validate=validate.Range(min=1))
    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    process_id = fields.Int(required=True, validate=validate.Range(min=1))
    wage_type = fields.Str(required=True, validate=validate.OneOf(WAGE_TYPE_CHOICES))
    monthly_salary = fields.Float(load_default=0, validate=validate.Range(min=0))
    piece_rate = fields.Float(load_default=0, validate=validate.Range(min=0))
    base_salary = fields.Float(load_default=0, validate=validate.Range(min=0))
    base_piece_rate = fields.Float(load_default=0, validate=validate.Range(min=0))
    hourly_rate = fields.Float(load_default=0, validate=validate.Range(min=0))
    effective_date = fields.Str(required=True, validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str()

    @validates_schema
    def validate_wage_fields(self, data, **kwargs):
        """根据计薪方式校验关键金额字段。"""
        wage_type = data.get('wage_type')
        if wage_type == 'monthly' and data.get('monthly_salary', 0) <= 0:
            raise ValidationError('月薪金额必须大于 0', field_name='monthly_salary')
        if wage_type == 'piece' and data.get('piece_rate', 0) <= 0:
            raise ValidationError('计件单价必须大于 0', field_name='piece_rate')
        if wage_type == 'base_piece':
            if data.get('base_salary', 0) <= 0:
                raise ValidationError('保底工资必须大于 0', field_name='base_salary')
            if data.get('base_piece_rate', 0) <= 0:
                raise ValidationError('保底计件单价必须大于 0', field_name='base_piece_rate')
        if wage_type == 'hourly' and data.get('hourly_rate', 0) <= 0:
            raise ValidationError('计时单价必须大于 0', field_name='hourly_rate')


class EmployeeWageUpdateSchema(Schema):
    """更新员工计薪入参。"""

    factory_id = fields.Int(validate=validate.Range(min=1))
    wage_type = fields.Str(validate=validate.OneOf(WAGE_TYPE_CHOICES))
    monthly_salary = fields.Float(validate=validate.Range(min=0))
    piece_rate = fields.Float(validate=validate.Range(min=0))
    base_salary = fields.Float(validate=validate.Range(min=0))
    base_piece_rate = fields.Float(validate=validate.Range(min=0))
    hourly_rate = fields.Float(validate=validate.Range(min=0))
    effective_date = fields.Str(validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str()


class WageCalculateSchema(Schema):
    """员工计薪试算入参。"""

    factory_id = fields.Int(required=True, validate=validate.Range(min=1))
    user_id = fields.Int(required=True, validate=validate.Range(min=1))
    process_id = fields.Int(required=True, validate=validate.Range(min=1))
    quantity = fields.Int(load_default=0, validate=validate.Range(min=0))
    work_hours = fields.Float(load_default=0, validate=validate.Range(min=0))
    work_days = fields.Float(load_default=1, validate=validate.Range(min=0))
    total_work_days = fields.Float(load_default=22, validate=validate.Range(min=0))
    work_date = fields.Str(validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
