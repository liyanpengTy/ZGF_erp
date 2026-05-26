"""角色相关序列化定义。"""

from marshmallow import Schema, fields, validate

from app.constants.identity import ROLE_SCOPE_FACTORY, ROLE_SCOPE_PLATFORM


ACTIVE_ROLE_SCOPES = (ROLE_SCOPE_FACTORY, ROLE_SCOPE_PLATFORM)


class RoleSchema(Schema):
    """角色返回结构。"""

    id = fields.Int()
    scope_type = fields.Str()
    scope_type_label = fields.Str()
    scope_id = fields.Int()
    name = fields.Str()
    code = fields.Str()
    description = fields.Str()
    status = fields.Int()
    sort_order = fields.Int()
    data_scope = fields.Str()
    data_scope_label = fields.Str()
    is_factory_admin = fields.Int()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class RoleCreateSchema(Schema):
    """创建角色请求结构。"""

    scope_type = fields.Str(load_default=ROLE_SCOPE_FACTORY, validate=validate.OneOf(sorted(ACTIVE_ROLE_SCOPES)))
    scope_id = fields.Int(load_default=0, allow_none=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    description = fields.Str(validate=validate.Length(max=255))
    sort_order = fields.Int(load_default=0)
    data_scope = fields.Str(validate=validate.OneOf(['all_factory', 'assigned', 'own_related', 'self_only']))
    is_factory_admin = fields.Int(validate=validate.OneOf([0, 1]))


class RoleUpdateSchema(Schema):
    """更新角色请求结构。"""

    name = fields.Str(validate=validate.Length(min=2, max=50))
    description = fields.Str(validate=validate.Length(max=255))
    status = fields.Int(validate=validate.OneOf([0, 1]))
    sort_order = fields.Int()
    data_scope = fields.Str(validate=validate.OneOf(['all_factory', 'assigned', 'own_related', 'self_only']))
    is_factory_admin = fields.Int(validate=validate.OneOf([0, 1]))


class RoleAssignMenuSchema(Schema):
    """角色菜单分配请求结构。"""

    menu_ids = fields.List(fields.Int(), required=True, description='菜单ID列表')
