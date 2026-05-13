from marshmallow import Schema, fields, validate


class UserBaseSchema(Schema):
    platform_identity = fields.Str()
    platform_identity_label = fields.Str()
    subject_type = fields.Method('get_subject_type')
    subject_type_label = fields.Method('get_subject_type_label')

    def get_subject_type(self, obj):
        relation_types = [relation.relation_type for relation in getattr(obj, 'user_factories', []) if relation.is_deleted == 0]
        return obj.get_subject_type(relation_types)

    def get_subject_type_label(self, obj):
        relation_types = [relation.relation_type for relation in getattr(obj, 'user_factories', []) if relation.is_deleted == 0]
        return obj.get_subject_type_label(relation_types)


class UserSchema(UserBaseSchema):
    id = fields.Int()
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20), load_only=True)
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    avatar = fields.Str()
    status = fields.Int(default=1)
    is_paid = fields.Int()
    invite_code = fields.Str()
    invited_count = fields.Int()
    created_by = fields.Int()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    last_login_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class UserLoginSchema(UserBaseSchema):
    id = fields.Int()
    username = fields.Str()
    nickname = fields.Str()
    phone = fields.Str()
    avatar = fields.Str()
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
    platform_identity = fields.Str(validate=validate.OneOf(['platform_admin', 'platform_staff', 'external_user']))
    invite_code = fields.Str(description='邀请码（可选）')
    factory_id = fields.Int()


class UserUpdateSchema(Schema):
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    status = fields.Int(validate=validate.OneOf([0, 1]))


class UserResetPasswordSchema(Schema):
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
