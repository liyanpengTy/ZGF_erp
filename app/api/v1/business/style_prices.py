"""款号价格管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.business.style_price import StylePriceSchema, StylePriceCreateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, StylePriceService

style_price_ns = Namespace('style-prices', description='款号价格管理')

shared = get_shared_models(style_price_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
style_price_query_parser = style_price_ns.parser()
style_price_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_price_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_price_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_price_query_parser.add_argument('price_type', type=str, location='args', help='价格类型',
                                      choices=['customer', 'internal', 'outsourced', 'button', 'other'])

# ========== 响应模型 ==========
style_price_item_model = style_price_ns.model('StylePriceItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'price_type': fields.String(),
    'price_type_label': fields.String(),
    'price': fields.Float(),
    'effective_date': fields.String(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_price_list_data = style_price_ns.model('StylePriceListData', {
    'items': fields.List(fields.Nested(style_price_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_price_list_response = style_price_ns.clone('StylePriceListResponse', base_response, {
    'data': fields.Nested(style_price_list_data)
})

style_price_item_response = style_price_ns.clone('StylePriceItemResponse', base_response, {
    'data': fields.Nested(style_price_item_model)
})

# ========== Schema 初始化 ==========
style_price_schema = StylePriceSchema()
style_prices_schema = StylePriceSchema(many=True)
style_price_create_schema = StylePriceCreateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@style_price_ns.route('')
class StylePriceList(Resource):
    @login_required
    @style_price_ns.expect(style_price_query_parser)
    @style_price_ns.response(200, '成功', style_price_list_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_price_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']

        # 验证权限
        style, error = StylePriceService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        result = StylePriceService.get_price_list(style_id, args)

        items = []
        for price in result['items']:
            item = style_price_schema.dump(price)
            item = StylePriceService.enrich_with_label(item, price)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @style_price_ns.expect(style_price_ns.model('StylePriceCreate', {
        'style_id': fields.Integer(required=True, description='款号ID'),
        'price_type': fields.String(required=True, description='价格类型',
                                    choices=['customer', 'internal', 'outsourced', 'button', 'other']),
        'price': fields.Float(required=True, description='价格'),
        'effective_date': fields.String(required=True, description='生效日期', example='2024-01-01'),
        'remark': fields.String(description='备注')
    }))
    @style_price_ns.response(201, '创建成功', style_price_item_response)
    @style_price_ns.response(400, '参数错误', error_response)
    @style_price_ns.response(403, '无权限', error_response)
    @style_price_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_price_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style_id = data.get('style_id')
        if not style_id:
            return ApiResponse.error('请指定款号ID', 400)

        # 验证权限
        style, error = StylePriceService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        price = StylePriceService.create_price(data)

        result = style_price_schema.dump(price)
        result = StylePriceService.enrich_with_label(result, price)

        return ApiResponse.success(result, '创建成功', 201)


@style_price_ns.route('/<int:price_id>')
class StylePriceDetail(Resource):
    @login_required
    @style_price_ns.response(200, '成功', style_price_item_response)
    @style_price_ns.response(404, '不存在', error_response)
    def get(self, price_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        price = StylePriceService.get_price_by_id(price_id)
        if not price:
            return ApiResponse.error('价格记录不存在')

        # 验证权限
        has_permission, error = StylePriceService.check_price_permission(current_user, price)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = style_price_schema.dump(price)
        result = StylePriceService.enrich_with_label(result, price)

        return ApiResponse.success(result)

    @login_required
    @style_price_ns.response(200, '删除成功', base_response)
    @style_price_ns.response(404, '不存在', error_response)
    def delete(self, price_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        price = StylePriceService.get_price_by_id(price_id)
        if not price:
            return ApiResponse.error('价格记录不存在')

        # 验证权限
        has_permission, error = StylePriceService.check_price_permission(current_user, price)
        if not has_permission:
            return ApiResponse.error(error, 403)

        StylePriceService.delete_price(price)

        return ApiResponse.success(message='删除成功')
