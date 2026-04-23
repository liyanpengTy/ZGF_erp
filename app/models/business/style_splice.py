from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class StyleSplice(BaseModel):
    __tablename__ = 'fab_style_splice'
    __table_args__ = (
        {'comment': '款号拼接明细表，记录颜色拼接、布料拼接等拼接信息'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    splice_type = db.Column(db.String(20), nullable=False,
                            comment='拼接类型：color-颜色拼接，fabric-布料拼接，lace-蕾丝拼接，other-其他')
    material_id = db.Column(db.Integer, comment='材料ID（颜色ID或布料ID）')
    material_name = db.Column(db.String(100), comment='材料名称')
    material_code = db.Column(db.String(50), comment='材料编码')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    remark = db.Column(db.String(255), comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    style = db.relationship('Style', backref='splices')
