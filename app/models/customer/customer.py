"""客户账号、客户主体关联和客户邀请码模型。"""

from datetime import datetime

from app.constants.identity import (
    CUSTOMER_INVITE_STATUS_ACTIVE,
    CUSTOMER_RELATION_STATUS_ACTIVE,
    CUSTOMER_TIER_FREE,
)
from app.extensions import db
from app.models.base import BaseModel


class CustomerUser(BaseModel):
    """客户账号表，用于客户侧订单查看和下单。"""

    __tablename__ = 'customer_user'
    __table_args__ = (
        db.Index('idx_customer_user_phone_deleted', 'phone', 'is_deleted'),
        {'comment': '客户用户表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='客户ID')
    phone = db.Column(db.String(20), unique=True, nullable=False, comment='手机号')
    name = db.Column(db.String(50), nullable=False, comment='客户名称')
    password = db.Column(db.String(255), nullable=False, comment='加密密码')
    status = db.Column(db.String(20), default='active', nullable=False, comment='状态：active/disabled')
    tier = db.Column(db.String(20), default=CUSTOMER_TIER_FREE, nullable=False, comment='客户等级：free/pro/enterprise')
    quota_limit = db.Column(db.Integer, comment='订单数量上限，空表示不限制')
    extra_functions = db.Column(db.JSON, comment='预留功能开关')
    created_by_subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), comment='代注册主体ID')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    created_by_subject = db.relationship('Factory', foreign_keys=[created_by_subject_id], backref='created_customers')

    def to_dict(self):
        data = super().to_dict()
        data.pop('password', None)
        return data


class CustomerSubjectRelation(BaseModel):
    """客户与主体关联表，不进入主体角色权限体系。"""

    __tablename__ = 'customer_subject_relation'
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'subject_id', name='uk_customer_subject_relation'),
        db.Index('idx_customer_subject_relation_customer_status', 'customer_id', 'status', 'is_deleted'),
        db.Index('idx_customer_subject_relation_subject_status', 'subject_id', 'status', 'is_deleted'),
        {'comment': '客户-主体关联表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='关联ID')
    customer_id = db.Column(db.Integer, db.ForeignKey('customer_user.id'), nullable=False, comment='客户ID')
    subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='主体ID')
    status = db.Column(db.String(20), default=CUSTOMER_RELATION_STATUS_ACTIVE, nullable=False, comment='状态：active/inactive')
    created_via = db.Column(db.String(20), nullable=False, comment='创建方式：qrcode/admin')
    created_by = db.Column(db.Integer, comment='创建方ID：主体ID或客户ID')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    customer = db.relationship('CustomerUser', backref='subject_relations')
    subject = db.relationship('Factory', backref='customer_relations')

    @property
    def is_active(self):
        return self.status == CUSTOMER_RELATION_STATUS_ACTIVE and self.is_deleted == 0


class CustomerInviteCode(BaseModel):
    """主体生成的可复用客户绑定邀请码。"""

    __tablename__ = 'customer_invite_code'
    __table_args__ = (
        db.Index('idx_customer_invite_code_subject_status', 'subject_id', 'status', 'is_deleted'),
        {'comment': '客户邀请二维码邀请码表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='邀请码ID')
    subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='生成主体ID')
    code = db.Column(db.String(64), unique=True, nullable=False, comment='唯一邀请码')
    expire_type = db.Column(db.String(20), nullable=False, comment='有效期类型：week/month/year')
    expire_at = db.Column(db.DateTime, nullable=False, comment='具体过期时间')
    status = db.Column(db.String(20), default=CUSTOMER_INVITE_STATUS_ACTIVE, nullable=False, comment='状态：active/expired')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    subject = db.relationship('Factory', backref='customer_invite_codes')

    def is_available(self, now=None):
        now = now or datetime.now()
        return self.status == CUSTOMER_INVITE_STATUS_ACTIVE and self.is_deleted == 0 and self.expire_at >= now
