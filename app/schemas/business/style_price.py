"""款号价格相关序列化定义。"""

from marshmallow import Schema, fields, validate


PRICE_TYPE_CHOICES = ['customer', 'internal', 'outsourced', 'button', 'other']


class StylePriceSchema(Schema):
    """款号价格返回结构。"""

    id = fields.Int()
    style_id = fields.Int(required=True, validate=validate.Range(min=1))
    price_type = fields.Str(required=True, validate=validate.OneOf(PRICE_TYPE_CHOICES))
    price = fields.Float(required=True, validate=validate.Range(min=0))
    effective_date = fields.Date(required=True)
    remark = fields.Str(validate=validate.Length(max=500))
    create_time = fields.DateTime()


class StylePriceCreateSchema(Schema):
    """创建款号价格请求结构。"""

    style_id = fields.Int(required=True, validate=validate.Range(min=1))
    price_type = fields.Str(required=True, validate=validate.OneOf(PRICE_TYPE_CHOICES))
    price = fields.Float(required=True, validate=validate.Range(min=0))
    effective_date = fields.Date(required=True)
    remark = fields.Str(validate=validate.Length(max=500))
