"""员工计酬配置模型"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class EmployeeWage(BaseModel):
    """员工计酬配置表"""
    __tablename__ = 'sys_employee_wage'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'process_id', 'effective_date', name='uk_user_process_date'),
        db.Index('idx_user_id', 'user_id'),
        db.Index('idx_process_id', 'process_id'),
        db.Index('idx_effective_date', 'effective_date'),
        {'comment': '员工计酬配置表，支持不同工序不同计酬方式'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='员工ID')
    process_id = db.Column(db.Integer, db.ForeignKey('pro_process.id'), nullable=False, comment='工序ID')
    wage_type = db.Column(db.String(20), nullable=False,
                          comment='计酬方式：monthly-月薪，piece-计件，base_piece-底薪+计件，hourly-计时')
    monthly_salary = db.Column(db.Numeric(10, 2), default=0, comment='月薪金额（元/月）')
    piece_rate = db.Column(db.Numeric(10, 2), default=0, comment='计件单价（元/件）')
    base_salary = db.Column(db.Numeric(10, 2), default=0, comment='底薪（元/月）')
    base_piece_rate = db.Column(db.Numeric(10, 2), default=0, comment='计件单价（元/件）')
    hourly_rate = db.Column(db.Numeric(10, 2), default=0, comment='计时单价（元/小时）')
    effective_date = db.Column(db.Date, nullable=False, comment='生效日期')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联关系
    user = db.relationship('User', backref='wage_configs', foreign_keys=[user_id])
    process = db.relationship('Process', backref='wage_configs', foreign_keys=[process_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'nickname': self.user.nickname if self.user else None,
            'process_id': self.process_id,
            'process_name': self.process.name if self.process else None,
            'wage_type': self.wage_type,
            'wage_type_label': self.get_wage_type_label(),
            'monthly_salary': float(self.monthly_salary) if self.monthly_salary else 0,
            'piece_rate': float(self.piece_rate) if self.piece_rate else 0,
            'base_salary': float(self.base_salary) if self.base_salary else 0,
            'base_piece_rate': float(self.base_piece_rate) if self.base_piece_rate else 0,
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else 0,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'remark': self.remark,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }

    def get_wage_type_label(self):
        labels = {
            'monthly': '月薪制',
            'piece': '计件制',
            'base_piece': '底薪+计件',
            'hourly': '计时制'
        }
        return labels.get(self.wage_type, self.wage_type)
