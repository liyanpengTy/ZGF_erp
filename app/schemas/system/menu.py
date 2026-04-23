from marshmallow import Schema, fields, validate


class MenuSchema(Schema):
    """菜单序列化器"""
    id = fields.Int()
    parent_id = fields.Int()
    name = fields.Str()
    path = fields.Str()
    component = fields.Str()
    permission = fields.Str()
    type = fields.Int()  # 0-目录 1-菜单 2-按钮
    icon = fields.Str()
    sort_order = fields.Int()
    status = fields.Int()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')

    # 子菜单（用于树形结构）
    children = fields.List(fields.Nested(lambda: MenuSchema()), default=[])


class MenuCreateSchema(Schema):
    """创建菜单参数"""
    parent_id = fields.Int(default=0)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    path = fields.Str(validate=validate.Length(max=100))
    component = fields.Str(validate=validate.Length(max=100))
    permission = fields.Str(validate=validate.Length(max=100))
    type = fields.Int(required=True, validate=validate.OneOf([0, 1, 2]))
    icon = fields.Str(validate=validate.Length(max=50))
    sort_order = fields.Int(default=0)


class MenuUpdateSchema(Schema):
    """更新菜单参数"""
    parent_id = fields.Int()
    name = fields.Str(validate=validate.Length(min=1, max=50))
    path = fields.Str(validate=validate.Length(max=100))
    component = fields.Str(validate=validate.Length(max=100))
    permission = fields.Str(validate=validate.Length(max=100))
    type = fields.Int(validate=validate.OneOf([0, 1, 2]))
    icon = fields.Str(validate=validate.Length(max=50))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))