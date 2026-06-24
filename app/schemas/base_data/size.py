"""尺码相关序列化定义。"""

from marshmallow import Schema, fields, validate


class SizeSchema(Schema):
    """尺码返回结构。"""

    id = fields.Int()
    name = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    factory_id = fields.Int(dump_default=0)
    sort_order = fields.Int(dump_default=0)
    status = fields.Int(dump_default=1)


class SizeCreateSchema(Schema):
    """创建尺码请求结构。"""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    factory_id = fields.Int(load_default=0)
    sort_order = fields.Int(load_default=0)


class SizeUpdateSchema(Schema):
    """更新尺码请求结构。"""

    name = fields.Str(validate=validate.Length(min=1, max=20))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))
