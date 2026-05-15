"""款号价格管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.business.style_price import StylePriceCreateSchema, StylePriceSchema
from app.services import StylePriceService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_price_ns = Namespace('款号价格管理-style-prices', description='款号价格管理')

common = get_common_models(style_price_ns)
base_response = common['base_response']
unauthorized_response = common['unauthorized_response']
error_response = common['error_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

style_price_query_parser = page_parser.copy()
style_price_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号 ID')
style_price_query_parser.add_argument(
    'price_type',
    type=str,
    location='args',
    help='价格类型',
    choices=['customer', 'internal', 'outsourced', 'button', 'other'],
)

style_price_item_model = style_price_ns.model('StylePriceItem', {
    'id': fields.Integer(description='价格记录ID'),
    'style_id': fields.Integer(description='款号ID'),
    'price_type': fields.String(description='价格类型'),
    'price_type_label': fields.String(description='价格类型名称'),
    'price': fields.Float(description='价格'),
    'effective_date': fields.String(description='生效日期'),
    'remark': fields.String(description='备注'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_price_list_data = build_page_data_model(style_price_ns, 'StylePriceListData', style_price_item_model, items_description='价格列表')
style_price_list_response = build_page_response_model(style_price_ns, 'StylePriceListResponse', base_response, style_price_list_data, '价格分页数据')
style_price_item_response = style_price_ns.clone('StylePriceItemResponse', base_response, {
    'data': fields.Nested(style_price_item_model, description='价格详情数据')
})

style_price_create_model = style_price_ns.model('StylePriceCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'price_type': fields.String(required=True, description='价格类型', choices=['customer', 'internal', 'outsourced', 'button', 'other'], example='customer'),
    'price': fields.Float(required=True, description='价格', example=12.5),
    'effective_date': fields.String(required=True, description='生效日期', example='2026-05-15'),
    'remark': fields.String(description='备注', example='首单报价'),
})

style_price_schema = StylePriceSchema()
style_price_create_schema = StylePriceCreateSchema()


@style_price_ns.route('')
class StylePriceList(Resource):
    @login_required
    @style_price_ns.expect(style_price_query_parser)
    @style_price_ns.response(200, '成功', style_price_list_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询款号价格分页列表。"""
        args = style_price_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        style, error = StylePriceService.check_style_permission(current_factory_id, args['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        result = StylePriceService.get_price_list(style.id, args)
        items = []
        for price in result['items']:
            item = style_price_schema.dump(price)
            items.append(StylePriceService.enrich_with_label(item, price))

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @style_price_ns.expect(style_price_create_model)
    @style_price_ns.response(201, '创建成功', style_price_item_response)
    @style_price_ns.response(400, '参数错误', error_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '款号不存在', error_response)
    def post(self):
        """创建款号价格记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_price_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        _, error = StylePriceService.check_style_permission(current_factory_id, data['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        price = StylePriceService.create_price(data)
        result = style_price_schema.dump(price)
        return ApiResponse.success(StylePriceService.enrich_with_label(result, price), '创建成功', 201)


@style_price_ns.route('/<int:price_id>')
class StylePriceDetail(Resource):
    @login_required
    @style_price_ns.response(200, '成功', style_price_item_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '价格记录不存在', error_response)
    def get(self, price_id):
        """查询款号价格详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        price = StylePriceService.get_price_by_id(price_id)
        if not price:
            return ApiResponse.error('价格记录不存在')

        has_permission, error = StylePriceService.check_price_permission(current_factory_id, price)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = style_price_schema.dump(price)
        return ApiResponse.success(StylePriceService.enrich_with_label(result, price))

    @login_required
    @style_price_ns.response(200, '删除成功', base_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '价格记录不存在', error_response)
    def delete(self, price_id):
        """删除款号价格记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        price = StylePriceService.get_price_by_id(price_id)
        if not price:
            return ApiResponse.error('价格记录不存在')

        has_permission, error = StylePriceService.check_price_permission(current_factory_id, price)
        if not has_permission:
            return ApiResponse.error(error, 403)

        StylePriceService.delete_price(price)
        return ApiResponse.success(message='删除成功')
