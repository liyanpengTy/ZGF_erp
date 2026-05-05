from marshmallow import Schema, fields, validate


class CategorySchema(Schema):
    """分类序列化器"""
    id = fields.Int()
    parent_id = fields.Int()
    name = fields.Str()
    code = fields.Str()
    category_type = fields.Str()
    factory_id = fields.Int()
    sort_order = fields.Int()
    status = fields.Int()
    remark = fields.Str()
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    children = fields.List(fields.Nested(lambda: CategorySchema()), default=[])


class CategoryCreateSchema(Schema):
    """创建分类参数"""
    parent_id = fields.Int(default=0)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    category_type = fields.Str(default='style', validate=validate.OneOf(['style', 'material', 'order']))
    sort_order = fields.Int(default=0)
    remark = fields.Str(validate=validate.Length(max=255))


class CategoryUpdateSchema(Schema):
    """更新分类参数"""
    parent_id = fields.Int()
    name = fields.Str(validate=validate.Length(min=1, max=50))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))
    category_type = fields.Str(validate=validate.OneOf(['style', 'material', 'order']))
    remark = fields.Str(validate=validate.Length(max=255))
