from marshmallow import Schema, fields, validate


class StyleSpliceSchema(Schema):
    id = fields.Int()
    style_id = fields.Int(required=True)
    splice_type = fields.Str(required=True, validate=validate.OneOf(['color', 'fabric', 'lace', 'other']))
    material_id = fields.Int()
    material_name = fields.Str()
    material_code = fields.Str()
    sort_order = fields.Int(default=0)
    remark = fields.Str()
    create_time = fields.DateTime()


class StyleSpliceCreateSchema(Schema):
    splice_type = fields.Str(required=True, validate=validate.OneOf(['color', 'fabric', 'lace', 'other']))
    material_id = fields.Int()
    material_name = fields.Str()
    material_code = fields.Str()
    sort_order = fields.Int(default=0)
    remark = fields.Str()


class StyleSpliceUpdateSchema(Schema):
    splice_type = fields.Str(validate=validate.OneOf(['color', 'fabric', 'lace', 'other']))
    material_id = fields.Int()
    material_name = fields.Str()
    material_code = fields.Str()
    sort_order = fields.Int()
    remark = fields.Str()
