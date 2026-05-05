"""分类模型"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Category(BaseModel):
    """分类表（支持树形结构，工厂级隔离）"""
    __tablename__ = 'sys_category'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'code', 'is_deleted', name='uk_factory_category_code'),
        {'comment': '分类表，存储产品分类、款号分类等树形结构数据'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id = db.Column(db.Integer, default=0, comment='父分类ID，0表示顶级分类')
    name = db.Column(db.String(50), nullable=False, comment='分类名称')
    code = db.Column(db.String(50), nullable=False, comment='分类编码，工厂内唯一')

    # 分类类型
    category_type = db.Column(db.String(20), default='style', comment='分类类型：style-款号，material-物料，order-订单')

    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), default=0, comment='所属工厂ID，0表示系统内置')
    sort_order = db.Column(db.Integer, default=0, comment='排序序号，越小越靠前')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    remark = db.Column(db.String(255), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        data = super().to_dict()
        data.pop('is_deleted', None)
        return data
