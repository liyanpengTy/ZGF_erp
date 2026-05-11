"""工序管理模型"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Process(BaseModel):
    """工序定义表（系统级基础数据）"""
    __tablename__ = 'pro_process'
    __table_args__ = (
        {'comment': '工序定义表'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, comment='工序名称，如：裁剪、缝制、整烫')
    code = db.Column(db.String(50), unique=True, nullable=False, comment='工序编码')
    description = db.Column(db.String(255), comment='工序描述')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'sort_order': self.sort_order,
            'status': self.status,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None
        }


class StyleProcessMapping(BaseModel):
    """款号工序关联表（每个款号对应的工序流程）"""
    __tablename__ = 'pro_style_process'
    __table_args__ = (
        db.UniqueConstraint('style_id', 'process_id', name='uk_style_process'),
        db.Index('idx_pro_style_process_style_id', 'style_id'),
        {'comment': '款号工序关联表'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    process_id = db.Column(db.Integer, db.ForeignKey('pro_process.id'), nullable=False, comment='工序ID')
    sequence = db.Column(db.Integer, default=1, comment='工序顺序（第几道工序）')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联关系
    style = db.relationship('Style', backref='style_process_mappings', foreign_keys=[style_id])
    process = db.relationship('Process', backref='style_process_mappings', foreign_keys=[process_id])

    def to_dict(self):
        return {
            'id': self.id,
            'style_id': self.style_id,
            'process_id': self.process_id,
            'process_name': self.process.name if self.process else None,
            'process_code': self.process.code if self.process else None,
            'sequence': self.sequence,
            'remark': self.remark
        }
    
