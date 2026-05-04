from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Category(BaseModel):
    __tablename__ = 'sys_category'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'code', 'is_deleted', name='uk_factory_category_code'),
        {'comment': '分类表，存储系统默认分类和工厂自定义分类，支持多级分类'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, comment='分类名称')
    parent_id = db.Column(db.Integer, default=0, comment='父分类ID，0为顶级分类')
    code = db.Column(db.String(50), nullable=False, comment='分类编码')
    factory_id = db.Column(db.Integer, default=0, comment='所属工厂ID，0为全局默认，大于0为工厂自定义')
    category_type = db.Column(db.String(20), default='style', comment='分类类型：style-款号，material-物料，order-订单')
    sort_order = db.Column(db.Integer, default=0, comment='排序，数字越小越靠前')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
