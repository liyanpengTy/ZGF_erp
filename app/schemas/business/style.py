"""款号相关序列化器。"""

from marshmallow import Schema, fields, validate


class StyleSchema(Schema):
    """款号序列化器。"""

    id = fields.Int()
    factory_id = fields.Int(required=True)
    style_no = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    customer_style_no = fields.Str()
    name = fields.Str()
    category_id = fields.Int()
    gender = fields.Str()
    season = fields.Str()
    material = fields.Str()
    description = fields.Str()
    status = fields.Int(default=1)
    images = fields.List(fields.Str())
    need_cutting = fields.Int(default=0)
    cutting_reserve = fields.Float(default=0)
    custom_attributes = fields.Dict()
    is_splice = fields.Int(default=0, validate=validate.OneOf([0, 1]))
    splice_data = fields.List(fields.Dict(), description='拼接数据，格式：[{"sequence":1,"description":"红色棉麻"}]')
    create_time = fields.DateTime()
    update_time = fields.DateTime()


class StyleCreateSchema(Schema):
    """创建款号参数。"""

    style_no = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    customer_style_no = fields.Str()
    name = fields.Str()
    category_id = fields.Int()
    gender = fields.Str()
    season = fields.Str()
    material = fields.Str()
    description = fields.Str()
    images = fields.List(fields.Str())
    need_cutting = fields.Int(default=0)
    cutting_reserve = fields.Float(default=0)
    custom_attributes = fields.Dict()
    is_splice = fields.Int(default=0, validate=validate.OneOf([0, 1]))
    splice_data = fields.List(fields.Dict(), description='拼接数据')


class StyleUpdateSchema(Schema):
    """更新款号参数。"""

    style_no = fields.Str(validate=validate.Length(min=1, max=50))
    customer_style_no = fields.Str()
    name = fields.Str()
    category_id = fields.Int()
    gender = fields.Str()
    season = fields.Str()
    material = fields.Str()
    description = fields.Str()
    status = fields.Int(validate=validate.OneOf([0, 1]))
    images = fields.List(fields.Str())
    need_cutting = fields.Int()
    cutting_reserve = fields.Float()
    custom_attributes = fields.Dict()
    is_splice = fields.Int(validate=validate.OneOf([0, 1]))
    splice_data = fields.List(fields.Dict(), description='拼接数据')
