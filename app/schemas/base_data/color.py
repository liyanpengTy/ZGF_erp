from marshmallow import Schema, fields, validate


class ColorSchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    actual_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    factory_id = fields.Int(default=0)
    sort_order = fields.Int(default=0)
    status = fields.Int(default=1)
    remark = fields.Str()


class ColorCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    actual_name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    factory_id = fields.Int(default=0)
    sort_order = fields.Int(default=0)
    remark = fields.Str()


class ColorUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=50))
    actual_name = fields.Str(validate=validate.Length(min=1, max=50))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))
    remark = fields.Str()
