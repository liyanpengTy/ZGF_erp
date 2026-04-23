from marshmallow import Schema, fields, validate


class ProfileUpdateSchema(Schema):
    """更新个人信息参数"""
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    avatar = fields.Str(validate=validate.Length(max=255))


class PasswordChangeSchema(Schema):
    """修改密码参数"""
    old_password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    new_password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    confirm_password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
