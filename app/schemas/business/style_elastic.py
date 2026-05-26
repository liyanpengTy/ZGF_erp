"""款号橡筋相关序列化定义。"""

from marshmallow import Schema, fields


class StyleElasticSchema(Schema):
    """款号橡筋返回结构。"""

    id = fields.Int()
    style_id = fields.Int(required=True)
    size_id = fields.Int()
    size_name = fields.Str()
    elastic_type = fields.Str(required=True)
    elastic_length = fields.Float(required=True)
    quantity = fields.Int(default=1)
    remark = fields.Str()
    create_time = fields.DateTime()


class StyleElasticCreateSchema(Schema):
    """创建款号橡筋请求结构。"""

    size_id = fields.Int()
    elastic_type = fields.Str(required=True)
    elastic_length = fields.Float(required=True)
    quantity = fields.Int(default=1)
    remark = fields.Str()


class StyleElasticUpdateSchema(Schema):
    """更新款号橡筋请求结构。"""

    size_id = fields.Int()
    elastic_type = fields.Str()
    elastic_length = fields.Float()
    quantity = fields.Int()
    remark = fields.Str()
