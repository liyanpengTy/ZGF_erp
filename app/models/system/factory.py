# 工厂模型
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Factory(BaseModel):
    """工厂表（租户）"""
    __tablename__ = 'sys_factory'
    __table_args__ = {'comment': '工厂表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, comment='工厂名称')
    code = db.Column(db.String(50), unique=True, nullable=False, comment='工厂编码')
    contact_person = db.Column(db.String(50), comment='联系人')
    contact_phone = db.Column(db.String(20), comment='联系电话')
    address = db.Column(db.String(255), comment='地址')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1启用 0禁用')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    remark = db.Column(db.String(500), comment='备注')
