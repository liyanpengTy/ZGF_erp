# 角色模型
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


# 角色-菜单关联表
role_menu = db.Table('sys_role_menu',
                     db.Column('role_id', db.Integer, db.ForeignKey('sys_role.id'), primary_key=True, comment='角色id'),
                     db.Column('menu_id', db.Integer, db.ForeignKey('sys_menu.id'), primary_key=True, comment='菜单/权限id')
                     )


class Role(BaseModel):
    __tablename__ = 'sys_role'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='所属工厂ID')
    name = db.Column(db.String(50), nullable=False, comment='角色名称')
    code = db.Column(db.String(50), nullable=False, comment='角色编码')
    description = db.Column(db.String(255), comment='描述')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1启用 0禁用')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    remark = db.Column(db.String(500), comment='备注')

    # 关联关系
    factory = db.relationship('Factory', backref='roles')

    # 联合唯一索引：同一工厂下角色名和编码唯一
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'name', name='uk_factory_role_name'),
        db.UniqueConstraint('factory_id', 'code', name='uk_factory_role_code'),
        {'comment': '角色表'}
    )
