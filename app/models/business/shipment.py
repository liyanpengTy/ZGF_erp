"""出货单业务模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class Shipment(BaseModel):
    """出货单主表，记录订单级出货单头信息。"""

    __tablename__ = 'shp_shipment'
    __table_args__ = (
        db.Index('idx_shp_shipment_shipment_no', 'shipment_no'),
        db.Index('idx_shp_shipment_factory_id', 'factory_id'),
        db.Index('idx_shp_shipment_order_id', 'order_id'),
        db.Index('idx_shp_shipment_ship_date', 'ship_date'),
        db.Index('idx_shp_shipment_status', 'status'),
        {'comment': '出货单主表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shipment_no = db.Column(db.String(50), unique=True, nullable=False, comment='出货单号')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    order_id = db.Column(db.Integer, db.ForeignKey('ord_order.id'), nullable=False, comment='订单ID')
    customer_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='客户ID')
    customer_name = db.Column(db.String(100), comment='客户名称快照')
    ship_date = db.Column(db.Date, nullable=False, comment='出货日期')
    status = db.Column(db.String(20), nullable=False, default='created', comment='状态：created/cancelled')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    create_by = db.Column(db.Integer, comment='创建人ID')
    update_by = db.Column(db.Integer, comment='更新人ID')

    factory = db.relationship('Factory', backref='shipments')
    order = db.relationship('Order', backref='shipments')
    customer = db.relationship('User', backref='shipment_orders')
    items = db.relationship('ShipmentItem', backref='shipment', cascade='all, delete-orphan')

    @property
    def status_label(self):
        """返回出货单状态中文名称。"""
        return {
            'created': '已出货',
            'cancelled': '已作废',
        }.get(self.status, self.status)

    @property
    def total_quantity(self):
        """返回出货单总数量。"""
        return sum((item.quantity or 0) for item in self.items if item.is_deleted == 0)

    @property
    def item_count(self):
        """返回出货单明细行数。"""
        return len([item for item in self.items if item.is_deleted == 0])

    @property
    def order_no(self):
        """返回关联订单号。"""
        return self.order.order_no if self.order else None


class ShipmentItem(BaseModel):
    """出货单明细表，记录某个订单 SKU 的出货数量。"""

    __tablename__ = 'shp_shipment_item'
    __table_args__ = (
        db.Index('idx_shp_shipment_item_shipment_id', 'shipment_id'),
        db.Index('idx_shp_shipment_item_order_detail_id', 'order_detail_id'),
        db.Index('idx_shp_shipment_item_order_detail_sku_id', 'order_detail_sku_id'),
        {'comment': '出货单明细表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey('shp_shipment.id'), nullable=False, comment='出货单ID')
    order_detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    order_detail_sku_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail_sku.id'), nullable=False, comment='订单SKU ID')
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    color_id = db.Column(db.Integer, db.ForeignKey('fab_color.id'), comment='颜色ID')
    size_id = db.Column(db.Integer, db.ForeignKey('sys_size.id'), comment='尺码ID')
    quantity = db.Column(db.Integer, nullable=False, default=0, comment='出货数量')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    detail = db.relationship('OrderDetail', backref='shipment_items')
    sku = db.relationship('OrderDetailSku', backref='shipment_items')
    style = db.relationship('Style', backref='shipment_items')
    color = db.relationship('Color', backref='shipment_items')
    size = db.relationship('Size', backref='shipment_items')
