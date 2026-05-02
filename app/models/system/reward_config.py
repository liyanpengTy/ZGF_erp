"""奖励配置模型"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class RewardConfig(BaseModel):
    """奖励配置表"""
    __tablename__ = 'sys_reward_config'
    __table_args__ = (
        db.UniqueConstraint('rule_type', 'threshold', 'reward_object', 'is_deleted', name='uk_rule_type_threshold_object'),
        {'comment': '奖励配置表，支持动态配置奖励规则'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, comment='奖励名称')
    rule_type = db.Column(db.String(20), nullable=False, default='invite_count', comment='规则类型：invite_count-邀请人数')
    threshold = db.Column(db.Integer, nullable=False, comment='触发阈值（如邀请满5人）')
    reward_object = db.Column(db.String(20), nullable=False, comment='奖励对象：factory-工厂，personal-个人')
    reward_type = db.Column(db.String(20), nullable=False, comment='奖励类型：extend-工厂VIP延期，cash-个人现金')
    reward_value = db.Column(db.Numeric(10, 2), nullable=False, comment='奖励值（延期天数或现金金额）')
    is_active = db.Column(db.SmallInteger, default=1, comment='是否启用：1-启用，0-禁用')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rule_type': self.rule_type,
            'threshold': self.threshold,
            'reward_object': self.reward_object,
            'reward_object_label': '工厂' if self.reward_object == 'factory' else '个人',
            'reward_type': self.reward_type,
            'reward_type_label': '工厂VIP延期' if self.reward_type == 'extend' else '个人现金',
            'reward_value': float(self.reward_value) if self.reward_value else 0,
            'is_active': self.is_active,
            'remark': self.remark,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None
        }
