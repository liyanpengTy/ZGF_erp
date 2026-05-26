"""款号橡筋模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class StyleElastic(BaseModel):
    """记录款号在不同尺码下的橡筋配置。"""

    __tablename__ = 'fab_style_elastic'
    __table_args__ = ({'comment': '款号橡筋明细表，记录不同尺码所需的橡筋规格'},)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    size_id = db.Column(db.Integer, db.ForeignKey('sys_size.id'), comment='尺码ID，为空表示适用于全部尺码')
    elastic_type = db.Column(db.String(50), nullable=False, comment='橡筋类型，例如 1cm 宽橡筋')
    elastic_length = db.Column(db.Numeric(10, 2), nullable=False, comment='橡筋长度，单位厘米')
    quantity = db.Column(db.Integer, default=1, comment='数量')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    remark = db.Column(db.String(255), comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    style = db.relationship('Style', backref='elastics')
    size = db.relationship('Size', backref='style_elastics')
