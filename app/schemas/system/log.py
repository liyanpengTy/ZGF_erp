from marshmallow import Schema, fields


class OperationLogSchema(Schema):
    """操作日志序列化器"""
    id = fields.Int()
    user_id = fields.Int()
    username = fields.Str()
    factory_id = fields.Int()
    operation = fields.Str()
    method = fields.Str()
    url = fields.Str()
    params = fields.Str()
    ip = fields.Str()
    duration = fields.Int()
    status = fields.Int()
    error_msg = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class LoginLogSchema(Schema):
    """登录日志序列化器"""
    id = fields.Int()
    user_id = fields.Int()
    username = fields.Str()
    login_type = fields.Str()  # pc/miniapp
    ip = fields.Str()
    status = fields.Int()  # 1-成功 0-失败
    error_msg = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')