from marshmallow import Schema, fields, validate


class CategorySchema(Schema):
    id = fields.Int()
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    parent_id = fields.Int(default=0)
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    factory_id = fields.Int(default=0)
    sort_order = fields.Int(default=0)
    status = fields.Int(default=1)
    children = fields.List(fields.Nested(lambda: CategorySchema()), default=[])


class CategoryCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    parent_id = fields.Int(default=0)
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    factory_id = fields.Int(default=0)
    sort_order = fields.Int(default=0)


class CategoryUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=50))
    parent_id = fields.Int()
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))
