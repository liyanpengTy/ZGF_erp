from datetime import datetime

from app.constants.identity import (
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_DATA_SCOPE_SELF_ONLY,
)
from app.extensions import db
from app.models.base import BaseModel

# 角色-菜单关联表
role_menu = db.Table(
    'sys_role_menu',
    db.Column('role_id', db.Integer, db.ForeignKey('sys_role.id'), primary_key=True),
    db.Column('menu_id', db.Integer, db.ForeignKey('sys_menu.id'), primary_key=True)
)


class Role(BaseModel):
    __tablename__ = 'sys_role'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'code', 'is_deleted', name='uk_factory_role_code'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, default=0, comment='0表示平台角色，>0表示工厂角色')
    name = db.Column(db.String(50), nullable=False, comment='角色名称')
    code = db.Column(db.String(50), nullable=False, comment='角色编码')
    description = db.Column(db.String(255), comment='描述')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    data_scope = db.Column(
        db.String(20),
        default=ROLE_DATA_SCOPE_OWN_RELATED,
        nullable=False,
        comment='数据范围：all_factory/assigned/own_related/self_only'
    )
    is_factory_admin = db.Column(db.SmallInteger, default=0, comment='是否工厂管理员角色：1-是，0-否')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')

    factory = db.relationship(
        'Factory',
        primaryjoin='and_(Role.factory_id == Factory.id, Role.factory_id > 0)',
        foreign_keys=[factory_id],
        backref='roles'
    )

    @property
    def is_platform_role(self):
        """判断该角色是否属于平台级角色。"""
        return self.factory_id == 0

    @property
    def is_factory_role(self):
        """判断该角色是否属于某个工厂。"""
        return self.factory_id > 0

    @property
    def data_scope_label(self):
        """返回角色数据范围的中文显示名称。"""
        labels = {
            ROLE_DATA_SCOPE_ALL: '全工厂数据',
            ROLE_DATA_SCOPE_ASSIGNED: '分配数据',
            ROLE_DATA_SCOPE_OWN_RELATED: '本人关联数据',
            ROLE_DATA_SCOPE_SELF_ONLY: '仅个人数据'
        }
        return labels.get(self.data_scope, self.data_scope)
