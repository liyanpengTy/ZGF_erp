from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    id = fields.Int()
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20), load_only=True)
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    avatar = fields.Str()
    is_admin = fields.Int(default=0)
    status = fields.Int(default=1)
    is_paid = fields.Int()
    invite_code = fields.Str()
    invited_count = fields.Int()
    created_by = fields.Int()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    last_login_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class UserLoginSchema(Schema):
    id = fields.Int()
    username = fields.Str()
    nickname = fields.Str()
    phone = fields.Str()
    avatar = fields.Str()
    is_admin = fields.Int()
    status = fields.Int()
    is_paid = fields.Int()
    invite_code = fields.Str()
    invited_count = fields.Int()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    last_login_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class UserCreateSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    is_admin = fields.Int(default=0)
    invite_code = fields.Str(description='邀请码（可选）')
    factory_id = fields.Int()


class UserUpdateSchema(Schema):
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    status = fields.Int(validate=validate.OneOf([0, 1]))


class UserResetPasswordSchema(Schema):
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
