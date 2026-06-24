"""系统角色模板、主体本地角色和主体用户授权模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel

subject_role_menu = db.Table(
    'subject_role_menu',
    db.Column('subject_role_id', db.Integer, db.ForeignKey('subject_role.id'), primary_key=True, comment='主体角色ID'),
    db.Column('menu_id', db.Integer, db.ForeignKey('sys_menu.id'), primary_key=True, comment='菜单或按钮权限ID'),
    comment='主体角色菜单权限关联表',
)


class SystemRoleTemplate(BaseModel):
    """平台预定义角色模板，用于实例化主体本地角色。"""

    __tablename__ = 'system_role_template'
    __table_args__ = (
        db.UniqueConstraint('code', 'is_deleted', name='uk_system_role_template_code'),
        {'comment': '系统角色模板表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='模板ID')
    name = db.Column(db.String(50), nullable=False, comment='模板名称')
    code = db.Column(db.String(50), nullable=False, comment='模板编码')
    role_type = db.Column(db.String(20), nullable=False, comment='角色类型：internal/external/mixed')
    description = db.Column(db.String(255), comment='模板说明')
    data_scope = db.Column(db.String(20), default='subject', nullable=False, comment='默认数据范围')
    is_admin = db.Column(db.SmallInteger, default=0, comment='是否管理员模板：1-是，0-否')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class SubjectRole(BaseModel):
    """主体本地角色实例，可在系统模板基础上自定义名称。"""

    __tablename__ = 'subject_role'
    __table_args__ = (
        db.UniqueConstraint('subject_id', 'code', 'is_deleted', name='uk_subject_role_subject_code'),
        db.Index('idx_subject_role_subject_status', 'subject_id', 'status', 'is_deleted'),
        {'comment': '主体本地角色表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主体角色ID')
    subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='主体ID')
    template_id = db.Column(db.Integer, db.ForeignKey('system_role_template.id'), comment='系统角色模板ID')
    name = db.Column(db.String(50), nullable=False, comment='角色名称，可由主体自定义')
    code = db.Column(db.String(50), nullable=False, comment='角色编码')
    description = db.Column(db.String(255), comment='角色说明')
    data_scope = db.Column(db.String(20), default='subject', nullable=False, comment='数据范围')
    is_admin = db.Column(db.SmallInteger, default=0, comment='是否主体管理员：1-是，0-否')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    subject = db.relationship('Factory', backref='subject_roles')
    template = db.relationship('SystemRoleTemplate', backref='subject_roles')
    menus = db.relationship('Menu', secondary=subject_role_menu, backref='subject_roles')


class SubjectUserRole(BaseModel):
    """主体用户授权表，表达用户、主体和主体角色的绑定关系。"""

    __tablename__ = 'subject_user_role'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'subject_id', 'subject_role_id', 'is_deleted', name='uk_subject_user_role'),
        db.Index('idx_subject_user_role_user_subject', 'user_id', 'subject_id', 'is_deleted'),
        db.Index('idx_subject_user_role_subject_role', 'subject_id', 'subject_role_id', 'is_deleted'),
        {'comment': '主体用户角色授权表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='授权ID')
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='用户ID')
    subject_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='主体ID')
    subject_role_id = db.Column(db.Integer, db.ForeignKey('subject_role.id'), nullable=False, comment='主体角色ID')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    user = db.relationship('User', backref='subject_user_roles')
    subject = db.relationship('Factory', backref='subject_user_roles')
    subject_role = db.relationship('SubjectRole', backref='subject_user_roles')
