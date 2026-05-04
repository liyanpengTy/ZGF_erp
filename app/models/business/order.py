"""订单管理模型"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Order(BaseModel):
    """订单主表"""
    __tablename__ = 'ord_order'
    __table_args__ = (
        db.Index('idx_order_no', 'order_no'),
        db.Index('idx_factory_id', 'factory_id'),
        db.Index('idx_status', 'status'),
        db.Index('idx_order_date', 'order_date'),
        {'comment': '订单主表'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False, comment='订单号')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    customer_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='客户ID')
    customer_name = db.Column(db.String(100), comment='客户名称')
    order_date = db.Column(db.Date, nullable=False, comment='订单日期')
    delivery_date = db.Column(db.Date, comment='交货日期')
    status = db.Column(db.String(20), default='pending', comment='订单状态')
    total_amount = db.Column(db.Numeric(12, 2), default=0, comment='订单总金额')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    create_by = db.Column(db.Integer, comment='创建人ID')
    update_by = db.Column(db.Integer, comment='更新人ID')

    # 关联关系
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
            'update_time': self.update_time.isoformat() if self.update_time else None
        }

    def get_status_label(self):
        status_map = {
            'pending': '待确认',
            'confirmed': '已确认',
            'processing': '生产中',
            'completed': '已完成',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)


class OrderDetail(BaseModel):
    """订单明细主表（款号级）"""
    __tablename__ = 'ord_order_detail'
    __table_args__ = (
        db.Index('idx_order_id', 'order_id'),
        db.Index('idx_style_id', 'style_id'),
        {'comment': '订单明细主表，存储款号级信息'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('ord_order.id'), nullable=False, comment='订单ID')
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    # 快照（从款号表复制，防止款号修改后订单变化）
    snapshot_splice_data = db.Column(db.JSON, comment='下单时款号的拼接结构')
    snapshot_custom_attributes = db.Column(db.JSON, comment='下单时款号的自定义属性')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    # 关联关系
    order = db.relationship('Order', backref='details')
    style = db.relationship('Style', backref='order_details')
    skus = db.relationship('OrderDetailSku', backref='detail', cascade='all, delete-orphan')

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
            'skus': [sku.to_dict() for sku in self.skus]
        }


class OrderDetailSku(BaseModel):
    """订单明细SKU表（颜色尺码级）"""
    __tablename__ = 'ord_order_detail_sku'
    __table_args__ = (
        db.Index('idx_detail_id', 'detail_id'),
        db.Index('idx_color_id', 'color_id'),
        db.Index('idx_size_id', 'size_id'),
        {'comment': '订单明细SKU表，存储每个颜色尺码的数量和拼接配置'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    color_id = db.Column(db.Integer, db.ForeignKey('fab_color.id'), comment='颜色ID')
    size_id = db.Column(db.Integer, db.ForeignKey('sys_size.id'), comment='尺码ID')
    quantity = db.Column(db.Integer, nullable=False, comment='数量')
    # 价格快照（下单时的单价和金额）
    unit_price = db.Column(db.Numeric(10, 2), default=0, comment='下单时单价')
    amount = db.Column(db.Numeric(12, 2), default=0, comment='小计金额')
    splice_config = db.Column(db.JSON, comment='拼接配置')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    # 关联关系
    detail = db.relationship('OrderDetail', backref='detail_skus')
    color = db.relationship('Color', backref='order_detail_skus')
    size = db.relationship('Size', backref='order_detail_skus')

    def to_dict(self):
        return {
            'id': self.id,
            'detail_id': self.detail_id,
            'color_id': self.color_id,
            'color_name': self.color.name if self.color else None,
            'size_id': self.size_id,
            'size_name': self.size.name if self.size else None,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'amount': float(self.amount) if self.amount else 0,
            'splice_config': self.splice_config,
            'remark': self.remark
        }
