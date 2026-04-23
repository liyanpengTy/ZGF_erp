from marshmallow import Schema, fields, validate


class StyleProcessSchema(Schema):
    id = fields.Int()
    style_id = fields.Int(required=True)
    process_type = fields.Str(required=True, validate=validate.OneOf(['embroidery', 'print', 'other']))
    process_name = fields.Str()
    remark = fields.Str()
    create_time = fields.DateTime()


class StyleProcessCreateSchema(Schema):
    process_type = fields.Str(required=True, validate=validate.OneOf(['embroidery', 'print', 'other']))
    process_name = fields.Str()
    remark = fields.Str()


class StyleProcessUpdateSchema(Schema):
    process_type = fields.Str(validate=validate.OneOf(['embroidery', 'print', 'other']))
    process_name = fields.Str()
    remark = fields.Str()
