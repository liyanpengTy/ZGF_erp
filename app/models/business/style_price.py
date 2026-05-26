"""款号价格模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class StylePrice(BaseModel):
    """记录款号价格及其历史生效时间。"""

    __tablename__ = 'fab_style_price'
    __table_args__ = ({'comment': '款号价格表，记录不同价格类型及历史变更'},)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    price_type = db.Column(
        db.String(20),
        nullable=False,
        comment='价格类型：customer-客户价，internal-内部价，outsourced-外发价，button-钉扣价，other-其他',
    )
    price = db.Column(db.Numeric(10, 2), nullable=False, comment='价格')
    effective_date = db.Column(db.Date, nullable=False, comment='生效日期')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    remark = db.Column(db.String(255), comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    style = db.relationship('Style', backref='prices')
