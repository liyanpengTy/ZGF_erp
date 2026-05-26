"""款号价格相关序列化定义。"""

from marshmallow import Schema, fields, validate


class StylePriceSchema(Schema):
    """款号价格返回结构。"""

    id = fields.Int()
    style_id = fields.Int(required=True)
    price_type = fields.Str(required=True, validate=validate.OneOf(['customer', 'internal', 'outsourced', 'button', 'other']))
    price = fields.Float(required=True)
    effective_date = fields.Date(required=True)
    remark = fields.Str()
    create_time = fields.DateTime()


class StylePriceCreateSchema(Schema):
    """创建款号价格请求结构。"""

    price_type = fields.Str(required=True, validate=validate.OneOf(['customer', 'internal', 'outsourced', 'button', 'other']))
    price = fields.Float(required=True)
    effective_date = fields.Date(required=True)
    remark = fields.Str()
