from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.business.style import Style
from app.models.business.style_price import StylePrice
from app.utils.response import ApiResponse
from app.schemas.business.style_price import StylePriceSchema, StylePriceCreateSchema
from app.api.v1.shared_models import get_shared_models
from marshmallow import ValidationError
from datetime import datetime
from app.utils.permissions import login_required

style_price_ns = Namespace('style-prices', description='款号价格管理')

shared = get_shared_models(style_price_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

style_price_query_parser = style_price_ns.parser()
style_price_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_price_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_price_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_price_query_parser.add_argument('price_type', type=str, location='args', help='价格类型',
                                      choices=['customer', 'internal', 'outsourced', 'button', 'other'])

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

price_type_labels = {
    'customer': '客户价',
    'internal': '工厂内部价',
    'outsourced': '外发价',
    'button': '钉扣价',
    'other': '其他'
}

style_price_schema = StylePriceSchema()
style_prices_schema = StylePriceSchema(many=True)
style_price_create_schema = StylePriceCreateSchema()


@style_price_ns.route('')
class StylePriceList(Resource):
    @login_required
    @style_price_ns.expect(style_price_query_parser)
    @style_price_ns.response(200, '成功', style_price_list_response)
    @style_price_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_price_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']
        page = args['page']
        page_size = args['page_size']
        price_type = args.get('price_type')

        style = Style.query.filter_by(id=style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        query = StylePrice.query.filter_by(style_id=style_id, is_deleted=0)

        if price_type:
            query = query.filter_by(price_type=price_type)

        pagination = query.order_by(StylePrice.effective_date.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        items = []
        for price in pagination.items:
            item = style_price_schema.dump(price)
            item['price_type_label'] = price_type_labels.get(price.price_type, price.price_type)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @style_price_ns.expect(style_price_ns.model('StylePriceCreate', {
        'price_type': fields.String(required=True),
        'price': fields.Float(required=True),
        'effective_date': fields.String(required=True),
        'remark': fields.String()
    }))
    @style_price_ns.response(201, '创建成功', style_price_item_response)
    @style_price_ns.response(400, '参数错误', error_response)
    @style_price_ns.response(403, '无权限', forbidden_response)
    @style_price_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_price_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style_id = data.get('style_id')
        if not style_id:
            return ApiResponse.error('请指定款号ID', 400)

        style = Style.query.filter_by(id=style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        price = StylePrice(
            style_id=style_id,
            price_type=data['price_type'],
            price=data['price'],
            effective_date=datetime.strptime(data['effective_date'], '%Y-%m-%d').date(),
            remark=data.get('remark', '')
        )
        price.save()

        result = style_price_schema.dump(price)
        result['price_type_label'] = price_type_labels.get(price.price_type, price.price_type)

        return ApiResponse.success(result, '创建成功', 201)


@style_price_ns.route('/<int:price_id>')
class StylePriceDetail(Resource):
    @login_required
    @style_price_ns.response(200, '成功', style_price_item_response)
    @style_price_ns.response(404, '不存在', error_response)
    def get(self, price_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        price = StylePrice.query.filter_by(id=price_id, is_deleted=0).first()
        if not price:
            return ApiResponse.error('价格记录不存在')

        style = Style.query.filter_by(id=price.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限查看', 403)

        result = style_price_schema.dump(price)
        result['price_type_label'] = price_type_labels.get(price.price_type, price.price_type)

        return ApiResponse.success(result)

    @login_required
    @style_price_ns.response(200, '删除成功', base_response)
    @style_price_ns.response(404, '不存在', error_response)
    def delete(self, price_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        price = StylePrice.query.filter_by(id=price_id, is_deleted=0).first()
        if not price:
            return ApiResponse.error('价格记录不存在')

        style = Style.query.filter_by(id=price.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限删除', 403)

        price.delete()

        return ApiResponse.success(message='删除成功')
    