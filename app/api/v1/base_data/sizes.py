from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.base_data.size import Size
from app.utils.response import ApiResponse
from app.schemas.base_data.size import SizeSchema, SizeCreateSchema, SizeUpdateSchema
from app.api.v1.shared_models import get_shared_models
from marshmallow import ValidationError
from app.utils.permissions import login_required

size_ns = Namespace('sizes', description='尺码管理')

shared = get_shared_models(size_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

size_query_parser = size_ns.parser()
size_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
size_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
size_query_parser.add_argument('name', type=str, location='args', help='尺码名称')
size_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
size_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])

size_item_model = size_ns.model('SizeItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'code': fields.String(),
    'factory_id': fields.Integer(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

size_list_data = size_ns.model('SizeListData', {
    'items': fields.List(fields.Nested(size_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

size_list_response = size_ns.clone('SizeListResponse', base_response, {
    'data': fields.Nested(size_list_data)
})

size_item_response = size_ns.clone('SizeItemResponse', base_response, {
    'data': fields.Nested(size_item_model)
})

size_schema = SizeSchema()
sizes_schema = SizeSchema(many=True)
size_create_schema = SizeCreateSchema()
size_update_schema = SizeUpdateSchema()


@size_ns.route('')
class SizeList(Resource):
    @login_required
    @size_ns.expect(size_query_parser)
    @size_ns.response(200, '成功', size_list_response)
    @size_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = size_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        name = args.get('name', '')
        status = args.get('status')
        factory_only = args.get('factory_only', 0)

        query = Size.query.filter_by(is_deleted=0)

        if factory_only:
            query = query.filter(Size.factory_id == current_user.factory_id)
        else:
            query = query.filter((Size.factory_id == 0) | (Size.factory_id == current_user.factory_id))

        if name:
            query = query.filter(Size.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Size.sort_order).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': sizes_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @size_ns.expect(size_ns.model('SizeCreate', {
        'name': fields.String(required=True),
        'code': fields.String(required=True),
        'sort_order': fields.Integer(default=0)
    }))
    @size_ns.response(201, '创建成功', size_item_response)
    @size_ns.response(400, '参数错误', error_response)
    @size_ns.response(409, '编码已存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = size_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        existing = Size.query.filter_by(
            factory_id=current_user.factory_id,
            code=data['code'],
            is_deleted=0
        ).first()
        if existing:
            return ApiResponse.error('尺码编码已存在')

        size = Size(
            name=data['name'],
            code=data['code'],
            factory_id=current_user.factory_id,
            sort_order=data.get('sort_order', 0),
            status=1
        )
        size.save()

        return ApiResponse.success(size_schema.dump(size), '创建成功', 201)


@size_ns.route('/<int:size_id>')
class SizeDetail(Resource):
    @login_required
    @size_ns.response(200, '成功', size_item_response)
    @size_ns.response(404, '不存在', error_response)
    def get(self, size_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        size = Size.query.filter_by(id=size_id, is_deleted=0).first()
        if not size:
            return ApiResponse.error('尺码不存在')

        if size.factory_id != 0 and size.factory_id != current_user.factory_id:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(size_schema.dump(size))

    @login_required
    @size_ns.expect(size_ns.model('SizeUpdate', {
        'name': fields.String(),
        'sort_order': fields.Integer(),
        'status': fields.Integer()
    }))
    @size_ns.response(200, '更新成功', size_item_response)
    @size_ns.response(404, '不存在', error_response)
    def put(self, size_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        size = Size.query.filter_by(id=size_id, is_deleted=0).first()
        if not size:
            return ApiResponse.error('尺码不存在')

        if size.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的尺码', 403)

        try:
            data = size_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'name' in data:
            size.name = data['name']
        if 'sort_order' in data:
            size.sort_order = data['sort_order']
        if 'status' in data:
            size.status = data['status']

        size.save()

        return ApiResponse.success(size_schema.dump(size), '更新成功')

    @login_required
    @size_ns.response(200, '删除成功', base_response)
    @size_ns.response(404, '不存在', error_response)
    def delete(self, size_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        size = Size.query.filter_by(id=size_id, is_deleted=0).first()
        if not size:
            return ApiResponse.error('尺码不存在')

        if size.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的尺码', 403)

        size.delete()

        return ApiResponse.success(message='删除成功')
