from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Color(BaseModel):
    __tablename__ = 'fab_color'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'code', 'is_deleted', name='uk_factory_color_code'),
        {'comment': '颜色表，存储布料颜色，支持工厂内叫法和实际名称对照'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, comment='颜色名称，工厂内叫法，如：子色')
    actual_name = db.Column(db.String(50), nullable=False, comment='实际颜色名称，布料上标准名称，如：紫色')
    code = db.Column(db.String(50), nullable=False, comment='颜色编码，工厂内唯一，如：PURPLE01')
    factory_id = db.Column(db.Integer, default=0, comment='所属工厂ID，0为全局默认，大于0为工厂自定义')
    sort_order = db.Column(db.Integer, default=0, comment='排序，数字越小越靠前')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    remark = db.Column(db.String(255), comment='备注信息')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
