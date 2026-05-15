"""裁床报工相关序列化器。"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

from app.schemas.business.bundle import ProductionBundleSchema


class CuttingReportBundleCreateSchema(Schema):
    """裁床报工时生成菲的明细参数。"""

    bed_no = fields.Int(load_default=1)
    bundle_quantity = fields.Int(required=True)
    priority = fields.Str(load_default='normal', validate=validate.OneOf(['normal', 'urgent', 'top']))
    remark = fields.Str(validate=validate.Length(max=500))


class CuttingReportCreateSchema(Schema):
    """创建裁床报工参数。"""

    order_detail_sku_id = fields.Int(required=True)
    cut_date = fields.Str(required=True, validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2}$'))
    cut_quantity = fields.Int(required=True)
    template_id = fields.Int(allow_none=True)
    remark = fields.Str(validate=validate.Length(max=500))
    bundles = fields.List(fields.Nested(CuttingReportBundleCreateSchema), load_default=list)

    @validates_schema
    def validate_payload(self, data, **kwargs):
        """校验裁床数量和菲拆分数量必须为正数。"""
        cut_quantity = data.get('cut_quantity', 0)
        if cut_quantity <= 0:
            raise ValidationError('实裁数量必须大于 0', field_name='cut_quantity')

        for index, item in enumerate(data.get('bundles') or [], start=1):
            if item.get('bed_no', 0) <= 0:
                raise ValidationError(f'第 {index} 个菲的床号必须大于 0', field_name='bundles')
            if item.get('bundle_quantity', 0) <= 0:
                raise ValidationError(f'第 {index} 个菲的数量必须大于 0', field_name='bundles')


class WorkCuttingReportSchema(Schema):
    """裁床报工序列化器。"""

    id = fields.Int()
    factory_id = fields.Int()
    template_id = fields.Int(allow_none=True)
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
    report_user_id = fields.Int()
    report_user_name = fields.Method('get_report_user_name')
    cut_batch_no = fields.Int()
    cut_date = fields.Date(format='%Y-%m-%d')
    cut_quantity = fields.Int()
    bundle_count = fields.Int()
    status = fields.Str()
    status_label = fields.Str()
    remark = fields.Str(allow_none=True)
    create_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    update_time = fields.DateTime(format='%Y-%m-%d %H:%M:%S')
    bundles = fields.List(fields.Nested(ProductionBundleSchema))

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

    def get_report_user_name(self, obj):
        """返回报工人名称。"""
        return obj.report_user.nickname if obj.report_user else None
