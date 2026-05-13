from datetime import datetime

from app.constants.identity import (
    PLATFORM_IDENTITY_ADMIN,
    PLATFORM_IDENTITY_EXTERNAL,
    PLATFORM_IDENTITY_STAFF,
    SUBJECT_TYPE_FACTORY,
    SUBJECT_TYPE_INDIVIDUAL,
    SUBJECT_TYPE_PARTNER,
    infer_subject_type,
    is_internal_platform_identity,
)
from app.extensions import db
from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = 'sys_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    password = db.Column(db.String(255), nullable=False, comment='密码')
    nickname = db.Column(db.String(50), comment='昵称')
    email = db.Column(db.String(100), comment='邮箱')
    phone = db.Column(db.String(20), comment='手机号')
    avatar = db.Column(db.String(255), comment='头像')
    openid = db.Column(db.String(100), comment='微信openid')
    platform_identity = db.Column(
        db.String(20),
        default=PLATFORM_IDENTITY_EXTERNAL,
        nullable=False,
        comment='平台身份：platform_admin/platform_staff/external_user'
    )
    status = db.Column(db.SmallInteger, default=1, comment='账号状态：1-正常，0-禁用')
    last_login_time = db.Column(db.DateTime, comment='最后登录时间')
    is_paid = db.Column(db.SmallInteger, default=0, comment='是否已付费：0-否，1-是')
    invite_code = db.Column(db.String(20), unique=True, comment='用户邀请码（唯一）')
    invited_by = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='邀请人用户ID')
    invited_count = db.Column(db.Integer, default=0, comment='成功邀请人数')
    created_by = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='创建人用户ID')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    inviter = db.relationship('User', remote_side=[id], foreign_keys=[invited_by], backref='invited_users')
    creator = db.relationship('User', remote_side=[id], foreign_keys=[created_by], backref='created_users')

    @property
    def platform_identity_label(self):
        """返回平台身份的中文显示名称。"""
        labels = {
            PLATFORM_IDENTITY_ADMIN: '平台管理员',
            PLATFORM_IDENTITY_STAFF: '平台员工',
            PLATFORM_IDENTITY_EXTERNAL: '外部人员',
        }
        return labels.get(self.platform_identity, self.platform_identity)

    @property
    def is_platform_admin(self):
        """判断用户是否拥有平台管理员能力。"""
        return self.platform_identity == PLATFORM_IDENTITY_ADMIN

    @property
    def is_platform_staff(self):
        """判断用户是否属于平台员工。"""
        return self.platform_identity == PLATFORM_IDENTITY_STAFF

    @property
    def is_internal_user(self):
        """判断用户是否属于平台内部账号。"""
        return is_internal_platform_identity(self.platform_identity)

    def get_subject_type(self, relation_types=None):
        """按当前关系上下文推导用户所属主体类型。"""
        return infer_subject_type(self.platform_identity, relation_types)

    def get_subject_type_label(self, relation_types=None):
        """返回主体类型的中文显示名称。"""
        labels = {
            SUBJECT_TYPE_INDIVIDUAL: '个人主体',
            SUBJECT_TYPE_FACTORY: '工厂主体',
            SUBJECT_TYPE_PARTNER: '协作主体',
        }
        subject_type = self.get_subject_type(relation_types)
        return labels.get(subject_type, subject_type)

    def to_dict(self):
        """导出用户数据，并追加身份字段且隐藏密码。"""
        data = super().to_dict()
        data['platform_identity_label'] = self.platform_identity_label
        data.pop('password', None)
        return data
