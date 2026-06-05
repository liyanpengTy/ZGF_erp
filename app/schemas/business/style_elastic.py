"""款号橡筋相关序列化定义。"""

from marshmallow import Schema, fields, validate


class StyleElasticSchema(Schema):
    """款号橡筋返回结构。"""

    id = fields.Int()
    style_id = fields.Int(required=True, validate=validate.Range(min=1))
    size_id = fields.Int(allow_none=True)
    size_name = fields.Str()
    elastic_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    elastic_length = fields.Float(required=True, validate=validate.Range(min=0, min_inclusive=False))
    quantity = fields.Int(load_default=1, validate=validate.Range(min=1))
    remark = fields.Str(validate=validate.Length(max=500))
    create_time = fields.DateTime()


class StyleElasticCreateSchema(Schema):
    """创建款号橡筋请求结构。"""

    style_id = fields.Int(required=True, validate=validate.Range(min=1))
    size_id = fields.Int(validate=validate.Range(min=1))
    elastic_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    elastic_length = fields.Float(required=True, validate=validate.Range(min=0, min_inclusive=False))
    quantity = fields.Int(load_default=1, validate=validate.Range(min=1))
    remark = fields.Str(validate=validate.Length(max=500))


class StyleElasticUpdateSchema(Schema):
    """更新款号橡筋请求结构。"""

    size_id = fields.Int(validate=validate.Range(min=1))
    elastic_type = fields.Str(validate=validate.Length(min=1, max=50))
    elastic_length = fields.Float(validate=validate.Range(min=0, min_inclusive=False))
    quantity = fields.Int(validate=validate.Range(min=1))
    remark = fields.Str(validate=validate.Length(max=500))


class StyleElasticBatchDetailSchema(Schema):
    """批量保存时的橡筋明细结构。"""

    size_id = fields.Int(required=True, validate=validate.Range(min=1))
    length = fields.Float(required=True, validate=validate.Range(min=0, min_inclusive=False))
    quantity = fields.Int(load_default=1, validate=validate.Range(min=1))
    remark = fields.Str(validate=validate.Length(max=500))


class StyleElasticBatchItemSchema(Schema):
    """批量保存时的橡筋分组结构。"""

    elastic_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    details = fields.List(
        fields.Nested(StyleElasticBatchDetailSchema),
        required=True,
        validate=validate.Length(min=1),
    )


class StyleElasticBatchCreateSchema(Schema):
    """批量保存款号橡筋请求结构。"""

    style_id = fields.Int(required=True, validate=validate.Range(min=1))
    items = fields.List(fields.Nested(StyleElasticBatchItemSchema), required=True)
