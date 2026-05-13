from datetime import datetime

from app.constants.identity import (
    COLLABORATOR_TYPE_BUTTON,
    COLLABORATOR_TYPE_OTHER,
    COLLABORATOR_TYPE_PRINT,
    COLLABORATOR_TYPE_SHRINK,
    RELATION_TYPE_COLLABORATOR,
    RELATION_TYPE_CUSTOMER,
    RELATION_TYPE_EMPLOYEE,
    RELATION_TYPE_OWNER,
)
from app.extensions import db
from app.models.base import BaseModel


class UserFactory(BaseModel):
    """用户-工厂关联表。"""

    __tablename__ = 'sys_user_factory'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'factory_id', 'relation_type', name='uk_user_factory_relation'),
        {'comment': '用户-工厂关联表，记录用户与工厂的关系类型'}
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), nullable=False, comment='用户ID')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    relation_type = db.Column(
        db.String(20),
        nullable=False,
        comment='关系类型：owner-工厂管理员，employee-员工，customer-客户，collaborator-协作用户'
    )
    collaborator_type = db.Column(
        db.String(30),
        comment='协作类型：button_partner/shrink_partner/print_partner/other_partner'
    )
    status = db.Column(db.SmallInteger, default=1, comment='关联状态：1-有效，0-无效')
    entry_date = db.Column(db.Date, comment='入职日期/关联日期')
    leave_date = db.Column(db.Date, comment='离职日期/解除日期')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除')
    remark = db.Column(db.String(255), comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    user = db.relationship('User', backref='user_factories')
    factory = db.relationship('Factory', backref='user_factories')

    @property
    def relation_type_label(self):
        """返回用户在工厂中的关系类型中文名称。"""
        labels = {
            RELATION_TYPE_OWNER: '工厂管理员',
            RELATION_TYPE_EMPLOYEE: '工厂员工',
            RELATION_TYPE_CUSTOMER: '订单客户',
            RELATION_TYPE_COLLABORATOR: '协作用户'
        }
        return labels.get(self.relation_type, self.relation_type)

    @property
    def collaborator_type_label(self):
        """返回协作用户细分类型的中文名称。"""
        labels = {
            COLLABORATOR_TYPE_BUTTON: '专机钉扣',
            COLLABORATOR_TYPE_SHRINK: '缩水厂',
            COLLABORATOR_TYPE_PRINT: '印花厂',
            COLLABORATOR_TYPE_OTHER: '其他协作方'
        }
        return labels.get(self.collaborator_type, self.collaborator_type)
