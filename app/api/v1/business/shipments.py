"""出货单管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_claims, get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_with_date_parser
from app.schemas.business.shipment import ShipmentCancelSchema, ShipmentCreateSchema, ShipmentSchema
from app.services import ShipmentService
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

shipment_query_parser = page_with_date_parser.copy()
shipment_query_parser.add_argument('shipment_no', type=str, location='args', help='出货单号')
shipment_query_parser.add_argument('order_no', type=str, location='args', help='订单号')
shipment_query_parser.add_argument('customer_name', type=str, location='args', help='客户名称')
shipment_query_parser.add_argument('status', type=str, location='args', help='出货单状态', choices=['created', 'cancelled'])

shipment_item_model = shipment_ns.model('ShipmentItemView', {
    'id': fields.Integer(description='出货明细ID', example=1),
    'shipment_id': fields.Integer(description='出货单ID', example=1),
    'order_detail_id': fields.Integer(description='订单明细ID', example=16),
    'order_detail_sku_id': fields.Integer(description='订单SKU ID', example=119),
    'style_id': fields.Integer(description='款号ID', example=16),
    'style_no': fields.String(description='款号', example='2235#'),
    'style_name': fields.String(description='款号名称', allow_null=True),
    'color_id': fields.Integer(description='颜色ID', allow_null=True),
    'color_name': fields.String(description='颜色名称', allow_null=True),
    'size_id': fields.Integer(description='尺码ID', allow_null=True),
    'size_name': fields.String(description='尺码名称', allow_null=True),
    'quantity': fields.Integer(description='出货数量', example=20),
    'remark': fields.String(description='备注', allow_null=True),
})

shipment_item_create_model = shipment_ns.model('ShipmentItemCreate', {
    'order_detail_sku_id': fields.Integer(required=True, description='订单SKU ID', example=119),
    'quantity': fields.Integer(required=True, description='本次出货数量', example=20),
    'remark': fields.String(description='备注', example='首批出货'),
})

shipment_model = shipment_ns.model('ShipmentView', {
    'id': fields.Integer(description='出货单ID', example=1),
    'shipment_no': fields.String(description='出货单号', example='SHP1202605160001'),
    'factory_id': fields.Integer(description='工厂ID', example=1),
    'order_id': fields.Integer(description='订单ID', example=16),
    'order_no': fields.String(description='订单号', example='DEMO-ORDER-002'),
    'customer_id': fields.Integer(description='客户ID', allow_null=True),
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
    'order_id': fields.Integer(required=True, description='订单ID', example=16),
    'ship_date': fields.String(required=True, description='出货日期', example='2026-05-16'),
    'remark': fields.String(description='备注', example='第一批出货'),
    'items': fields.List(fields.Nested(shipment_item_create_model), required=True, description='出货明细'),
})

shipment_cancel_model = shipment_ns.model('ShipmentCancel', {
    'remark': fields.String(description='作废备注', example='录入错误，重新开单'),
})

shipment_list_statistics_model = shipment_ns.model('ShipmentListStatistics', {
    'shipment_count': fields.Integer(description='当前页出货单数量', example=3),
    'total_quantity': fields.Integer(description='当前页总出货数量', example=120),
    'status_totals': fields.List(fields.Raw, description='按状态汇总'),
    'customer_totals': fields.List(fields.Raw, description='按客户汇总'),
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
shipment_list_response = build_page_response_model(shipment_ns, 'ShipmentListResponse', base_response, shipment_list_data, '出货单分页数据')
shipment_item_response = shipment_ns.clone('ShipmentItemResponse', base_response, {
    'data': fields.Nested(shipment_model, description='出货单详情'),
})

shipment_schema = ShipmentSchema()
shipments_schema = ShipmentSchema(many=True)
shipment_create_schema = ShipmentCreateSchema()
shipment_cancel_schema = ShipmentCancelSchema()


def check_shipment_write_permission(current_user):
    """校验当前用户是否具备出货单写权限。"""
    if not current_user:
        return False
    if current_user.is_internal_user:
        return True
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    return relation_type in {'owner', 'employee'}


@shipment_ns.route('')
class ShipmentList(Resource):
    @login_required
    @shipment_ns.expect(shipment_query_parser)
    @shipment_ns.response(200, '成功', shipment_list_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询当前工厂的出货单列表。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在', 401)
        if not current_factory_id:
            return ApiResponse.error('当前缺少工厂上下文，请先切换工厂', 400)

        args = shipment_query_parser.parse_args()
        result = ShipmentService.get_shipment_list(current_factory_id, args)
        return ApiResponse.success({
            'items': shipments_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
            'statistics': ShipmentService.build_shipment_list_statistics(result['items']),
        })

    @login_required
    @shipment_ns.expect(shipment_create_model)
    @shipment_ns.response(201, '创建成功', shipment_item_response)
    @shipment_ns.response(400, '参数错误', error_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """创建订单出货单，并校验各 SKU 不得超出可出货数量。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在', 401)
        if not current_factory_id:
            return ApiResponse.error('当前缺少工厂上下文，请先切换工厂', 400)
        if not check_shipment_write_permission(current_user):
            return ApiResponse.error('当前用户没有创建出货单的权限', 403)

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
    @shipment_ns.response(200, '成功', shipment_item_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(404, '出货单不存在', error_response)
    def get(self, shipment_id):
        """查询指定出货单详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在', 401)
        if not current_factory_id:
            return ApiResponse.error('当前缺少工厂上下文，请先切换工厂', 400)

        shipment = ShipmentService.get_shipment_by_id(shipment_id)
        if not shipment or shipment.factory_id != current_factory_id:
            return ApiResponse.error('出货单不存在', 404)
        return ApiResponse.success(shipment_schema.dump(shipment))


@shipment_ns.route('/<int:shipment_id>/cancel')
class ShipmentCancel(Resource):
    @login_required
    @shipment_ns.expect(shipment_cancel_model)
    @shipment_ns.response(200, '作废成功', shipment_item_response)
    @shipment_ns.response(400, '参数错误', error_response)
    @shipment_ns.response(401, '未登录', unauthorized_response)
    @shipment_ns.response(403, '无权限', forbidden_response)
    @shipment_ns.response(404, '出货单不存在', error_response)
    def post(self, shipment_id):
        """作废指定出货单，使其不再参与订单已出货统计。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在', 401)
        if not current_factory_id:
            return ApiResponse.error('当前缺少工厂上下文，请先切换工厂', 400)
        if not check_shipment_write_permission(current_user):
            return ApiResponse.error('当前用户没有作废出货单的权限', 403)

        shipment = ShipmentService.get_shipment_by_id(shipment_id)
        if not shipment or shipment.factory_id != current_factory_id:
            return ApiResponse.error('出货单不存在', 404)

        try:
            data = shipment_cancel_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        shipment, error = ShipmentService.cancel_shipment(shipment, current_user, data.get('remark', ''))
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(shipment_schema.dump(shipment), '作废成功')
