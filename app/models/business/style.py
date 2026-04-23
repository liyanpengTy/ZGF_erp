from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Style(BaseModel):
    __tablename__ = 'fab_style'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'style_no', 'is_deleted', name='uk_factory_style_no'),
        {'comment': '款号主表，存储款号基础信息、生产属性等'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='所属工厂ID')
    style_no = db.Column(db.String(50), nullable=False, comment='款号，工厂内唯一，如：6032#')
    customer_style_no = db.Column(db.String(50), comment='客户款号，客户提供的款号编码')
    name = db.Column(db.String(100), comment='款号名称，产品名称，如：圆领印花T恤')
    category_id = db.Column(db.Integer, db.ForeignKey('sys_category.id'), comment='分类ID，关联分类表')
    gender = db.Column(db.String(10), comment='适用性别：男/女/通用')
    season = db.Column(db.String(10), comment='适用季节：春/夏/秋/冬/四季')
    material = db.Column(db.String(200), comment='材质成分，如：95%棉 5%氨纶')
    description = db.Column(db.Text, comment='详细描述')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    images = db.Column(db.JSON, comment='产品图片URL列表，JSON数组格式')
    need_cutting = db.Column(db.SmallInteger, default=0, comment='是否需要切捆条：1-是，0-否')
    cutting_reserve = db.Column(db.Numeric(10, 2), default=0, comment='捆条预留长度(厘米)，每件预留多少cm')
    custom_attributes = db.Column(db.JSON, comment='自定义属性，JSON格式，如：{"属性名":"属性值"}')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='styles')
    category = db.relationship('Category', backref='styles')
