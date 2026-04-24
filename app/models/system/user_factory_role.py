from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class UserFactoryRole(BaseModel):
    """用户-工厂-角色关联表"""
    __tablename__ = 'sys_user_factory_role'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'factory_id', 'role_id', name='uk_user_factory_role'),
        {'comment': '用户-工厂-角色关联表'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='用户ID')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False,
                           comment='工厂ID（平台角色时可为0）')
    role_id = db.Column(db.Integer, db.ForeignKey('sys_role.id'), nullable=False, comment='角色ID')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')

    user = db.relationship('User', backref='user_factory_roles')
    factory = db.relationship('Factory', backref='user_factory_roles')
    role = db.relationship('Role', backref='user_factory_roles')
