"""主体间协作任务模型。"""

from datetime import datetime

from app.constants.identity import COLLABORATION_STATUS_PENDING
from app.extensions import db
from app.models.base import BaseModel


class CollaborationTask(BaseModel):
    """主体之间按工序派发和接收的协作任务。"""

    __tablename__ = 'collaboration_task'
    __table_args__ = (
        db.Index('idx_collaboration_task_from_subject', 'from_subject_id', 'status', 'is_deleted'),
        db.Index('idx_collaboration_task_to_subject', 'to_subject_id', 'status', 'is_deleted'),
        db.Index('idx_collaboration_task_source_order', 'source_order_id', 'is_deleted'),
        {'comment': '主体协作任务表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='协作任务ID')
    from_subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='发起主体ID')
    to_subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='接收主体ID')
    source_order_id = db.Column(db.Integer, db.ForeignKey('ord_order.id'), nullable=False, comment='原始订单/工单ID')
    process_name = db.Column(db.String(100), nullable=False, comment='协作工序名称')
    quantity = db.Column(db.Integer, nullable=False, default=0, comment='协作数量')
    deliver_at = db.Column(db.DateTime, comment='交付时间')
    status = db.Column(
        db.String(20),
        default=COLLABORATION_STATUS_PENDING,
        nullable=False,
        comment='状态：pending/accepted/in_progress/completed',
    )
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    create_by = db.Column(db.Integer, comment='创建人ID')
    update_by = db.Column(db.Integer, comment='更新人ID')

    from_subject = db.relationship('Factory', foreign_keys=[from_subject_id], backref='outbound_collaboration_tasks')
    to_subject = db.relationship('Factory', foreign_keys=[to_subject_id], backref='inbound_collaboration_tasks')
    source_order = db.relationship('Order', backref='collaboration_tasks')

    def to_safe_dict(self):
        """返回接收主体可见的协作任务数据，不暴露成本和利润信息。"""
        return {
            'id': self.id,
            'from_subject_id': self.from_subject_id,
            'to_subject_id': self.to_subject_id,
            'source_order_id': self.source_order_id,
            'process_name': self.process_name,
            'quantity': self.quantity,
            'deliver_at': self.deliver_at.isoformat() if self.deliver_at else None,
            'status': self.status,
            'remark': self.remark,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }
