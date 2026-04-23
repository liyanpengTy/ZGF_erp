# 菜单/权限模型
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Menu(BaseModel):
    """菜单/权限表"""
    __tablename__ = 'sys_menu'
    __table_args__ = {'comment': '菜单/权限表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id = db.Column(db.Integer, default=0, comment='父菜单ID')
    name = db.Column(db.String(50), nullable=False, comment='菜单名称')
    path = db.Column(db.String(100), comment='路由路径')
    component = db.Column(db.String(100), comment='组件路径')
    permission = db.Column(db.String(100), comment='权限标识')
    type = db.Column(db.SmallInteger, comment='类型：0目录 1菜单 2按钮')
    icon = db.Column(db.String(50), comment='图标')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1启用 0禁用')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    remark = db.Column(db.String(500), comment='备注')
