"""款号价格管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
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
style_price_item_response = style_price_ns.clone('StylePriceItemResponse', base_response, {
    'data': fields.Nested(style_price_item_model, description='价格详情数据'),
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


def build_style_price_access_error(error):
    """根据款号价格访问错误内容推导响应状态码。"""
    return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)


def serialize_style_price(price):
    """序列化款号价格记录并补充价格类型名称。"""
    return StylePriceService.enrich_with_label(style_price_schema.dump(price), price)


def get_accessible_price_style_or_error(style_id, require_write=False):
    """查询当前上下文可访问的款号，用于价格记录读写前校验。"""
    if require_write:
        current_user, current_factory_id, error_response_obj = resolve_write_factory_context()
    else:
        current_user, current_factory_id, error_response_obj = resolve_read_factory_context(
            allow_internal_without_factory=True,
        )
    if error_response_obj:
        return None, None, None, error_response_obj

    style, error = StylePriceService.check_style_permission(current_user, current_factory_id, style_id)
    if error:
        return None, None, None, build_style_price_access_error(error)
    return current_user, current_factory_id, style, None


def get_accessible_price_or_error(price_id, require_write=False):
    """查询当前上下文可访问的价格记录。"""
    if require_write:
        current_user, current_factory_id, error_response_obj = resolve_write_factory_context()
    else:
        current_user, current_factory_id, error_response_obj = resolve_read_factory_context(
            allow_internal_without_factory=True,
        )
    if error_response_obj:
        return None, None, None, error_response_obj

    price = StylePriceService.get_price_by_id(price_id)
    if not price:
        return None, None, None, ApiResponse.error('价格记录不存在', 404)

    has_permission, error = StylePriceService.check_price_permission(current_user, current_factory_id, price)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, price, None


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
        return ApiResponse.success_page_result(result, [serialize_style_price(price) for price in result['items']])

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
        _, _, _, error_response_data = get_accessible_price_style_or_error(
            (request.get_json() or {}).get('style_id'),
            require_write=True,
        ) if (request.get_json() or {}).get('style_id') else (None, None, None, None)

        try:
            data = style_price_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

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
