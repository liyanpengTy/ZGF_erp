"""订单管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_with_date_parser
from app.schemas.business.order import OrderCreateSchema, OrderSchema, OrderStatusUpdateSchema, OrderUpdateSchema
from app.services import OrderService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

order_ns = Namespace('订单管理-orders', description='订单管理')

common = get_common_models(order_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

order_query_parser = page_with_date_parser.copy()
order_query_parser.add_argument('order_no', type=str, location='args', help='订单号')
order_query_parser.add_argument('customer_name', type=str, location='args', help='客户名称')
order_query_parser.add_argument(
    'status',
    type=str,
    location='args',
    help='订单状态',
    choices=['pending', 'confirmed', 'processing', 'completed', 'cancelled'],
)

color_size_values_example = {'M': 20, 'L': 20, 'XL': 20, '2XL': 25}
color_size_column_totals_example = {'M': 120, 'L': 100, 'XL': 100, '2XL': 145}
color_size_headers_example = ['颜色', 'M', 'L', 'XL', '2XL', '合计']
color_size_rows_example = [
    {'label': '红色', 'cells': [20, 20, 20, 25], 'total': 85},
    {'label': '黄色', 'cells': [25, 20, 20, 30], 'total': 95},
]
color_size_summary_example = {'label': '合计', 'cells': [120, 100, 100, 145], 'total': 465}

style_splice_item_model = order_ns.model('OrderStyleSpliceItem', {
    'sequence': fields.Integer(description='拼接顺序', example=1),
    'description': fields.String(description='拼接描述', example='红色'),
})

order_sku_splice_config_model = order_ns.model('OrderSkuSpliceConfig', {
    'color_id': fields.Integer(description='颜色ID', example=1),
    'color_name': fields.String(description='颜色名称', example='红色'),
    'size_id': fields.Integer(description='尺码ID', example=1),
    'size_name': fields.String(description='尺码名称', example='M'),
    'quantity': fields.Integer(description='数量', example=20),
    'unit_price': fields.Float(description='单价', example=0),
    'priority': fields.Integer(description='优先级', example=1),
    'tag': fields.String(description='颜色尺码类 SKU 标签，常用于矩阵单据快速识别', example='RED-M'),
    'variant_name': fields.String(description='拼接组合类 SKU 名称，通常由多个节位描述拼接而成', example='红黄绿条纹紫'),
    'splice_data': fields.List(
        fields.Nested(style_splice_item_model),
        description='拼接结构列表；颜色尺码订单通常为空，拼接订单会按节位返回',
        example=[{'sequence': 1, 'description': '红'}, {'sequence': 2, 'description': '黄'}],
    ),
})

order_detail_sku_model = order_ns.model('OrderDetailSku', {
    'id': fields.Integer(description='SKU 记录ID', example=8),
    'detail_id': fields.Integer(description='订单明细ID', example=4),
    'splice_config': fields.Nested(order_sku_splice_config_model, description='SKU 配置对象'),
    'remark': fields.String(description='SKU 备注', example='红色-M 数量 20'),
})

order_detail_item_model = order_ns.model('OrderDetailItem', {
    'id': fields.Integer(description='订单明细ID', example=4),
    'order_id': fields.Integer(description='订单ID', example=4),
    'style_id': fields.Integer(description='款号ID', example=4),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', example='2235#测试款'),
    'snapshot_splice_data': fields.List(fields.Nested(style_splice_item_model), description='款号拼接快照列表'),
    'snapshot_custom_attributes': fields.Raw(
        description='款号自定义属性快照对象，键为属性名，值为字符串、数字、布尔等标量',
        example={'unit': '件'},
    ),
    'remark': fields.String(description='明细备注', example='2235# 颜色尺码矩阵订单'),
    'skus': fields.List(fields.Nested(order_detail_sku_model), description='SKU 列表'),
})

order_item_model = order_ns.model('OrderItem', {
    'id': fields.Integer(description='订单ID', example=4),
    'order_no': fields.String(description='订单号', example='ORD1202605140002'),
    'factory_id': fields.Integer(description='所属工厂ID', example=1),
    'customer_id': fields.Integer(description='客户ID', example=4),
    'customer_name': fields.String(description='客户名称', example='工厂客户'),
    'order_date': fields.String(description='订单日期', example='2026-05-14'),
    'delivery_date': fields.String(description='交期', example='2026-05-22'),
    'status': fields.String(description='订单状态', example='pending'),
    'status_label': fields.String(description='订单状态名称', example='待确认'),
    'total_amount': fields.Float(description='订单总金额', example=0),
    'remark': fields.String(description='订单备注', example='测试数据-订单2-2235#'),
    'create_time': fields.String(description='创建时间', example='2026-05-14 23:23:35'),
    'update_time': fields.String(description='更新时间', example='2026-05-14 23:23:35'),
    'details': fields.List(fields.Nested(order_detail_item_model), description='订单明细列表'),
})

dimension_total_item_model = order_ns.model('OrderDimensionTotalItem', {
    'name': fields.String(description='维度名称', example='红色'),
    'quantity': fields.Integer(description='汇总件数', example=85),
})

statistics_table_row_model = order_ns.model('OrderStatisticsTableRow', {
    'label': fields.String(description='行标题', example='红色'),
    'cells': fields.List(
        fields.Raw,
        description='按 headers 顺序返回的单元格值列表，可包含数量值或节位文本',
        example=[20, 20, 20, 25],
    ),
    'total': fields.Integer(description='当前行合计', example=85),
})

statistics_table_summary_model = order_ns.model('OrderStatisticsTableSummary', {
    'label': fields.String(description='汇总行标题', example='合计'),
    'cells': fields.List(
        fields.Raw,
        description='按 headers 顺序返回的合计单元格值列表，可包含数量值或节位文本',
        example=[120, 100, 100, 145],
    ),
    'total': fields.Integer(description='汇总行合计', example=465),
})

statistics_table_model = order_ns.model('OrderStatisticsTable', {
    'key': fields.String(description='表格标识', example='color_size_matrix'),
    'title': fields.String(description='表格标题', example='颜色尺码统计'),
    'headers': fields.List(fields.String, description='表头列表', example=color_size_headers_example),
    'rows': fields.List(fields.Nested(statistics_table_row_model), description='表格行列表', example=color_size_rows_example),
    'summary_row': fields.Nested(statistics_table_summary_model, description='合计行', example=color_size_summary_example),
})

color_size_matrix_row_model = order_ns.model('OrderColorSizeMatrixRow', {
    'name': fields.String(description='颜色名称', example='红色'),
    'values': fields.Raw(
        description='动态尺码键到数量的映射对象，键来自 columns 中的尺码名称',
        example=color_size_values_example,
    ),
    'total': fields.Integer(description='当前颜色合计', example=85),
})

color_size_matrix_model = order_ns.model('OrderColorSizeMatrix', {
    'columns': fields.List(fields.String, description='尺码列列表', example=['M', 'L', 'XL', '2XL']),
    'rows': fields.List(fields.Nested(color_size_matrix_row_model), description='颜色矩阵行列表'),
    'column_totals': fields.Raw(
        description='动态尺码键到列合计数量的映射对象，键来自 columns 中的尺码名称',
        example=color_size_column_totals_example,
    ),
    'grand_total': fields.Integer(description='矩阵总件数', example=465),
    'table_headers': fields.List(fields.String, description='可直接渲染的表头', example=color_size_headers_example),
    'table_rows': fields.List(fields.Nested(statistics_table_row_model), description='可直接渲染的表格行', example=color_size_rows_example),
    'summary_row': fields.Nested(statistics_table_summary_model, description='可直接渲染的合计行', example=color_size_summary_example),
})

splice_section_value_model = order_ns.model('OrderSpliceSectionValue', {
    'name': fields.String(description='节位值名称', example='绿，条纹'),
    'quantity': fields.Integer(description='对应件数', example=30),
})

splice_section_model = order_ns.model('OrderSpliceSectionStatistics', {
    'sequence': fields.Integer(description='节位顺序', example=3),
    'values': fields.List(fields.Nested(splice_section_value_model), description='当前节位的值汇总'),
    'total': fields.Integer(description='当前节位总件数', example=70),
})

splice_item_table_row_model = order_ns.model('OrderSpliceItemTableRow', {
    'remark': fields.String(description='组合备注', example='组合一 30 件'),
    'cells': fields.List(fields.String, description='拼接组合单元格列表', example=['红', '黄', '绿，条纹', '紫']),
    'total': fields.Integer(description='当前组合件数', example=30),
})

splice_item_table_model = order_ns.model('OrderSpliceItemTable', {
    'headers': fields.List(fields.String, description='拼接表头列表', example=['第一节', '第二节', '第三节', '第四节', '数量']),
    'rows': fields.List(fields.Nested(splice_item_table_row_model), description='拼接组合行列表'),
    'summary_row': fields.Nested(
        statistics_table_summary_model,
        description='拼接组合合计行',
        example={'label': '合计', 'cells': ['', '', '', ''], 'total': 70},
    ),
})

detail_statistics_model = order_ns.model('OrderDetailStatistics', {
    'sku_count': fields.Integer(description='SKU 行数', example=20),
    'total_quantity': fields.Integer(description='明细总件数', example=465),
    'color_totals': fields.List(fields.Nested(dimension_total_item_model), description='颜色汇总'),
    'size_totals': fields.List(fields.Nested(dimension_total_item_model), description='尺码汇总'),
    'color_size_matrix': fields.Nested(color_size_matrix_model, allow_null=True, description='颜色尺码矩阵'),
    'splice_sections': fields.List(fields.Nested(splice_section_model), description='拼接节位统计'),
    'splice_item_table': fields.Nested(splice_item_table_model, allow_null=True, description='拼接组合表格'),
    'tables': fields.List(fields.Nested(statistics_table_model), description='统一表格协议列表'),
})

order_statistics_detail_item_model = order_ns.model('OrderStatisticsDetailItem', {
    'detail_id': fields.Integer(description='订单明细ID', example=4),
    'style_id': fields.Integer(description='款号ID', example=4),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', example='2235#测试款'),
    'sku_count': fields.Integer(description='SKU 行数', example=20),
    'total_quantity': fields.Integer(description='当前明细总件数', example=465),
})

order_statistics_summary_model = order_ns.model('OrderStatisticsSummary', {
    'detail_count': fields.Integer(description='明细数', example=1),
    'sku_count': fields.Integer(description='SKU 行数', example=20),
    'total_quantity': fields.Integer(description='订单总件数', example=465),
    'details': fields.List(fields.Nested(order_statistics_detail_item_model), description='明细汇总列表'),
})

order_statistics_detail_response_model = order_ns.model('OrderStatisticsDetailResponse', {
    'detail_id': fields.Integer(description='订单明细ID', example=4),
    'style_id': fields.Integer(description='款号ID', example=4),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', example='2235#测试款'),
    'remark': fields.String(description='明细备注', example='2235# 颜色尺码矩阵订单'),
    'statistics': fields.Nested(detail_statistics_model, description='明细统计'),
})

order_statistics_data_model = order_ns.model('OrderStatisticsData', {
    'order_id': fields.Integer(description='订单ID', example=4),
    'order_no': fields.String(description='订单号', example='ORD1202605140002'),
    'customer_id': fields.Integer(description='客户ID', example=4),
    'customer_name': fields.String(description='客户名称', example='工厂客户'),
    'order_date': fields.String(description='订单日期', example='2026-05-14'),
    'delivery_date': fields.String(description='交期', example='2026-05-22'),
    'status': fields.String(description='订单状态', example='pending'),
    'remark': fields.String(description='订单备注', example='测试数据-订单2-2235#'),
    'statistics': fields.Nested(order_statistics_summary_model, description='订单级统计'),
    'details': fields.List(fields.Nested(order_statistics_detail_response_model), description='订单明细统计列表'),
})

order_list_statistics_model = order_ns.model('OrderListStatistics', {
    'order_count': fields.Integer(description='当前页订单数', example=3),
    'detail_count': fields.Integer(description='当前页明细数', example=3),
    'sku_count': fields.Integer(description='当前页 SKU 行数', example=23),
    'total_quantity': fields.Integer(description='当前页总件数', example=655),
    'status_totals': fields.List(fields.Nested(dimension_total_item_model), description='状态汇总'),
    'customer_totals': fields.List(fields.Nested(dimension_total_item_model), description='客户汇总'),
    'delivery_date_totals': fields.List(fields.Nested(dimension_total_item_model), description='交期汇总'),
})

order_list_data = build_page_data_model(order_ns, 'OrderListData', order_item_model, extra_fields={
    'statistics': fields.Nested(
        order_list_statistics_model,
        description='订单列表级统计，包含当前页订单数、明细数、SKU 数、总件数以及状态、客户、交期汇总',
    ),
}, items_description='订单列表')

order_list_response = build_page_response_model(order_ns, 'OrderListResponse', base_response, order_list_data, '订单分页数据')
order_item_response = order_ns.clone('OrderItemResponse', base_response, {
    'data': fields.Nested(order_item_model, description='订单详情数据')
})
order_statistics_response = order_ns.clone('OrderStatisticsResponse', base_response, {
    'data': fields.Nested(order_statistics_data_model, description='订单统计数据')
})

order_production_sku_item_model = order_ns.model('OrderProductionSkuItem', {
    'order_detail_sku_id': fields.Integer(description='订单SKU ID', example=119),
    'sku_name': fields.String(description='SKU 展示名称', example='红色-2XL'),
    'color_id': fields.Integer(description='颜色ID', allow_null=True),
    'color_name': fields.String(description='颜色名称', allow_null=True),
    'size_id': fields.Integer(description='尺码ID', allow_null=True),
    'size_name': fields.String(description='尺码名称', allow_null=True),
    'ordered_quantity': fields.Integer(description='下单数量', example=25),
    'cut_quantity': fields.Integer(description='实裁数量', example=20),
    'bundle_quantity': fields.Integer(description='已生成菲数量', example=20),
    'issued_quantity': fields.Integer(description='累计领货数量', example=20),
    'returned_quantity': fields.Integer(description='累计交货数量', example=8),
    'in_hand_quantity': fields.Integer(description='当前在手数量', example=12),
    'completed_quantity': fields.Integer(description='已完工数量', example=0),
    'shipped_quantity': fields.Integer(description='已出货数量', example=0),
    'cutting_report_count': fields.Integer(description='裁床报工次数', example=1),
    'bundle_count': fields.Integer(description='菲数量', example=1),
})

order_production_detail_item_model = order_ns.model('OrderProductionDetailItem', {
    'detail_id': fields.Integer(description='订单明细ID', example=16),
    'style_id': fields.Integer(description='款号ID', example=16),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', example='2235#测试款'),
    'ordered_quantity': fields.Integer(description='下单数量', example=25),
    'cut_quantity': fields.Integer(description='实裁数量', example=20),
    'bundle_quantity': fields.Integer(description='已生成菲数量', example=20),
    'issued_quantity': fields.Integer(description='累计领货数量', example=20),
    'returned_quantity': fields.Integer(description='累计交货数量', example=8),
    'in_hand_quantity': fields.Integer(description='当前在手数量', example=12),
    'completed_quantity': fields.Integer(description='已完工数量', example=0),
    'shipped_quantity': fields.Integer(description='已出货数量', example=0),
    'cutting_report_count': fields.Integer(description='裁床报工次数', example=1),
    'bundle_count': fields.Integer(description='菲数量', example=1),
    'sku_items': fields.List(fields.Nested(order_production_sku_item_model), description='SKU 生产统计列表'),
})

order_production_summary_model = order_ns.model('OrderProductionSummary', {
    'detail_count': fields.Integer(description='明细数', example=1),
    'sku_count': fields.Integer(description='SKU 数', example=1),
    'ordered_quantity': fields.Integer(description='下单总数', example=25),
    'cut_quantity': fields.Integer(description='实裁总数', example=20),
    'bundle_quantity': fields.Integer(description='生成菲总数', example=20),
    'issued_quantity': fields.Integer(description='累计领货总数', example=20),
    'returned_quantity': fields.Integer(description='累计交货总数', example=8),
    'in_hand_quantity': fields.Integer(description='当前在手总数', example=12),
    'completed_quantity': fields.Integer(description='已完工总数', example=0),
    'shipped_quantity': fields.Integer(description='已出货总数', example=0),
    'cutting_report_count': fields.Integer(description='裁床报工次数', example=1),
    'bundle_count': fields.Integer(description='菲总数', example=1),
})

order_production_statistics_data_model = order_ns.model('OrderProductionStatisticsData', {
    'order_id': fields.Integer(description='订单ID', example=16),
    'order_no': fields.String(description='订单号', example='DEMO-ORDER-002'),
    'customer_id': fields.Integer(description='客户ID', allow_null=True),
    'customer_name': fields.String(description='客户名称', allow_null=True),
    'order_date': fields.String(description='订单日期', example='2026-05-16'),
    'delivery_date': fields.String(description='交期', example='2026-05-24'),
    'status': fields.String(description='订单状态', example='pending'),
    'remark': fields.String(description='订单备注', allow_null=True),
    'summary': fields.Nested(order_production_summary_model, description='订单生产汇总'),
    'details': fields.List(fields.Nested(order_production_detail_item_model), description='订单明细生产统计列表'),
})

order_production_statistics_response = order_ns.clone('OrderProductionStatisticsResponse', base_response, {
    'data': fields.Nested(order_production_statistics_data_model, description='订单生产统计数据')
})

order_shipment_availability_sku_item_model = order_ns.model('OrderShipmentAvailabilitySkuItem', {
    'order_detail_sku_id': fields.Integer(description='订单SKU ID', example=119),
    'sku_name': fields.String(description='SKU 展示名称', example='红色-2XL'),
    'color_id': fields.Integer(description='颜色ID', allow_null=True),
    'color_name': fields.String(description='颜色名称', allow_null=True),
    'size_id': fields.Integer(description='尺码ID', allow_null=True),
    'size_name': fields.String(description='尺码名称', allow_null=True),
    'ordered_quantity': fields.Integer(description='下单数量', example=25),
    'completed_quantity': fields.Integer(description='已完工数量', example=20),
    'shipped_quantity': fields.Integer(description='已出货数量', example=8),
    'available_quantity': fields.Integer(description='可出货数量', example=12),
})

order_shipment_availability_detail_item_model = order_ns.model('OrderShipmentAvailabilityDetailItem', {
    'detail_id': fields.Integer(description='订单明细ID', example=16),
    'style_id': fields.Integer(description='款号ID', example=16),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', allow_null=True),
    'ordered_quantity': fields.Integer(description='下单数量', example=25),
    'completed_quantity': fields.Integer(description='已完工数量', example=20),
    'shipped_quantity': fields.Integer(description='已出货数量', example=8),
    'available_quantity': fields.Integer(description='可出货数量', example=12),
    'sku_items': fields.List(fields.Nested(order_shipment_availability_sku_item_model), description='SKU 可出货明细列表'),
})

order_shipment_availability_summary_model = order_ns.model('OrderShipmentAvailabilitySummary', {
    'detail_count': fields.Integer(description='明细数', example=1),
    'sku_count': fields.Integer(description='SKU 数', example=1),
    'ordered_quantity': fields.Integer(description='下单总数', example=25),
    'completed_quantity': fields.Integer(description='已完工总数', example=20),
    'shipped_quantity': fields.Integer(description='已出货总数', example=8),
    'available_quantity': fields.Integer(description='可出货总数', example=12),
})

order_shipment_availability_data_model = order_ns.model('OrderShipmentAvailabilityData', {
    'order_id': fields.Integer(description='订单ID', example=16),
    'order_no': fields.String(description='订单号', example='DEMO-ORDER-002'),
    'customer_id': fields.Integer(description='客户ID', allow_null=True),
    'customer_name': fields.String(description='客户名称', allow_null=True),
    'order_date': fields.String(description='订单日期', example='2026-05-16'),
    'delivery_date': fields.String(description='交期', example='2026-05-24'),
    'status': fields.String(description='订单状态', example='pending'),
    'remark': fields.String(description='订单备注', allow_null=True),
    'summary': fields.Nested(order_shipment_availability_summary_model, description='订单可出货汇总'),
    'details': fields.List(fields.Nested(order_shipment_availability_detail_item_model), description='订单明细可出货统计列表'),
})

order_shipment_availability_response = order_ns.clone('OrderShipmentAvailabilityResponse', base_response, {
    'data': fields.Nested(order_shipment_availability_data_model, description='订单可出货统计数据')
})

order_detail_sku_create_model = order_ns.model('OrderDetailSkuCreate', {
    'splice_config': fields.Nested(order_sku_splice_config_model, required=True, description='SKU 配置对象'),
    'remark': fields.String(description='SKU 备注', example='首单'),
})

order_detail_create_model = order_ns.model('OrderDetailCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'remark': fields.String(description='备注', example='均码订单'),
    'skus': fields.List(fields.Nested(order_detail_sku_create_model), required=True, description='SKU 列表'),
})

order_create_model = order_ns.model('OrderCreate', {
    'customer_id': fields.Integer(description='客户 ID', example=2),
    'customer_name': fields.String(description='客户名称', example='factory_customer'),
    'order_date': fields.String(required=True, description='订单日期', example='2026-05-15'),
    'delivery_date': fields.String(description='交付日期', example='2026-05-31'),
    'remark': fields.String(description='备注', example='测试订单'),
    'details': fields.List(fields.Nested(order_detail_create_model), required=True, description='订单明细'),
})

order_update_model = order_ns.model('OrderUpdate', {
    'customer_id': fields.Integer(description='客户 ID', example=2),
    'customer_name': fields.String(description='客户名称', example='factory_customer'),
    'delivery_date': fields.String(description='交付日期', example='2026-05-31'),
    'remark': fields.String(description='备注', example='更新备注'),
})

order_status_update_model = order_ns.model('OrderStatusUpdate', {
    'status': fields.String(required=True, description='订单状态', choices=['pending', 'confirmed', 'processing', 'completed', 'cancelled'], example='confirmed'),
})

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
order_create_schema = OrderCreateSchema()
order_update_schema = OrderUpdateSchema()
order_status_update_schema = OrderStatusUpdateSchema()


def serialize_order(order):
    """序列化订单详情，不附带统计字段。"""
    data = order_schema.dump(order)
    return data


def serialize_orders(orders):
    """批量序列化订单列表，不附带订单内嵌统计。"""
    return [serialize_order(order) for order in orders]


def serialize_order_statistics(order):
    """序列化独立订单统计结果。"""
    return {
        'order_id': order.id,
        'order_no': order.order_no,
        'customer_id': order.customer_id,
        'customer_name': order.customer_name,
        'order_date': order.order_date.isoformat() if order.order_date else None,
        'delivery_date': order.delivery_date.isoformat() if order.delivery_date else None,
        'status': order.status,
        'remark': order.remark,
        'statistics': OrderService.build_order_statistics(order),
        'details': [
            {
                'detail_id': detail.id,
                'style_id': detail.style_id,
                'style_no': detail.style.style_no if detail.style else None,
                'style_name': detail.style.name if detail.style else None,
                'remark': detail.remark,
                'statistics': OrderService.build_detail_statistics(detail),
            }
            for detail in order.details
        ],
    }


def serialize_order_production_statistics(order):
    """序列化独立订单生产统计结果。"""
    production_statistics = OrderService.build_order_production_statistics(order)
    return {
        'order_id': order.id,
        'order_no': order.order_no,
        'customer_id': order.customer_id,
        'customer_name': order.customer_name,
        'order_date': order.order_date.isoformat() if order.order_date else None,
        'delivery_date': order.delivery_date.isoformat() if order.delivery_date else None,
        'status': order.status,
        'remark': order.remark,
        'summary': production_statistics['summary'],
        'details': production_statistics['details'],
    }


def serialize_order_shipment_availability(order):
    """序列化独立订单可出货统计结果。"""
    shipment_availability = OrderService.build_order_shipment_availability(order)
    return {
        'order_id': order.id,
        'order_no': order.order_no,
        'customer_id': order.customer_id,
        'customer_name': order.customer_name,
        'order_date': order.order_date.isoformat() if order.order_date else None,
        'delivery_date': order.delivery_date.isoformat() if order.delivery_date else None,
        'status': order.status,
        'remark': order.remark,
        'summary': shipment_availability['summary'],
        'details': shipment_availability['details'],
    }


@order_ns.route('')
class OrderList(Resource):
    @login_required
    @order_ns.expect(order_query_parser)
    @order_ns.response(200, '成功', order_list_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询订单分页列表接口。"""
        args = order_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = OrderService.get_order_list(current_factory_id, args)
        return ApiResponse.success({
            'items': serialize_orders(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
            'statistics': OrderService.build_order_list_statistics(result['items']),
        })

    @login_required
    @order_ns.expect(order_create_model)
    @order_ns.response(201, '创建成功', order_item_response)
    @order_ns.response(400, '参数错误', error_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    def post(self):
        """创建订单接口。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = order_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        order, error = OrderService.create_order(current_user, current_factory_id, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_order(order), '创建成功', 201)


@order_ns.route('/<int:order_id>')
class OrderDetail(Resource):
    @login_required
    @order_ns.response(200, '成功', order_item_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def get(self, order_id):
        """查询订单详情接口。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(serialize_order(order))

    @login_required
    @order_ns.expect(order_update_model)
    @order_ns.response(200, '更新成功', order_item_response)
    @order_ns.response(400, '参数错误', error_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def patch(self, order_id):
        """更新订单接口。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = order_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        order = OrderService.update_order(order, data)
        return ApiResponse.success(serialize_order(order), '更新成功')

    @login_required
    @order_ns.response(200, '删除成功', base_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def delete(self, order_id):
        """删除订单接口。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        OrderService.delete_order(order)
        return ApiResponse.success(message='删除成功')


@order_ns.route('/<int:order_id>/statistics')
class OrderStatistics(Resource):
    @login_required
    @order_ns.response(200, '成功', order_statistics_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def get(self, order_id):
        """查询订单统计接口，返回订单级与明细级统计结果。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(serialize_order_statistics(order))


@order_ns.route('/<int:order_id>/status')
class OrderStatus(Resource):
    @login_required
    @order_ns.expect(order_status_update_model)
    @order_ns.response(200, '更新成功', order_item_response)
    @order_ns.response(400, '参数错误', error_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def post(self, order_id):
        """更新订单状态接口。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = order_status_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        order = OrderService.update_order_status(order, data['status'])
        return ApiResponse.success(serialize_order(order), '状态更新成功')


@order_ns.route('/<int:order_id>/production-statistics')
class OrderProductionStatistics(Resource):
    @login_required
    @order_ns.response(200, '成功', order_production_statistics_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def get(self, order_id):
        """查询订单生产统计接口，返回下单、实裁、领货、交货、在手与完工汇总。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(serialize_order_production_statistics(order))


@order_ns.route('/<int:order_id>/shipment-availability')
class OrderShipmentAvailability(Resource):
    @login_required
    @order_ns.response(200, '成功', order_shipment_availability_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    @order_ns.response(403, '无权限', forbidden_response)
    @order_ns.response(404, '订单不存在', error_response)
    def get(self, order_id):
        """查询订单可出货统计接口，返回各 SKU 的已完工、已出货与可出货数量。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        order = OrderService.get_order_by_id(order_id)
        if not order:
            return ApiResponse.error('订单不存在')

        has_permission, error = OrderService.check_permission(current_user, current_factory_id, order)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(serialize_order_shipment_availability(order))
