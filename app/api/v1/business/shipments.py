"""出货单管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_with_date_parser
from app.constants.permissions import (
    PERM_BUSINESS_SHIPMENT_ADD,
    PERM_BUSINESS_SHIPMENT_CANCEL,
    PERM_BUSINESS_SHIPMENT_QUERY,
)
from app.schemas.business.shipment import ShipmentCancelSchema, ShipmentCreateSchema, ShipmentSchema
from app.services import ShipmentService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

shipment_ns = Namespace('出货单管理-shipments', description='订单出货单创建、查询与作废')

common = get_common_models(shipment_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']
build_named_quantity_model = common['build_named_quantity_model']

shipment_query_parser = page_with_date_parser.copy()
shipment_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID，可选；平台内部用户可按工厂筛选')
shipment_query_parser.add_argument('shipment_no', type=str, location='args', help='出货单号')
shipment_query_parser.add_argument('order_no', type=str, location='args', help='订单号')
shipment_query_parser.add_argument('customer_name', type=str, location='args', help='客户名称')
shipment_query_parser.add_argument(
    'status',
    type=str,
    location='args',
    help='出货单状态',
    choices=['created', 'cancelled'],
)

shipment_item_model = shipment_ns.model('ShipmentItemView', {
    'id': fields.Integer(description='出货明细 ID', example=1),
    'shipment_id': fields.Integer(description='出货单 ID', example=1),
    'order_detail_id': fields.Integer(description='订单明细 ID', example=16),
    'order_detail_sku_id': fields.Integer(description='订单 SKU ID', example=119),
    'style_id': fields.Integer(description='款号 ID', example=16),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', allow_null=True),
    'color_id': fields.Integer(description='颜色 ID', allow_null=True),
    'color_name': fields.String(description='颜色名称', allow_null=True),
    'size_id': fields.Integer(description='尺码 ID', allow_null=True),
    'size_name': fields.String(description='尺码名称', allow_null=True),
    'quantity': fields.Integer(description='出货数量', example=20),
    'remark': fields.String(description='备注', allow_null=True),
})

shipment_item_create_model = shipment_ns.model('ShipmentItemCreate', {
    'order_detail_sku_id': fields.Integer(required=True, description='订单 SKU ID', example=119),
    'quantity': fields.Integer(required=True, description='本次出货数量', example=20),
    'remark': fields.String(description='备注', example='首批出货'),
})

shipment_model = shipment_ns.model('ShipmentView', {
    'id': fields.Integer(description='出货单 ID', example=1),
    'shipment_no': fields.String(description='出货单号', example='SHP1202605160001'),
    'factory_id': fields.Integer(description='工厂 ID', example=1),
    'order_id': fields.Integer(description='订单 ID', example=16),
    'order_no': fields.String(description='订单号', example='DEMO-ORDER-002'),
    'customer_id': fields.Integer(description='客户 ID', allow_null=True),
    'customer_name': fields.String(description='客户名称', allow_null=True),
    'ship_date': fields.String(description='出货日期', example='2026-05-16'),
    'status': fields.String(description='状态编码', example='created'),
    'status_label': fields.String(description='状态名称', example='已出货'),
    'total_quantity': fields.Integer(description='总出货数量', example=40),
    'item_count': fields.Integer(description='明细行数', example=2),
    'remark': fields.String(description='备注', allow_null=True),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
    'items': fields.List(fields.Nested(shipment_item_model), description='出货明细列表'),
})

shipment_create_model = shipment_ns.model('ShipmentCreate', {
    'order_id': fields.Integer(required=True, description='订单 ID', example=16),
    'ship_date': fields.String(required=True, description='出货日期', example='2026-05-16'),
    'remark': fields.String(description='备注', example='第一批出货'),
    'items': fields.List(fields.Nested(shipment_item_create_model), required=True, description='出货明细'),
})

shipment_cancel_model = shipment_ns.model('ShipmentCancel', {
    'remark': fields.String(description='作废备注', example='录入错误，重新开单'),
})

shipment_total_item_model = build_named_quantity_model(
    shipment_ns,
    'ShipmentTotalItem',
    name_description='汇总名称',
    quantity_description='汇总数量',
    name_example='已出货',
    quantity_example=120,
)

shipment_list_statistics_model = shipment_ns.model('ShipmentListStatistics', {
    'shipment_count': fields.Integer(description='当前页出货单数量', example=3),
    'total_quantity': fields.Integer(description='当前页总出货数量', example=120),
    'status_totals': fields.List(fields.Nested(shipment_total_item_model), description='按状态汇总'),
    'customer_totals': fields.List(fields.Nested(shipment_total_item_model), description='按客户汇总'),
})

shipment_list_data = build_page_data_model(
    shipment_ns,
    'ShipmentListData',
    shipment_model,
    extra_fields={
        'statistics': fields.Nested(shipment_list_statistics_model, description='出货单列表统计'),
    },
    items_description='出货单列表',
)
shipment_list_response = build_page_response_model(
    shipment_ns,
    'ShipmentListResponse',
    base_response,
    shipment_list_data,
    '出货单分页数据',
)
shipment_item_response = shipment_ns.clone('ShipmentItemResponse', base_response, {
    'data': fields.Nested(shipment_model, description='出货单详情'),
})

shipment_schema = ShipmentSchema()
shipments_schema = ShipmentSchema(many=True)
shipment_create_schema = ShipmentCreateSchema()
shipment_cancel_schema = ShipmentCancelSchema()


def get_shipment_request_context():
    """获取出货单接口通用的当前用户和工厂上下文。"""
    return resolve_read_factory_context(allow_internal_without_factory=True)


def require_shipment_write_context():
    """校验出货单写操作必须存在工厂上下文。"""
    return resolve_write_factory_context()


def get_accessible_shipment_or_error(shipment_id):
    """查询当前上下文可访问的出货单，不可访问时返回统一错误响应。"""
    current_user, current_factory_id, error_response_data = get_shipment_request_context()
    if error_response_data:
        return None, None, None, error_response_data

    shipment = ShipmentService.get_shipment_by_id(shipment_id)
    if not shipment:
        return None, None, None, ApiResponse.error('出货单不存在', 404)

    has_permission, error = ShipmentService.check_permission(current_user, current_factory_id, shipment)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, shipment, None


def get_writable_shipment_or_error(shipment_id):
    """查询当前工厂下可写入的出货单，不存在或超出数据范围时返回统一错误响应。"""
    current_user, current_factory_id, error_response_data = require_shipment_write_context()
    if error_response_data:
        return None, None, None, error_response_data

    shipment = ShipmentService.get_shipment_by_id(shipment_id)
    if not shipment or shipment.factory_id != current_factory_id:
        return None, None, None, ApiResponse.error('出货单不存在', 404)
    has_permission, error = ShipmentService.check_permission(current_user, current_factory_id, shipment)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, shipment, None


@shipment_ns.route('')
class ShipmentList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_SHIPMENT_QUERY)
    @shipment_ns.expect(shipment_query_parser)
    @shipment_ns.response(200, '查询成功', shipment_list_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询出货单分页列表接口。平台内部用户可直接全局查询，外部用户仍按当前工厂范围查询。"""
        args = shipment_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = resolve_read_factory_context(
            query_factory_id=args.get('factory_id'),
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        result = ShipmentService.get_shipment_list(current_user, current_factory_id, args)
        return ApiResponse.success_page_result(
            result,
            shipments_schema.dump(result['items']),
            extra={'statistics': ShipmentService.build_shipment_list_statistics(result['items'])},
        )

    @login_required
    @button_permission(PERM_BUSINESS_SHIPMENT_ADD)
    @shipment_ns.expect(shipment_create_model)
    @shipment_ns.response(201, '创建成功', shipment_item_response)
    @shipment_ns.response(400, '参数错误', error_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """创建出货单接口。写操作仍要求明确当前工厂上下文，并校验不可超出可出货数量。"""
        current_user, current_factory_id, error_response_data = require_shipment_write_context()
        if error_response_data:
            return error_response_data

        try:
            data = shipment_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        shipment, error = ShipmentService.create_shipment(current_user, current_factory_id, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(shipment_schema.dump(shipment), '创建成功', 201)


@shipment_ns.route('/<int:shipment_id>')
class ShipmentDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_SHIPMENT_QUERY)
    @shipment_ns.response(200, '查询成功', shipment_item_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(403, '无权限', forbidden_response)
    @shipment_ns.response(404, '出货单不存在', error_response)
    def get(self, shipment_id):
        """查询出货单详情接口。平台内部用户可跨工厂查看，外部用户仅可查看当前工厂数据。"""
        _, _, shipment, error_response_data = get_accessible_shipment_or_error(shipment_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(shipment_schema.dump(shipment))


@shipment_ns.route('/<int:shipment_id>/cancel')
class ShipmentCancel(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_SHIPMENT_CANCEL)
    @shipment_ns.expect(shipment_cancel_model)
    @shipment_ns.response(200, '作废成功', shipment_item_response)
    @shipment_ns.response(400, '参数错误', error_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(403, '无权限', forbidden_response)
    @shipment_ns.response(404, '出货单不存在', error_response)
    def post(self, shipment_id):
        """作废出货单接口。写操作仍要求明确当前工厂上下文，并且仅允许作废所属工厂的出货单。"""
        current_user, _, shipment, error_response_data = get_writable_shipment_or_error(shipment_id)
        if error_response_data:
            return error_response_data

        try:
            data = shipment_cancel_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        shipment, error = ShipmentService.cancel_shipment(shipment, current_user, data.get('remark', ''))
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(shipment_schema.dump(shipment), '作废成功')
