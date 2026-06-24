"""款号价格管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.api.common.response_helpers import load_json_or_error, success_mapped_page
from app.api.common.serializers import serialize_schema
from app.api.common.style_relation_helpers import (
    build_style_relation_access_error,
    get_accessible_style_or_error,
    get_accessible_style_resource_or_error,
)
from app.constants.permissions import (
    PERM_BUSINESS_STYLE_PRICE_ADD,
    PERM_BUSINESS_STYLE_PRICE_DELETE,
    PERM_BUSINESS_STYLE_PRICE_QUERY,
)
from app.schemas.business.style_price import StylePriceCreateSchema, StylePriceSchema
from app.services import StylePriceService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_price_ns = Namespace('款号价格管理-style-prices', description='款号价格记录查询与维护')

common = get_common_models(style_price_ns)
base_response = common['base_response']
unauthorized_response = common['unauthorized_response']
error_response = common['error_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']
build_item_response_model = common['build_item_response_model']

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
    'id': fields.Integer(description='价格记录 ID'),
    'style_id': fields.Integer(description='款号 ID'),
    'price_type': fields.String(description='价格类型'),
    'price_type_label': fields.String(description='价格类型名称'),
    'price': fields.Float(description='价格'),
    'effective_date': fields.String(description='生效日期'),
    'remark': fields.String(description='备注'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_price_list_data = build_page_data_model(
    style_price_ns,
    'StylePriceListData',
    style_price_item_model,
    items_description='价格列表',
)
style_price_list_response = build_page_response_model(
    style_price_ns,
    'StylePriceListResponse',
    base_response,
    style_price_list_data,
    '价格分页数据',
)
style_price_item_response = build_item_response_model(style_price_ns, 'StylePriceItemResponse', base_response, style_price_item_model, '价格详情数据')

style_price_create_model = style_price_ns.model('StylePriceCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'price_type': fields.String(required=True, description='价格类型', choices=['customer', 'internal', 'outsourced', 'button', 'other'], example='customer'),
    'price': fields.Float(required=True, description='价格', example=12.5),
    'effective_date': fields.String(required=True, description='生效日期', example='2026-05-15'),
    'remark': fields.String(description='备注', example='首单报价'),
})

style_price_schema = StylePriceSchema()
style_price_create_schema = StylePriceCreateSchema()


def serialize_style_price(price):
    """序列化款号价格记录并补充价格类型名称。"""
    return StylePriceService.enrich_with_label(serialize_schema(style_price_schema, price), price)


def get_accessible_price_style_or_error(style_id, require_write=False):
    """查询当前上下文可访问的款号，用于价格记录读写前校验。"""
    return get_accessible_style_or_error(
        style_id,
        StylePriceService.check_style_permission,
        require_write=require_write,
    )


def get_accessible_price_or_error(price_id, require_write=False):
    """查询当前上下文可访问的价格记录。"""
    return get_accessible_style_resource_or_error(
        price_id,
        StylePriceService.get_price_by_id,
        StylePriceService.check_price_permission,
        '价格记录不存在',
        require_write=require_write,
    )


@style_price_ns.route('')
class StylePriceList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PRICE_QUERY)
    @style_price_ns.expect(style_price_query_parser)
    @style_price_ns.response(200, '查询成功', style_price_list_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询款号价格分页列表接口。平台内部用户可不切工厂直接按款号查询。"""
        args = style_price_query_parser.parse_args()
        _, _, style, error_response_data = get_accessible_price_style_or_error(args['style_id'])
        if error_response_data:
            return error_response_data

        result = StylePriceService.get_price_list(style.id, args)
        return success_mapped_page(result, [serialize_style_price(price) for price in result['items']])

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PRICE_ADD)
    @style_price_ns.expect(style_price_create_model)
    @style_price_ns.response(201, '创建成功', style_price_item_response)
    @style_price_ns.response(400, '参数错误', error_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '款号不存在', error_response)
    def post(self):
        """创建款号价格记录接口。写操作仍要求当前工厂上下文。"""
        data, validation_error = load_json_or_error(style_price_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        _, _, _, error_response_data = get_accessible_price_style_or_error(data['style_id'], require_write=True)
        if error_response_data:
            return error_response_data

        price = StylePriceService.create_price(data)
        return ApiResponse.success(serialize_style_price(price), '创建成功', 201)


@style_price_ns.route('/<int:price_id>')
class StylePriceDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PRICE_QUERY)
    @style_price_ns.response(200, '查询成功', style_price_item_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '价格记录不存在', error_response)
    def get(self, price_id):
        """查询款号价格详情接口。平台内部用户可跨工厂查看。"""
        _, _, price, error_response_data = get_accessible_price_or_error(price_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(serialize_style_price(price))

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PRICE_DELETE)
    @style_price_ns.response(200, '删除成功', base_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '价格记录不存在', error_response)
    def delete(self, price_id):
        """删除款号价格记录接口。写操作仍要求当前工厂上下文。"""
        _, _, price, error_response_data = get_accessible_price_or_error(price_id, require_write=True)
        if error_response_data:
            return error_response_data

        StylePriceService.delete_price(price)
        return ApiResponse.success(message='删除成功')
