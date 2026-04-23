# 日志模型
from app.extensions import db
from datetime import datetime


class OperationLog(db.Model):
    """操作日志表"""
    __tablename__ = 'sys_operation_log'
    __table_args__ = {'comment': '操作日志表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, comment='操作用户ID')
    username = db.Column(db.String(50), comment='操作用户名')
    factory_id = db.Column(db.Integer, comment='所属工厂ID')
    operation = db.Column(db.String(255), comment='操作描述')
    method = db.Column(db.String(10), comment='请求方法')
    url = db.Column(db.String(255), comment='请求URL')
    params = db.Column(db.Text, comment='请求参数')
    ip = db.Column(db.String(50), comment='IP地址')
    duration = db.Column(db.Integer, comment='执行耗时(ms)')
    status = db.Column(db.SmallInteger, comment='状态：1成功 0失败')
    error_msg = db.Column(db.Text, comment='错误信息')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='操作时间')


class LoginLog(db.Model):
    """登录日志表"""
    __tablename__ = 'sys_login_log'
    __table_args__ = {'comment': '登录日志表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, comment='用户ID')
    username = db.Column(db.String(50), comment='用户名')
    login_type = db.Column(db.String(20), comment='登录类型：pc/miniapp')
    ip = db.Column(db.String(50), comment='IP地址')
    status = db.Column(db.SmallInteger, comment='状态：1成功 0失败')
    error_msg = db.Column(db.String(255), comment='错误信息')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='登录时间')
