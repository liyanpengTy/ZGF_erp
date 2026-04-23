from marshmallow import Schema, fields, validate


class StylePriceSchema(Schema):
    id = fields.Int()
    style_id = fields.Int(required=True)
    price_type = fields.Str(required=True, validate=validate.OneOf(['customer', 'internal', 'outsourced', 'button', 'other']))
    price = fields.Float(required=True)
    effective_date = fields.Date(required=True)
    remark = fields.Str()
    create_time = fields.DateTime()


class StylePriceCreateSchema(Schema):
    price_type = fields.Str(required=True, validate=validate.OneOf(['customer', 'internal', 'outsourced', 'button', 'other']))
    price = fields.Float(required=True)
    effective_date = fields.Date(required=True)
    remark = fields.Str()
    