"""用户相关序列化定义。"""

from marshmallow import Schema, fields, validate

from app.constants.identity import RELATION_TYPE_CUSTOMER, ROLE_SCOPE_FACTORY, ROLE_SCOPE_PLATFORM, ROLE_SCOPE_SUBJECT


PLATFORM_IDENTITY_CHOICES = ['platform_admin', 'platform_staff', 'external_user']


class UserBaseSchema(Schema):
    """用户基础返回结构。"""

    platform_identity = fields.Str()
    platform_identity_label = fields.Str()
    subject_type = fields.Method('get_subject_type')
    subject_type_label = fields.Method('get_subject_type_label')

    def get_subject_type(self, obj):
        """根据用户工厂关系推导主体类型。"""
        relation_types = [
            relation.relation_type
            for relation in getattr(obj, 'user_factories', [])
            if relation.is_deleted == 0 and relation.relation_type != RELATION_TYPE_CUSTOMER
        ]
        return obj.get_subject_type(relation_types)

    def get_subject_type_label(self, obj):
        """根据用户工厂关系返回主体类型名称。"""
        relation_types = [
            relation.relation_type
            for relation in getattr(obj, 'user_factories', [])
            if relation.is_deleted == 0 and relation.relation_type != RELATION_TYPE_CUSTOMER
        ]
        return obj.get_subject_type_label(relation_types)


class UserSchema(UserBaseSchema):
    """用户详情结构。"""

    id = fields.Int()
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20), load_only=True)
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    avatar = fields.Str()
    status = fields.Int(dump_default=1)
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
    platform_identity = fields.Str(validate=validate.OneOf(PLATFORM_IDENTITY_CHOICES))
    invite_code = fields.Str(validate=validate.Length(max=50))
    factory_id = fields.Int(validate=validate.Range(min=1))


class UserUpdateSchema(Schema):
    """更新用户请求结构。"""

    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(validate=validate.Length(max=20))
    status = fields.Int(validate=validate.OneOf([0, 1]))


class UserResetPasswordSchema(Schema):
    """重置密码请求结构。"""

    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))


class LoginRequestSchema(Schema):
    """账号密码登录入参。"""

    username = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))


class RegisterRequestSchema(Schema):
    """注册入参。"""

    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    nickname = fields.Str(validate=validate.Length(max=50))
    phone = fields.Str(required=True, validate=validate.Length(max=20))
    invite_code = fields.Str(validate=validate.Length(max=50))


class SwitchFactorySchema(Schema):
    """切换工厂入参。"""

    factory_id = fields.Int(required=True, validate=validate.Range(min=1))


class UserAssignRolesSchema(Schema):
    """用户角色分配入参。"""

    role_ids = fields.List(fields.Int(validate=validate.Range(min=1)), required=True)
    factory_id = fields.Int(allow_none=True, validate=validate.Range(min=0))
    scope_type = fields.Str(validate=validate.OneOf([ROLE_SCOPE_PLATFORM, ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT]))
