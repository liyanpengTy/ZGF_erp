from marshmallow import Schema, fields, validate


class FactorySchema(Schema):
    """工厂序列化器。"""

    id = fields.Int()
    name = fields.Str()
    code = fields.Str()
    contact_person = fields.Str()
    contact_phone = fields.Str()
    address = fields.Str()
    status = fields.Int()
    remark = fields.Str()
    service_expire_date = fields.Date(format='%Y-%m-%d', allow_none=True)
    service_status = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class FactoryCreateSchema(Schema):
    """创建工厂参数。"""

    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    code = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    contact_person = fields.Str(validate=validate.Length(max=50))
    contact_phone = fields.Str(validate=validate.Length(max=20))
    address = fields.Str(validate=validate.Length(max=255))
    service_expire_date = fields.Date(format='%Y-%m-%d', allow_none=True)
    remark = fields.Str(validate=validate.Length(max=500))


class FactoryUpdateSchema(Schema):
    """更新工厂参数。"""

    name = fields.Str(validate=validate.Length(min=2, max=100))
    contact_person = fields.Str(validate=validate.Length(max=50))
    contact_phone = fields.Str(validate=validate.Length(max=20))
    address = fields.Str(validate=validate.Length(max=255))
    service_expire_date = fields.Date(format='%Y-%m-%d', allow_none=True)
    status = fields.Int(validate=validate.OneOf([0, 1]))
    remark = fields.Str(validate=validate.Length(max=500))
