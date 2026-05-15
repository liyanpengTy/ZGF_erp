"""菲模板、菲规则与菲查询序列化器。"""

from marshmallow import Schema, fields, validate

from app.services.business.bundle_service import BundleService


class BundleTemplateItemSchema(Schema):
    """菲模板字段项序列化器。"""

    id = fields.Int()
    field_code = fields.Str()
    field_label = fields.Str()
    sort_order = fields.Int()
    is_visible = fields.Int()
    is_bold = fields.Int()
    is_new_line = fields.Int()


class BundleTemplateSchema(Schema):
    """菲模板序列化器。"""

    id = fields.Int()
    factory_id = fields.Int(allow_none=True)
    name = fields.Str()
    template_scope = fields.Str()
    scope_label = fields.Str()
    version = fields.Int()
    is_default = fields.Int()
    status = fields.Int()
    remark = fields.Str(allow_none=True)
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    items = fields.List(fields.Nested(BundleTemplateItemSchema))


class BundleTemplateItemCreateSchema(Schema):
    """创建或更新菲模板字段项参数。"""

    field_code = fields.Str(required=True, validate=validate.Length(max=50))
    field_label = fields.Str(required=True, validate=validate.Length(max=50))
    sort_order = fields.Int(load_default=0)
    is_visible = fields.Int(load_default=1, validate=validate.OneOf([0, 1]))
    is_bold = fields.Int(load_default=0, validate=validate.OneOf([0, 1]))
    is_new_line = fields.Int(load_default=1, validate=validate.OneOf([0, 1]))


class BundleTemplateCreateSchema(Schema):
    """创建菲模板参数。"""

    name = fields.Str(required=True, validate=validate.Length(max=100))
    is_default = fields.Int(load_default=0, validate=validate.OneOf([0, 1]))
    remark = fields.Str(validate=validate.Length(max=500))
    items = fields.List(fields.Nested(BundleTemplateItemCreateSchema), required=True, validate=validate.Length(min=1))


class BundleTemplateUpdateSchema(Schema):
    """更新菲模板参数。"""

    name = fields.Str(validate=validate.Length(max=100))
    is_default = fields.Int(validate=validate.OneOf([0, 1]))
    status = fields.Int(validate=validate.OneOf([0, 1]))
    remark = fields.Str(validate=validate.Length(max=500))
    items = fields.List(fields.Nested(BundleTemplateItemCreateSchema), validate=validate.Length(min=1))


class FactoryBundleRuleSchema(Schema):
    """工厂菲规则序列化器。"""

    id = fields.Int()
    factory_id = fields.Int()
    reset_cycle = fields.Str()
    reset_cycle_label = fields.Str()
    default_template_id = fields.Int(allow_none=True)
    bundle_code_prefix = fields.Str(allow_none=True)
    status = fields.Int()
    remark = fields.Str(allow_none=True)
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')


class FactoryBundleRuleUpdateSchema(Schema):
    """更新工厂菲规则参数。"""

    reset_cycle = fields.Str(validate=validate.OneOf(['yearly', 'monthly']))
    default_template_id = fields.Int(allow_none=True)
    bundle_code_prefix = fields.Str(validate=validate.Length(max=20))
    status = fields.Int(validate=validate.OneOf([0, 1]))
    remark = fields.Str(validate=validate.Length(max=500))


class ProductionBundleFlowSchema(Schema):
    """菲流转记录序列化器。"""

    id = fields.Int()
    process_id = fields.Int(allow_none=True)
    process_name = fields.Method('get_process_name')
    user_id = fields.Int(allow_none=True)
    user_name = fields.Method('get_user_name')
    from_user_id = fields.Int(allow_none=True)
    from_user_name = fields.Method('get_from_user_name')
    to_user_id = fields.Int(allow_none=True)
    to_user_name = fields.Method('get_to_user_name')
    action_type = fields.Str()
    action_type_label = fields.Str()
    quantity = fields.Int()
    action_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    remark = fields.Str(allow_none=True)

    def get_process_name(self, obj):
        """返回工序名称。"""
        return obj.process.name if obj.process else None

    def get_user_name(self, obj):
        """返回操作人名称。"""
        return obj.user.nickname if obj.user else None

    def get_from_user_name(self, obj):
        """返回来源人名称。"""
        return obj.from_user.nickname if obj.from_user else None

    def get_to_user_name(self, obj):
        """返回去向人名称。"""
        return obj.to_user.nickname if obj.to_user else None


class ProductionBundleSchema(Schema):
    """菲序列化器。"""

    id = fields.Int()
    factory_id = fields.Int()
    cutting_report_id = fields.Int()
    template_id = fields.Int(allow_none=True)
    template_version = fields.Int()
    bundle_no = fields.Str()
    order_id = fields.Int()
    order_detail_id = fields.Int()
    order_detail_sku_id = fields.Int()
    style_id = fields.Int()
    style_no = fields.Method('get_style_no')
    style_name = fields.Method('get_style_name')
    color_id = fields.Int(allow_none=True)
    color_name = fields.Method('get_color_name')
    size_id = fields.Int(allow_none=True)
    size_name = fields.Method('get_size_name')
    cut_batch_no = fields.Int()
    bed_no = fields.Int()
    bundle_quantity = fields.Int()
    priority = fields.Str()
    priority_label = fields.Str()
    status = fields.Str()
    status_label = fields.Str()
    current_holder_user_id = fields.Int(allow_none=True)
    current_holder_name = fields.Method('get_current_holder_name')
    current_process_id = fields.Int(allow_none=True)
    current_process_name = fields.Method('get_current_process_name')
    printed_content = fields.Str(allow_none=True)
    printed_at = fields.DateTime(format='%Y-%m-%d %H:%M:%S', allow_none=True)
    print_count = fields.Int()
    issued_quantity = fields.Method('get_issued_quantity')
    returned_quantity = fields.Method('get_returned_quantity')
    in_hand_quantity = fields.Method('get_in_hand_quantity')
    remark = fields.Str(allow_none=True)
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    flows = fields.List(fields.Nested(ProductionBundleFlowSchema))

    def get_style_no(self, obj):
        """返回款号。"""
        return obj.style.style_no if obj.style else None

    def get_style_name(self, obj):
        """返回款号名称。"""
        return obj.style.name if obj.style else None

    def get_color_name(self, obj):
        """返回颜色名称。"""
        return obj.color.name if obj.color else None

    def get_size_name(self, obj):
        """返回尺码名称。"""
        return obj.size.name if obj.size else None

    def get_current_holder_name(self, obj):
        """返回当前持有人名称。"""
        return obj.current_holder.nickname if obj.current_holder else None

    def get_current_process_name(self, obj):
        """返回当前工序名称。"""
        return obj.current_process.name if obj.current_process else None

    def get_issued_quantity(self, obj):
        """返回累计领货数量。"""
        return BundleService.calculate_flow_metrics(obj)['issued_quantity']

    def get_returned_quantity(self, obj):
        """返回累计交货数量。"""
        return BundleService.calculate_flow_metrics(obj)['returned_quantity']

    def get_in_hand_quantity(self, obj):
        """返回当前在手数量。"""
        return BundleService.calculate_flow_metrics(obj)['in_hand_quantity']


class BundleIssueSchema(Schema):
    """整菲领货参数。"""

    process_id = fields.Int(required=True)
    holder_user_id = fields.Int(allow_none=True)
    remark = fields.Str(validate=validate.Length(max=500))


class BundleReturnSchema(Schema):
    """交货参数。"""

    quantity = fields.Int(required=True)
    remark = fields.Str(validate=validate.Length(max=500))


class BundleTransferSchema(Schema):
    """转交参数。"""

    to_user_id = fields.Int(required=True)
    process_id = fields.Int(required=True)
    remark = fields.Str(validate=validate.Length(max=500))


class BundleCompleteSchema(Schema):
    """完工确认参数。"""

    remark = fields.Str(validate=validate.Length(max=500))


class BundlePrintSchema(Schema):
    """打印菲参数。"""

    remark = fields.Str(validate=validate.Length(max=500))
