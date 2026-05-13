from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.base import BaseModel


class Factory(BaseModel):
    """工厂表。"""

    __tablename__ = 'sys_factory'
    __table_args__ = {'comment': '工厂表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, comment='工厂名称')
    code = db.Column(db.String(50), unique=True, nullable=False, comment='工厂编码')
    contact_person = db.Column(db.String(50), comment='联系人')
    contact_phone = db.Column(db.String(20), comment='联系电话')
    address = db.Column(db.String(255), comment='地址')
    status = db.Column(db.SmallInteger, default=1, comment='状态：1-启用，0-禁用')
    qrcode = db.Column(db.String(500), comment='工厂二维码URL')
    qrcode_key = db.Column(db.String(100), unique=True, comment='二维码唯一标识')
    service_expire_date = db.Column(db.Date, comment='工厂服务到期日期')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    def get_service_status(self, today=None):
        """根据工厂状态和到期日计算当前服务状态。"""
        today = today or date.today()
        if self.status != 1:
            return 'disabled'
        if not self.service_expire_date:
            return 'active'
        if self.service_expire_date < today:
            return 'expired'
        if self.service_expire_date <= today + timedelta(days=30):
            return 'expiring_soon'
        return 'active'

    @property
    def service_status(self):
        """返回当前工厂的服务状态。"""
        return self.get_service_status()

    @property
    def is_service_expired(self):
        """便于业务层快速判断工厂是否已过期。"""
        return self.service_status == 'expired'

    def to_dict(self):
        """导出工厂数据。"""
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
            'service_expire_date': self.service_expire_date.isoformat() if self.service_expire_date else None,
            'service_status': self.service_status,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None
        }
