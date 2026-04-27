from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.business.style import Style
from app.models.business.style_elastic import StyleElastic
from app.models.base_data.size import Size
from app.utils.response import ApiResponse
from app.schemas.business.style_elastic import StyleElasticSchema, StyleElasticCreateSchema, StyleElasticUpdateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required

style_elastic_ns = Namespace('style-elastics', description='款号橡筋管理')

shared = get_shared_models(style_elastic_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

style_elastic_query_parser = style_elastic_ns.parser()
style_elastic_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_elastic_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_elastic_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_elastic_query_parser.add_argument('size_id', type=int, location='args', help='尺码ID')

style_elastic_item_model = style_elastic_ns.model('StyleElasticItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'size_id': fields.Integer(),
    'size_name': fields.String(),
    'elastic_type': fields.String(),
    'elastic_length': fields.Float(),
    'quantity': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_elastic_list_data = style_elastic_ns.model('StyleElasticListData', {
    'items': fields.List(fields.Nested(style_elastic_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_elastic_list_response = style_elastic_ns.clone('StyleElasticListResponse', base_response, {
    'data': fields.Nested(style_elastic_list_data)
})

style_elastic_item_response = style_elastic_ns.clone('StyleElasticItemResponse', base_response, {
    'data': fields.Nested(style_elastic_item_model)
})

style_elastic_schema = StyleElasticSchema()
style_elastics_schema = StyleElasticSchema(many=True)
style_elastic_create_schema = StyleElasticCreateSchema()
style_elastic_update_schema = StyleElasticUpdateSchema()


def get_size_name(size_id):
    if size_id:
        size = Size.query.filter_by(id=size_id, is_deleted=0).first()
        return size.name if size else None
    return None


@style_elastic_ns.route('')
class StyleElasticList(Resource):
    @login_required
    @style_elastic_ns.expect(style_elastic_query_parser)
    @style_elastic_ns.response(200, '成功', style_elastic_list_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_elastic_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']
        page = args['page']
        page_size = args['page_size']
        size_id = args.get('size_id')

        style = Style.query.filter_by(id=style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        query = StyleElastic.query.filter_by(style_id=style_id, is_deleted=0)

        if size_id:
            query = query.filter_by(size_id=size_id)

        pagination = query.order_by(StyleElastic.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        items = []
        for elastic in pagination.items:
            item = style_elastic_schema.dump(elastic)
            item['size_name'] = get_size_name(elastic.size_id)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticCreate', {
        'style_id': fields.Integer(required=True),
        'size_id': fields.Integer(),
        'elastic_type': fields.String(required=True),
        'elastic_length': fields.Float(required=True),
        'quantity': fields.Integer(default=1),
        'remark': fields.String()
    }))
    @style_elastic_ns.response(201, '创建成功', style_elastic_item_response)
    @style_elastic_ns.response(400, '参数错误', error_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    @style_elastic_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_elastic_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style = Style.query.filter_by(id=data['style_id'], factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        if data.get('size_id'):
            size = Size.query.filter_by(id=data['size_id'], is_deleted=0).first()
            if not size:
                return ApiResponse.error('尺码不存在')

        elastic = StyleElastic(
            style_id=data['style_id'],
            size_id=data.get('size_id'),
            elastic_type=data['elastic_type'],
            elastic_length=data['elastic_length'],
            quantity=data.get('quantity', 1),
            remark=data.get('remark', '')
        )
        elastic.save()

        result = style_elastic_schema.dump(elastic)
        result['size_name'] = get_size_name(elastic.size_id)

        return ApiResponse.success(result, '创建成功', 201)


@style_elastic_ns.route('/<int:elastic_id>')
class StyleElasticDetail(Resource):
    @login_required
    @style_elastic_ns.response(200, '成功', style_elastic_item_response)
    @style_elastic_ns.response(404, '不存在', error_response)
    def get(self, elastic_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        elastic = StyleElastic.query.filter_by(id=elastic_id, is_deleted=0).first()
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')

        style = Style.query.filter_by(id=elastic.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限查看', 403)

        result = style_elastic_schema.dump(elastic)
        result['size_name'] = get_size_name(elastic.size_id)

        return ApiResponse.success(result)

    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticUpdate', {
        'size_id': fields.Integer(),
        'elastic_type': fields.String(),
        'elastic_length': fields.Float(),
        'quantity': fields.Integer(),
        'remark': fields.String()
    }))
    @style_elastic_ns.response(200, '更新成功', style_elastic_item_response)
    @style_elastic_ns.response(404, '不存在', error_response)
    def put(self, elastic_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        elastic = StyleElastic.query.filter_by(id=elastic_id, is_deleted=0).first()
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')

        style = Style.query.filter_by(id=elastic.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限修改', 403)

        try:
            data = style_elastic_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'size_id' in data:
            if data['size_id']:
                size = Size.query.filter_by(id=data['size_id'], is_deleted=0).first()
                if not size:
                    return ApiResponse.error('尺码不存在')
            elastic.size_id = data['size_id']
        if 'elastic_type' in data:
            elastic.elastic_type = data['elastic_type']
        if 'elastic_length' in data:
            elastic.elastic_length = data['elastic_length']
        if 'quantity' in data:
            elastic.quantity = data['quantity']
        if 'remark' in data:
            elastic.remark = data['remark']

        elastic.save()

        result = style_elastic_schema.dump(elastic)
        result['size_name'] = get_size_name(elastic.size_id)

        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_elastic_ns.response(200, '删除成功', base_response)
    @style_elastic_ns.response(404, '不存在', error_response)
    def delete(self, elastic_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        elastic = StyleElastic.query.filter_by(id=elastic_id, is_deleted=0).first()
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')

        style = Style.query.filter_by(id=elastic.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限删除', 403)

        elastic.delete()

        return ApiResponse.success(message='删除成功')
    