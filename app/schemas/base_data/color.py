"""颜色相关序列化定义。"""

from marshmallow import Schema, fields, validate


class ColorSchema(Schema):
    """颜色返回结构。"""

    id = fields.Int()
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    actual_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    factory_id = fields.Int(dump_default=0)
    sort_order = fields.Int(dump_default=0)
    status = fields.Int(dump_default=1)
    remark = fields.Str()


class ColorCreateSchema(Schema):
    """创建颜色请求结构。"""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    actual_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    factory_id = fields.Int(load_default=0)
    sort_order = fields.Int(load_default=0)
    remark = fields.Str()


class ColorUpdateSchema(Schema):
    """更新颜色请求结构。"""

    name = fields.Str(validate=validate.Length(min=1, max=50))
    actual_name = fields.Str(validate=validate.Length(min=1, max=50))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))
    remark = fields.Str()
