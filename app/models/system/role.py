from datetime import datetime

from app.constants.identity import (
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_DATA_SCOPE_SELF_ONLY,
    ROLE_SCOPE_FACTORY,
    ROLE_SCOPE_PARTNER,
    ROLE_SCOPE_PLATFORM,
)
from app.extensions import db
from app.models.base import BaseModel

# 角色-菜单关联表，用于维护角色拥有的菜单与按钮权限。
role_menu = db.Table(
    'sys_role_menu',
    db.Column('role_id', db.Integer, db.ForeignKey('sys_role.id'), primary_key=True, comment='角色ID'),
    db.Column('menu_id', db.Integer, db.ForeignKey('sys_menu.id'), primary_key=True, comment='菜单或按钮权限ID'),
    comment='角色-菜单关联表'
)


class Role(BaseModel):
    """系统角色表，统一承载平台角色、工厂角色和后续协作主体角色。"""

    __tablename__ = 'sys_role'
    __table_args__ = (
        db.UniqueConstraint('scope_type', 'scope_id', 'code', 'is_deleted', name='uk_role_scope_code'),
        {'comment': '系统角色表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='角色ID')
    scope_type = db.Column(
        db.String(20),
        nullable=False,
        default=ROLE_SCOPE_FACTORY,
        comment='角色归属范围：platform-平台，factory-工厂，partner_subject-协作主体'
    )
    scope_id = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        comment='角色归属主键：平台角色固定为0，工厂角色为工厂ID，协作主体角色为主体ID'
    )
    name = db.Column(db.String(50), nullable=False, comment='角色名称')
    code = db.Column(db.String(50), nullable=False, comment='角色编码')
    description = db.Column(db.String(255), comment='角色说明')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    sort_order = db.Column(db.Integer, default=0, comment='排序值，数字越小越靠前')
    data_scope = db.Column(
        db.String(20),
        default=ROLE_DATA_SCOPE_OWN_RELATED,
        nullable=False,
        comment='数据范围：all_factory-全工厂，assigned-分配数据，own_related-本人关联，self_only-仅本人'
    )
    is_factory_admin = db.Column(db.SmallInteger, default=0, comment='是否工厂管理员角色：1-是，0-否')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')

    @property
    def is_platform_role(self):
        """判断当前角色是否属于平台级角色。"""
        return self.scope_type == ROLE_SCOPE_PLATFORM

    @property
    def is_factory_role(self):
        """判断当前角色是否属于工厂级角色。"""
        return self.scope_type == ROLE_SCOPE_FACTORY

    @property
    def is_partner_role(self):
        """判断当前角色是否属于协作主体等扩展主体角色。"""
        return self.scope_type == ROLE_SCOPE_PARTNER

    @property
    def scope_type_label(self):
        """返回角色归属范围的中文显示名称。"""
        labels = {
            ROLE_SCOPE_PLATFORM: '平台角色',
            ROLE_SCOPE_FACTORY: '工厂角色',
            ROLE_SCOPE_PARTNER: '协作主体角色',
        }
        return labels.get(self.scope_type, self.scope_type)

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
