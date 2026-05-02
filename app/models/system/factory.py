# 工厂模型
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Factory(BaseModel):
    """工厂表（租户）"""
    __tablename__ = 'sys_factory'
    __table_args__ = {'comment': '工厂表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, comment='工厂名称')
    code = db.Column(db.String(50), unique=True, nullable=False, comment='工厂编码')
    contact_person = db.Column(db.String(50), comment='联系人')
    contact_phone = db.Column(db.String(20), comment='联系电话')
    address = db.Column(db.String(255), comment='地址')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1启用 0禁用')
    qrcode = db.Column(db.String(500), comment='工厂二维码URL，扫码可绑定工厂')
    qrcode_key = db.Column(db.String(100), unique=True, comment='二维码唯一标识，用于扫码绑定')
    vip_expire_date = db.Column(db.Date, comment='工厂VIP到期日期')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'address': self.address,
            'status': self.status,
            'remark': self.remark,
            'qrcode': self.qrcode,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None
        }
