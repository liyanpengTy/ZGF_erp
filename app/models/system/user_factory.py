from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class UserFactory(BaseModel):
    """用户-工厂关联表"""
    __tablename__ = 'sys_user_factory'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'factory_id', 'relation_type', name='uk_user_factory_relation'),
        {'comment': '用户-工厂关联表，记录用户与工厂的关系类型'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='用户ID')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    relation_type = db.Column(db.String(20), nullable=False,
                              comment='关系类型：employee-员工，customer-客户，collaborator-协作用户')
    status = db.Column(db.SmallInteger, default=1, comment='关联状态：1-在职/有效，0-离职/无效')
    entry_date = db.Column(db.Date, comment='入职日期/关联日期')
    leave_date = db.Column(db.Date, comment='离职日期/解除日期')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    remark = db.Column(db.String(255), comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    user = db.relationship('User', backref='user_factories')
    factory = db.relationship('Factory', backref='user_factories')
