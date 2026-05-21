"""用户角色分配模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class UserFactoryRole(BaseModel):
    """用户角色分配表，记录用户在平台或某个工厂上下文中的角色。"""

    __tablename__ = 'sys_user_factory_role'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'factory_id', 'role_id', name='uk_user_factory_role'),
        {'comment': '用户角色分配表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='用户角色分配ID')
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='用户ID')
    factory_id = db.Column(
        db.Integer,
        nullable=False,
        comment='角色分配上下文ID：平台角色为0，工厂角色为工厂ID'
    )
    role_id = db.Column(db.Integer, db.ForeignKey('sys_role.id'), nullable=False, comment='角色ID')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')

    user = db.relationship('User', backref='user_factory_roles')
    role = db.relationship('Role', backref='user_factory_roles')
