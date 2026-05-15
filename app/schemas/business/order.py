"""订单相关序列化器。"""

from marshmallow import Schema, fields, validate


class OrderDetailSkuSchema(Schema):
    """订单明细 SKU 序列化器。"""

    id = fields.Int()
    detail_id = fields.Int()
    splice_config = fields.Dict(required=True)
    remark = fields.Str()


class OrderDetailSkuCreateSchema(Schema):
    """创建订单明细 SKU 参数。"""

    splice_config = fields.Dict(required=True)
    remark = fields.Str()


class OrderDetailSkuUpdateSchema(Schema):
    """更新订单明细 SKU 参数。"""

    splice_config = fields.Dict()
    remark = fields.Str()


class OrderDetailSchema(Schema):
    """订单明细序列化器。"""

    id = fields.Int()
    order_id = fields.Int()
    style_id = fields.Int()
    style_no = fields.Str()
    style_name = fields.Str()
    snapshot_splice_data = fields.List(fields.Dict())
    snapshot_custom_attributes = fields.Dict()
    remark = fields.Str()
    skus = fields.List(fields.Nested(OrderDetailSkuSchema))


class OrderDetailCreateSchema(Schema):
    """创建订单明细参数。"""

    style_id = fields.Int(required=True)
    remark = fields.Str()
    skus = fields.List(fields.Nested(OrderDetailSkuCreateSchema), required=True)


class OrderSchema(Schema):
    """订单序列化器。"""

    id = fields.Int()
    order_no = fields.Str()
    factory_id = fields.Int()
    customer_id = fields.Int()
    customer_name = fields.Str()
    order_date = fields.DateTime(format='%Y-%m-%d')
    delivery_date = fields.DateTime(format='%Y-%m-%d')
    status = fields.Str()
    status_label = fields.Str()
    total_amount = fields.Float()
    remark = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    details = fields.List(fields.Nested(OrderDetailSchema))


class OrderCreateSchema(Schema):
    """创建订单参数。"""

    customer_id = fields.Int()
    customer_name = fields.Str(validate=validate.Length(max=100))
    order_date = fields.Str(required=True, validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    delivery_date = fields.Str(validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str(validate=validate.Length(max=500))
    details = fields.List(fields.Nested(OrderDetailCreateSchema), required=True)


class OrderUpdateSchema(Schema):
    """更新订单参数。"""

    customer_id = fields.Int()
    customer_name = fields.Str(validate=validate.Length(max=100))
    delivery_date = fields.Str(validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    remark = fields.Str(validate=validate.Length(max=500))


class OrderStatusUpdateSchema(Schema):
    """更新订单状态参数。"""

    status = fields.Str(required=True, validate=validate.OneOf(['pending', 'confirmed', 'processing', 'completed', 'cancelled']))
