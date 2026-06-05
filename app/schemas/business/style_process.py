"""款号工艺相关序列化定义。"""

from marshmallow import Schema, fields, validate


class StyleProcessSchema(Schema):
    """款号工艺返回结构。"""

    id = fields.Int()
    style_id = fields.Int(required=True)
    process_type = fields.Str(required=True, validate=validate.OneOf(["embroidery", "print", "other"]))
    process_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    remark = fields.Str()
    create_time = fields.DateTime()


class StyleProcessCreateSchema(Schema):
    """创建款号工艺入参。"""

    style_id = fields.Int(required=True)
    process_type = fields.Str(required=True, validate=validate.OneOf(["embroidery", "print", "other"]))
    process_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    remark = fields.Str()


class StyleProcessUpdateSchema(Schema):
    """更新款号工艺入参。"""

    process_type = fields.Str(validate=validate.OneOf(["embroidery", "print", "other"]))
    process_name = fields.Str(validate=validate.Length(min=1, max=100))
    remark = fields.Str()
