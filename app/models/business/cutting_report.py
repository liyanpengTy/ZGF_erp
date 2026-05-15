"""裁床报工模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class WorkCuttingReport(BaseModel):
    """裁床报工主表，记录某个订单 SKU 的实裁数量与生成床次。"""

    __tablename__ = 'prd_work_cutting_report'
    __table_args__ = (
        db.Index('idx_prd_work_cutting_report_factory_id', 'factory_id'),
        db.Index('idx_prd_work_cutting_report_order_id', 'order_id'),
        db.Index('idx_prd_work_cutting_report_sku_id', 'order_detail_sku_id'),
        db.Index('idx_prd_work_cutting_report_cut_batch_no', 'cut_batch_no'),
        {'comment': '裁床报工主表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    template_id = db.Column(db.Integer, db.ForeignKey('prd_bundle_template.id'), comment='本次生成菲所使用的模板ID')
    order_id = db.Column(db.Integer, db.ForeignKey('ord_order.id'), nullable=False, comment='订单ID')
    order_detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    order_detail_sku_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail_sku.id'), nullable=False, comment='订单SKU ID')
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    color_id = db.Column(db.Integer, db.ForeignKey('fab_color.id'), comment='颜色ID')
    size_id = db.Column(db.Integer, db.ForeignKey('sys_size.id'), comment='尺码ID')
    report_user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='报工人ID')
    cut_batch_no = db.Column(db.Integer, nullable=False, comment='床次')
    cut_date = db.Column(db.Date, nullable=False, comment='裁床日期')
    cut_quantity = db.Column(db.Integer, nullable=False, default=0, comment='实裁数量')
    bundle_count = db.Column(db.Integer, nullable=False, default=0, comment='生成菲数量')
    status = db.Column(db.String(20), nullable=False, default='active', comment='状态：active/cancelled')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='cutting_reports')
    template = db.relationship('BundleTemplate', backref='cutting_reports')
    order = db.relationship('Order', backref='cutting_reports')
    order_detail = db.relationship('OrderDetail', backref='cutting_reports')
    order_detail_sku = db.relationship('OrderDetailSku', backref='cutting_reports')
    style = db.relationship('Style', backref='cutting_reports')
    color = db.relationship('Color', backref='cutting_reports')
    size = db.relationship('Size', backref='cutting_reports')
    report_user = db.relationship('User', backref='cutting_reports')

    @property
    def status_label(self):
        """返回裁床报工状态中文名称。"""
        return {'active': '生效中', 'cancelled': '已撤销'}.get(self.status, self.status)
