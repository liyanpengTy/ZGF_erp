from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class StyleProcess(BaseModel):
    __tablename__ = 'fab_style_process'
    __table_args__ = (
        {'comment': '款号工艺表，记录刺绣、印花等特殊工艺'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    process_type = db.Column(db.String(20), nullable=False, comment='工艺类型：embroidery-刺绣，print-印花，other-其他')
    process_name = db.Column(db.String(50), comment='工艺名称，如：电脑刺绣、丝网印花')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    remark = db.Column(db.String(255), comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    style = db.relationship('Style', backref='processes')
