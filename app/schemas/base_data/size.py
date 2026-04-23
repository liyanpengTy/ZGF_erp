from marshmallow import Schema, fields, validate


class SizeSchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    factory_id = fields.Int(default=0)
    sort_order = fields.Int(default=0)
    status = fields.Int(default=1)


class SizeCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    factory_id = fields.Int(default=0)
    sort_order = fields.Int(default=0)


class SizeUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=20))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))
