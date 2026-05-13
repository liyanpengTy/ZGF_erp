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

order_detail_sku_model = order_ns.model('OrderDetailSku', {
    'id': fields.Integer(),
    'detail_id': fields.Integer(),
    'splice_config': fields.Raw(required=True, description='SKU 配置'),
    'remark': fields.String(),
})

order_detail_item_model = order_ns.model('OrderDetailItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'style_no': fields.String(),
    'style_name': fields.String(),
    'snapshot_splice_data': fields.List(fields.Raw()),
    'snapshot_custom_attributes': fields.Raw(),
    'remark': fields.String(),
    'skus': fields.List(fields.Nested(order_detail_sku_model)),
})

order_item_model = order_ns.model('OrderItem', {
    'id': fields.Integer(),
    'order_no': fields.String(),
    'customer_name': fields.String(),
    'order_date': fields.String(),
    'delivery_date': fields.String(),
    'status': fields.String(),
    'status_label': fields.String(),
    'total_amount': fields.Float(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'details': fields.List(fields.Nested(order_detail_item_model)),
})

order_list_data = order_ns.model('OrderListData', {
    'items': fields.List(fields.Nested(order_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer(),
})

order_list_response = order_ns.clone('OrderListResponse', base_response, {'data': fields.Nested(order_list_data)})
order_item_response = order_ns.clone('OrderItemResponse', base_response, {'data': fields.Nested(order_item_model)})

order_detail_sku_create_model = order_ns.model('OrderDetailSkuCreate', {
    'splice_config': fields.Raw(required=True, description='SKU 配置'),
    'remark': fields.String(),
})

order_detail_create_model = order_ns.model('OrderDetailCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID'),
    'remark': fields.String(description='备注'),
    'skus': fields.List(fields.Nested(order_detail_sku_create_model), required=True, description='SKU 列表'),
})

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
order_create_schema = OrderCreateSchema()
order_update_schema = OrderUpdateSchema()
order_status_update_schema = OrderStatusUpdateSchema()


@order_ns.route('')
class OrderList(Resource):
    @login_required
    @order_ns.expect(order_query_parser)
    @order_ns.response(200, '成功', order_list_response)
    @order_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询当前工厂下的订单列表。"""
        args = order_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = OrderService.get_order_list(current_factory_id, args)
        return ApiResponse.success({
            'items': orders_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @order_ns.expect(order_ns.model('OrderCreate', {
        'customer_id': fields.Integer(description='客户 ID'),
        'customer_name': fields.String(description='客户名称'),
        'order_date': fields.String(required=True, description='订单日期', example='2024-01-01'),
        'delivery_date': fields.String(description='交付日期', example='2024-01-31'),
        'remark': fields.String(description='备注'),
        'details': fields.List(fields.Nested(order_detail_create_model), required=True, description='订单明细'),
    }))
    @order_ns.response(201, '创建成功', order_item_response)
    @order_ns.response(400, '参数错误', error_response)
    def post(self):
        """创建订单并保存订单明细与 SKU 快照。"""
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

        return ApiResponse.success(order_schema.dump(order), '创建成功', 201)


@order_ns.route('/<int:order_id>')
class OrderDetail(Resource):
    @login_required
    @order_ns.response(200, '成功', order_item_response)
    @order_ns.response(404, '不存在', error_response)
    def get(self, order_id):
        """查看单个订单详情。"""
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

        return ApiResponse.success(order_schema.dump(order))

    @login_required
    @order_ns.expect(order_ns.model('OrderUpdate', {
        'customer_id': fields.Integer(description='客户 ID'),
        'customer_name': fields.String(description='客户名称'),
        'delivery_date': fields.String(description='交付日期'),
        'remark': fields.String(description='备注'),
    }))
    @order_ns.response(200, '更新成功', order_item_response)
    def patch(self, order_id):
        """更新订单基础信息，不变更明细结构。"""
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
        return ApiResponse.success(order_schema.dump(order), '更新成功')

    @login_required
    @order_ns.response(200, '删除成功', base_response)
    def delete(self, order_id):
        """删除指定订单。"""
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


@order_ns.route('/<int:order_id>/status')
class OrderStatus(Resource):
    @login_required
    @order_ns.expect(order_ns.model('OrderStatusUpdate', {
        'status': fields.String(
            required=True,
            description='订单状态',
            choices=['pending', 'confirmed', 'processing', 'completed', 'cancelled'],
        ),
    }))
    @order_ns.response(200, '更新成功', order_item_response)
    def post(self, order_id):
        """更新订单状态。"""
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
        return ApiResponse.success(order_schema.dump(order), '状态更新成功')
