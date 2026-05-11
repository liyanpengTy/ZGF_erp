"""奖励记录模型"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class RewardRecord(BaseModel):
    """奖励记录表"""
    __tablename__ = 'sys_reward_record'
    __table_args__ = (
        db.Index('idx_sys_reward_record_user_id', 'user_id'),
        db.Index('idx_sys_reward_record_factory_id', 'factory_id'),
        db.Index('idx_sys_reward_record_reward_object', 'reward_object'),
        db.Index('idx_sys_reward_record_status', 'status'),
        {'comment': '奖励记录表'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # 奖励对象信息
    reward_object = db.Column(db.String(20), nullable=False, comment='奖励对象：factory-工厂，personal-个人')
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='用户ID（关联触发人）')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), comment='工厂ID（奖励工厂时必填）')

    reward_config_id = db.Column(db.Integer, db.ForeignKey('sys_reward_config.id'), comment='奖励配置ID')
    reward_type = db.Column(db.String(20), nullable=False, comment='奖励类型：extend-工厂VIP延期，cash-个人现金')
    reward_value = db.Column(db.Numeric(10, 2), nullable=False, comment='奖励值')

    # 触发信息
    trigger_condition = db.Column(db.String(100), comment='触发条件')
    trigger_value = db.Column(db.Integer, comment='触发时的数值')

    # 状态
    status = db.Column(db.String(20), default='pending', comment='状态：pending-待发放，distributed-已发放，cancelled-已取消')

    # 发放信息
    distributed_by = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='发放人ID')
    distributed_time = db.Column(db.DateTime, comment='发放时间')
    remark = db.Column(db.String(255), comment='备注')

    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联关系
    user = db.relationship('User', foreign_keys=[user_id], backref='reward_records')
    factory = db.relationship('Factory', foreign_keys=[factory_id], backref='reward_records')
    reward_config = db.relationship('RewardConfig', foreign_keys=[reward_config_id], backref='reward_records')
    distributor = db.relationship('User', foreign_keys=[distributed_by], backref='distributed_rewards')

    def to_dict(self):
        return {
            'id': self.id,
            'reward_object': self.reward_object,
            'reward_object_label': '工厂' if self.reward_object == 'factory' else '个人',
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'factory_id': self.factory_id,
            'factory_name': self.factory.name if self.factory else None,
            'reward_config_name': self.reward_config.name if self.reward_config else None,
            'reward_type': self.reward_type,
            'reward_type_label': '工厂VIP延期' if self.reward_type == 'extend' else '个人现金',
            'reward_value': float(self.reward_value) if self.reward_value else 0,
            'trigger_condition': self.trigger_condition,
            'trigger_value': self.trigger_value,
            'status': self.status,
            'status_label': '待发放' if self.status == 'pending' else ('已发放' if self.status == 'distributed' else '已取消'),
            'distributor_name': self.distributor.username if self.distributor else None,
            'distributed_time': self.distributed_time.isoformat() if self.distributed_time else None,
            'remark': self.remark,
            'create_time': self.create_time.isoformat() if self.create_time else None
        }
