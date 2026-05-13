from marshmallow import Schema, fields, validate


class RoleSchema(Schema):
    """角色序列化器。"""

    id = fields.Int()
    factory_id = fields.Int()
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
    """创建角色参数。"""

    name = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    description = fields.Str(validate=validate.Length(max=255))
    sort_order = fields.Int(default=0)
    data_scope = fields.Str(validate=validate.OneOf(['all_factory', 'assigned', 'own_related', 'self_only']))
    is_factory_admin = fields.Int(validate=validate.OneOf([0, 1]))


class RoleUpdateSchema(Schema):
    """更新角色参数。"""

    name = fields.Str(validate=validate.Length(min=2, max=50))
    description = fields.Str(validate=validate.Length(max=255))
    status = fields.Int(validate=validate.OneOf([0, 1]))
    sort_order = fields.Int()
    data_scope = fields.Str(validate=validate.OneOf(['all_factory', 'assigned', 'own_related', 'self_only']))
    is_factory_admin = fields.Int(validate=validate.OneOf([0, 1]))


class RoleAssignMenuSchema(Schema):
    """分配菜单权限参数。"""

    menu_ids = fields.List(fields.Int(), required=True, description='菜单ID列表')
