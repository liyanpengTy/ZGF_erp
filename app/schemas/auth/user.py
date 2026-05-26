"""用户相关序列化定义。"""

from marshmallow import Schema, fields, validate


class UserBaseSchema(Schema):
    """用户基础返回结构。"""

    platform_identity = fields.Str()
    platform_identity_label = fields.Str()
    subject_type = fields.Method('get_subject_type')
    subject_type_label = fields.Method('get_subject_type_label')

    def get_subject_type(self, obj):
        """根据用户工厂关系推导主体类型。"""
        relation_types = [relation.relation_type for relation in getattr(obj, 'user_factories', []) if relation.is_deleted == 0]
        return obj.get_subject_type(relation_types)

    def get_subject_type_label(self, obj):
        """根据用户工厂关系返回主体类型中文名称。"""
        relation_types = [relation.relation_type for relation in getattr(obj, 'user_factories', []) if relation.is_deleted == 0]
        return obj.get_subject_type_label(relation_types)


class UserSchema(UserBaseSchema):
    """用户详情结构。"""

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
    """登录后返回的用户结构。"""

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
    """创建用户请求结构。"""

    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    platform_identity = fields.Str(validate=validate.OneOf(['platform_admin', 'platform_staff', 'external_user']))
    invite_code = fields.Str(description='邀请码，可选')
    factory_id = fields.Int()


class UserUpdateSchema(Schema):
    """更新用户请求结构。"""

    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    status = fields.Int(validate=validate.OneOf([0, 1]))


class UserResetPasswordSchema(Schema):
    """重置密码请求结构。"""

    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
