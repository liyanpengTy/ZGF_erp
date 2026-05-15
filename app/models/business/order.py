"""订单业务模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel
from app.models.business.value_codec import decode_dynamic_value


class Order(BaseModel):
    """订单主表。"""

    __tablename__ = 'ord_order'
    __table_args__ = (
        db.Index('idx_ord_order_order_no', 'order_no'),
        db.Index('idx_ord_order_factory_id', 'factory_id'),
        db.Index('idx_ord_order_status', 'status'),
        db.Index('idx_ord_order_order_date', 'order_date'),
        {'comment': '订单主表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False, comment='订单号')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    customer_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='客户ID')
    customer_name = db.Column(db.String(100), comment='客户名称')
    order_date = db.Column(db.Date, nullable=False, comment='订单日期')
    delivery_date = db.Column(db.Date, comment='交付日期')
    status = db.Column(db.String(20), default='pending', comment='订单状态')
    total_amount = db.Column(db.Numeric(12, 2), default=0, comment='订单总金额')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    create_by = db.Column(db.Integer, comment='创建人ID')
    update_by = db.Column(db.Integer, comment='更新人ID')

    factory = db.relationship('Factory', backref='orders')
    customer = db.relationship('User', backref='orders')
    details = db.relationship('OrderDetail', backref='order', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'factory_id': self.factory_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'status': self.status,
            'status_label': self.get_status_label(),
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'remark': self.remark,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }

    def get_status_label(self):
        """返回订单状态中文标签。"""
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'processing': '生产中',
            'completed': '已完成',
            'cancelled': '已取消',
        }
        return status_map.get(self.status, self.status)


class OrderDetail(BaseModel):
    """订单明细主表，存储款号级别信息。"""

    __tablename__ = 'ord_order_detail'
    __table_args__ = (
        db.Index('idx_ord_order_detail_order_id', 'order_id'),
        db.Index('idx_ord_order_detail_style_id', 'style_id'),
        {'comment': '订单明细主表，存储款号级别信息'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('ord_order.id'), nullable=False, comment='订单ID')
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    style = db.relationship('Style', backref='order_details')
    skus = db.relationship('OrderDetailSku', backref='detail', cascade='all, delete-orphan')
    snapshot_splice_items = db.relationship('OrderDetailSpliceSnapshot', backref='detail', cascade='all, delete-orphan')
    snapshot_attribute_items = db.relationship('OrderDetailAttributeSnapshot', backref='detail', cascade='all, delete-orphan')

    @property
    def snapshot_splice_data(self):
        """返回下单时款号拼接结构快照。"""
        return [
            {'sequence': item.sequence, 'description': item.description}
            for item in sorted(self.snapshot_splice_items, key=lambda current: (current.sequence, current.id or 0))
        ]

    @property
    def snapshot_custom_attributes(self):
        """返回下单时款号自定义属性快照。"""
        return {
            item.attr_key: decode_dynamic_value(item.value_type, item.attr_value)
            for item in sorted(self.snapshot_attribute_items, key=lambda current: (current.sort_order, current.id or 0))
        }

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'style_id': self.style_id,
            'style_no': self.style.style_no if self.style else None,
            'style_name': self.style.name if self.style else None,
            'snapshot_splice_data': self.snapshot_splice_data,
            'snapshot_custom_attributes': self.snapshot_custom_attributes,
            'remark': self.remark,
            'skus': [sku.to_dict() for sku in self.skus],
        }


class OrderDetailSpliceSnapshot(BaseModel):
    """订单明细拼接结构快照表。"""

    __tablename__ = 'ord_order_detail_splice_snapshot'
    __table_args__ = (
        db.Index('idx_ord_order_detail_splice_snapshot_detail_id', 'detail_id'),
        {'comment': '订单明细拼接结构快照表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    sequence = db.Column(db.Integer, nullable=False, comment='顺序')
    description = db.Column(db.String(255), nullable=False, comment='拼接描述')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class OrderDetailAttributeSnapshot(BaseModel):
    """订单明细自定义属性快照表。"""

    __tablename__ = 'ord_order_detail_attribute_snapshot'
    __table_args__ = (
        db.Index('idx_ord_order_detail_attribute_snapshot_detail_id', 'detail_id'),
        {'comment': '订单明细自定义属性快照表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    attr_key = db.Column(db.String(100), nullable=False, comment='属性名')
    attr_value = db.Column(db.String(500), nullable=False, default='', comment='属性值')
    value_type = db.Column(db.String(20), nullable=False, default='str', comment='属性值类型')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class OrderDetailSku(BaseModel):
    """订单明细 SKU 表。"""

    __tablename__ = 'ord_order_detail_sku'
    __table_args__ = (
        db.Index('idx_ord_order_detail_sku_detail_id', 'detail_id'),
        db.Index('idx_ord_order_detail_sku_color_id', 'color_id'),
        db.Index('idx_ord_order_detail_sku_size_id', 'size_id'),
        {'comment': '订单明细SKU表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    color_id = db.Column(db.Integer, db.ForeignKey('fab_color.id'), comment='颜色ID')
    size_id = db.Column(db.Integer, db.ForeignKey('sys_size.id'), comment='尺码ID')
    quantity = db.Column(db.Integer, nullable=False, default=1, comment='数量')
    unit_price = db.Column(db.Numeric(10, 2), default=0, comment='单价')
    priority = db.Column(db.Integer, default=0, comment='优先级')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    color = db.relationship('Color', backref='order_skus')
    size = db.relationship('Size', backref='order_skus')
    splice_items = db.relationship('OrderDetailSkuSpliceItem', backref='sku', cascade='all, delete-orphan')
    attribute_items = db.relationship('OrderDetailSkuAttribute', backref='sku', cascade='all, delete-orphan')

    @property
    def splice_config(self):
        """返回兼容接口层的 SKU 配置对象。"""
        data = {
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price is not None else 0,
            'priority': self.priority,
        }
        if self.color_id:
            data['color_id'] = self.color_id
            data['color_name'] = self.color.name if self.color else None
        if self.size_id:
            data['size_id'] = self.size_id
            data['size_name'] = self.size.name if self.size else None

        for item in sorted(self.attribute_items, key=lambda current: (current.sort_order, current.id or 0)):
            data[item.attr_key] = decode_dynamic_value(item.value_type, item.attr_value)

        if self.splice_items:
            data['splice_data'] = [
                {'sequence': item.sequence, 'description': item.description}
                for item in sorted(self.splice_items, key=lambda current: (current.sequence, current.id or 0))
            ]
        return data

    def to_dict(self):
        return {
            'id': self.id,
            'detail_id': self.detail_id,
            'splice_config': self.splice_config,
            'remark': self.remark,
        }


class OrderDetailSkuSpliceItem(BaseModel):
    """订单明细 SKU 拼接结构表。"""

    __tablename__ = 'ord_order_detail_sku_splice_item'
    __table_args__ = (
        db.Index('idx_ord_order_detail_sku_splice_item_sku_id', 'sku_id'),
        {'comment': '订单明细SKU拼接结构表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail_sku.id'), nullable=False, comment='订单明细SKU ID')
    sequence = db.Column(db.Integer, nullable=False, comment='顺序')
    description = db.Column(db.String(255), nullable=False, comment='拼接描述')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class OrderDetailSkuAttribute(BaseModel):
    """订单明细 SKU 附加属性表。"""

    __tablename__ = 'ord_order_detail_sku_attribute'
    __table_args__ = (
        db.Index('idx_ord_order_detail_sku_attribute_sku_id', 'sku_id'),
        {'comment': '订单明细SKU附加属性表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail_sku.id'), nullable=False, comment='订单明细SKU ID')
    attr_key = db.Column(db.String(100), nullable=False, comment='属性名')
    attr_value = db.Column(db.String(500), nullable=False, default='', comment='属性值')
    value_type = db.Column(db.String(20), nullable=False, default='str', comment='属性值类型')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
