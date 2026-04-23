from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class User(BaseModel):
    __tablename__ = 'sys_user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
    password = db.Column(db.String(255), nullable=False, comment='密码')
    nickname = db.Column(db.String(50), comment='昵称')
    email = db.Column(db.String(100), comment='邮箱')
    phone = db.Column(db.String(20), comment='手机号')
    avatar = db.Column(db.String(255), comment='头像')
    openid = db.Column(db.String(100), comment='微信openid')
    is_admin = db.Column(db.SmallInteger, default=0, comment='是否公司内部人员：1-是，0-否')
    status = db.Column(db.SmallInteger, default=1, comment='账号状态：1-正常，0-禁用')
    last_login_time = db.Column(db.DateTime, comment='最后登录时间')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        data = super().to_dict()
        data.pop('password', None)
        return data
