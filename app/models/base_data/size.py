"""尺码模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class Size(BaseModel):
    """维护系统默认尺码和工厂自定义尺码。"""

    __tablename__ = 'sys_size'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'code', 'is_deleted', name='uk_factory_size_code'),
        {'comment': '尺码表，存储系统默认尺码和工厂自定义尺码'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=False, comment='尺码名称，例如 S、M、L、XL')
    code = db.Column(db.String(20), nullable=False, comment='尺码编码')
    factory_id = db.Column(db.Integer, default=0, comment='所属工厂ID，0 表示全局默认，大于 0 表示工厂自定义')
    sort_order = db.Column(db.Integer, default=0, comment='排序值，数值越小越靠前')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
