"""出货单相关序列化器。"""

from marshmallow import Schema, fields, validate


class ShipmentItemSchema(Schema):
    """出货单明细序列化器。"""

    id = fields.Int()
    shipment_id = fields.Int()
    order_detail_id = fields.Int()
    order_detail_sku_id = fields.Int()
    style_id = fields.Int()
    style_no = fields.Method('get_style_no')
    style_name = fields.Method('get_style_name')
    color_id = fields.Int(allow_none=True)
    color_name = fields.Method('get_color_name')
    size_id = fields.Int(allow_none=True)
    size_name = fields.Method('get_size_name')
    quantity = fields.Int()
    remark = fields.Str(allow_none=True)

    def get_style_no(self, obj):
        """返回款号。"""
        return obj.style.style_no if obj.style else None

    def get_style_name(self, obj):
        """返回款号名称。"""
        return obj.style.name if obj.style else None

    def get_color_name(self, obj):
        """返回颜色名称。"""
        return obj.color.name if obj.color else None

    def get_size_name(self, obj):
        """返回尺码名称。"""
        return obj.size.name if obj.size else None


class ShipmentSchema(Schema):
    """出货单序列化器。"""

    id = fields.Int()
    shipment_no = fields.Str()
    factory_id = fields.Int()
    order_id = fields.Int()
    order_no = fields.Str()
    customer_id = fields.Int(allow_none=True)
    customer_name = fields.Str(allow_none=True)
    ship_date = fields.DateTime(format='%Y-%m-%d')
    status = fields.Str()
    status_label = fields.Str()
    total_quantity = fields.Int()
    item_count = fields.Int()
    remark = fields.Str(allow_none=True)
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    items = fields.List(fields.Nested(ShipmentItemSchema))


class ShipmentItemCreateSchema(Schema):
    """创建出货单明细参数。"""

    order_detail_sku_id = fields.Int(required=True)
    quantity = fields.Int(required=True)
    remark = fields.Str(validate=validate.Length(max=500))


class ShipmentCreateSchema(Schema):
    """创建出货单参数。"""

    order_id = fields.Int(required=True)
    ship_date = fields.Str(required=True, validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str(validate=validate.Length(max=500))
    items = fields.List(fields.Nested(ShipmentItemCreateSchema), required=True, validate=validate.Length(min=1))


class ShipmentCancelSchema(Schema):
    """作废出货单参数。"""

    remark = fields.Str(validate=validate.Length(max=500))
