"""工序相关序列化定义。"""

from marshmallow import Schema, fields, validate


class ProcessSchema(Schema):
    """工序返回结构。"""

    id = fields.Int()
    name = fields.Str()
    code = fields.Str()
    description = fields.Str()
    sort_order = fields.Int()
    status = fields.Int()
    create_time = fields.DateTime(format="%Y-%m-%d %H:%M:%S")
    update_time = fields.DateTime(format="%Y-%m-%d %H:%M:%S")


class ProcessCreateSchema(Schema):
    """创建工序入参，名称和编码必须填写。"""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    code = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    description = fields.Str(validate=validate.Length(max=255))
    sort_order = fields.Int(load_default=0)


class ProcessUpdateSchema(Schema):
    """更新工序入参。"""

    name = fields.Str(validate=validate.Length(min=1, max=50))
    description = fields.Str(validate=validate.Length(max=255))
    sort_order = fields.Int()
    status = fields.Int(validate=validate.OneOf([0, 1]))


class StyleProcessMappingSchema(Schema):
    """款号工序映射返回结构。"""

    id = fields.Int()
    style_id = fields.Int()
    process_id = fields.Int()
    process_name = fields.Str()
    process_code = fields.Str()
    sequence = fields.Int()
    remark = fields.Str()


class StyleProcessMappingCreateSchema(Schema):
    """创建款号工序映射入参。"""

    process_id = fields.Int(required=True)
    sequence = fields.Int(load_default=1)
    remark = fields.Str()


class StyleProcessMappingBatchSchema(Schema):
    """批量保存款号工序映射入参。"""

    mappings = fields.List(
        fields.Nested(StyleProcessMappingCreateSchema),
        required=True,
    )
