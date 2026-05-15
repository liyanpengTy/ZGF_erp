"""款号业务模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel
from app.models.business.value_codec import decode_dynamic_value


class Style(BaseModel):
    """款号主表，存储款号基础信息。"""

    __tablename__ = 'fab_style'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'style_no', 'is_deleted', name='uk_factory_style_no'),
        {'comment': '款号主表，存储款号基础信息和生产属性'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='所属工厂ID')
    style_no = db.Column(db.String(50), nullable=False, comment='款号，工厂内唯一')
    customer_style_no = db.Column(db.String(50), comment='客户款号')
    name = db.Column(db.String(100), comment='款号名称')
    category_id = db.Column(db.Integer, db.ForeignKey('sys_category.id'), comment='分类ID')
    gender = db.Column(db.String(10), comment='适用性别')
    season = db.Column(db.String(10), comment='适用季节')
    material = db.Column(db.String(200), comment='材质成分')
    description = db.Column(db.Text, comment='详细描述')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    need_cutting = db.Column(db.SmallInteger, default=0, comment='是否需要裁床预留：1-是，0-否')
    cutting_reserve = db.Column(db.Numeric(10, 2), default=0, comment='裁床预留长度(厘米)')
    is_splice = db.Column(db.SmallInteger, default=0, comment='是否拼接款：0-否，1-是')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='styles')
    category = db.relationship('Category', backref='styles')
    image_items = db.relationship('StyleImage', backref='style', cascade='all, delete-orphan')
    splice_items = db.relationship('StyleSpliceItem', backref='style', cascade='all, delete-orphan')
    attribute_items = db.relationship('StyleAttribute', backref='style', cascade='all, delete-orphan')

    @property
    def images(self):
        """返回款号图片列表。"""
        return [
            item.image_url
            for item in sorted(self.image_items, key=lambda current: (current.sort_order, current.id or 0))
            if item.image_url
        ]

    @property
    def splice_data(self):
        """返回款号拼接结构列表。"""
        return [
            {'sequence': item.sequence, 'description': item.description}
            for item in sorted(self.splice_items, key=lambda current: (current.sequence, current.id or 0))
        ]

    @property
    def custom_attributes(self):
        """返回款号自定义属性字典。"""
        return {
            item.attr_key: decode_dynamic_value(item.value_type, item.attr_value)
            for item in sorted(self.attribute_items, key=lambda current: (current.sort_order, current.id or 0))
        }


class StyleImage(BaseModel):
    """款号图片明细表。"""

    __tablename__ = 'fab_style_image'
    __table_args__ = (
        db.Index('idx_fab_style_image_style_id', 'style_id'),
        {'comment': '款号图片明细表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    image_url = db.Column(db.String(500), nullable=False, comment='图片地址')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class StyleSpliceItem(BaseModel):
    """款号拼接结构明细表。"""

    __tablename__ = 'fab_style_splice_item'
    __table_args__ = (
        db.Index('idx_fab_style_splice_item_style_id', 'style_id'),
        {'comment': '款号拼接结构明细表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    sequence = db.Column(db.Integer, nullable=False, comment='顺序')
    description = db.Column(db.String(255), nullable=False, comment='拼接描述')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class StyleAttribute(BaseModel):
    """款号自定义属性明细表。"""

    __tablename__ = 'fab_style_attribute'
    __table_args__ = (
        db.Index('idx_fab_style_attribute_style_id', 'style_id'),
        {'comment': '款号自定义属性明细表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    attr_key = db.Column(db.String(100), nullable=False, comment='属性名')
    attr_value = db.Column(db.String(500), nullable=False, default='', comment='属性值')
    value_type = db.Column(db.String(20), nullable=False, default='str', comment='属性值类型')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
