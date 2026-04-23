from marshmallow import Schema, fields, validate


class StyleElasticSchema(Schema):
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
    size_id = fields.Int()
    elastic_type = fields.Str(required=True)
    elastic_length = fields.Float(required=True)
    quantity = fields.Int(default=1)
    remark = fields.Str()


class StyleElasticUpdateSchema(Schema):
    size_id = fields.Int()
    elastic_type = fields.Str()
    elastic_length = fields.Float()
    quantity = fields.Int()
    remark = fields.Str()