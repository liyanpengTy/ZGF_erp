from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.base_data.color import Color
from app.utils.response import ApiResponse
from app.schemas.base_data.color import ColorSchema, ColorCreateSchema, ColorUpdateSchema
from app.api.v1.shared_models import get_shared_models
from marshmallow import ValidationError

color_ns = Namespace('colors', description='颜色管理')

shared = get_shared_models(color_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

color_query_parser = color_ns.parser()
color_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
color_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
color_query_parser.add_argument('name', type=str, location='args', help='颜色名称')
color_query_parser.add_argument('actual_name', type=str, location='args', help='实际颜色名称')
color_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
color_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])

color_item_model = color_ns.model('ColorItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'actual_name': fields.String(),
    'code': fields.String(),
    'factory_id': fields.Integer(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

color_list_data = color_ns.model('ColorListData', {
    'items': fields.List(fields.Nested(color_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

color_list_response = color_ns.clone('ColorListResponse', base_response, {
    'data': fields.Nested(color_list_data)
})

color_item_response = color_ns.clone('ColorItemResponse', base_response, {
    'data': fields.Nested(color_item_model)
})

color_schema = ColorSchema()
colors_schema = ColorSchema(many=True)
color_create_schema = ColorCreateSchema()
color_update_schema = ColorUpdateSchema()


@color_ns.route('')
class ColorList(Resource):
    @jwt_required()
    @color_ns.expect(color_query_parser)
    @color_ns.response(200, '成功', color_list_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = color_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        name = args.get('name', '')
        actual_name = args.get('actual_name', '')
        status = args.get('status')
        factory_only = args.get('factory_only', 0)

        query = Color.query.filter_by(is_deleted=0)

        if factory_only:
            query = query.filter(Color.factory_id == current_user.factory_id)
        else:
            query = query.filter((Color.factory_id == 0) | (Color.factory_id == current_user.factory_id))

        if name:
            query = query.filter(Color.name.like(f'%{name}%'))
        if actual_name:
            query = query.filter(Color.actual_name.like(f'%{actual_name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Color.sort_order).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': colors_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @jwt_required()
    @color_ns.expect(color_ns.model('ColorCreate', {
        'name': fields.String(required=True),
        'actual_name': fields.String(required=True),
        'code': fields.String(required=True),
        'sort_order': fields.Integer(default=0),
        'remark': fields.String()
    }))
    @color_ns.response(201, '创建成功', color_item_response)
    @color_ns.response(400, '参数错误', error_response)
    @color_ns.response(409, '编码已存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = color_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        existing = Color.query.filter_by(
            factory_id=current_user.factory_id,
            code=data['code'],
            is_deleted=0
        ).first()
        if existing:
            return ApiResponse.error('颜色编码已存在')

        color = Color(
            name=data['name'],
            actual_name=data['actual_name'],
            code=data['code'],
            factory_id=current_user.factory_id,
            sort_order=data.get('sort_order', 0),
            status=1,
            remark=data.get('remark', '')
        )
        color.save()

        return ApiResponse.success(color_schema.dump(color), '创建成功', 201)


@color_ns.route('/<int:color_id>')
class ColorDetail(Resource):
    @jwt_required()
    @color_ns.response(200, '成功', color_item_response)
    @color_ns.response(404, '不存在', error_response)
    def get(self, color_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        color = Color.query.filter_by(id=color_id, is_deleted=0).first()
        if not color:
            return ApiResponse.error('颜色不存在')

        if color.factory_id != 0 and color.factory_id != current_user.factory_id:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(color_schema.dump(color))

    @jwt_required()
    @color_ns.expect(color_ns.model('ColorUpdate', {
        'name': fields.String(),
        'actual_name': fields.String(),
        'sort_order': fields.Integer(),
        'status': fields.Integer(),
        'remark': fields.String()
    }))
    @color_ns.response(200, '更新成功', color_item_response)
    @color_ns.response(404, '不存在', error_response)
    def put(self, color_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        color = Color.query.filter_by(id=color_id, is_deleted=0).first()
        if not color:
            return ApiResponse.error('颜色不存在')

        if color.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的颜色', 403)

        try:
            data = color_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'name' in data:
            color.name = data['name']
        if 'actual_name' in data:
            color.actual_name = data['actual_name']
        if 'sort_order' in data:
            color.sort_order = data['sort_order']
        if 'status' in data:
            color.status = data['status']
        if 'remark' in data:
            color.remark = data['remark']

        color.save()

        return ApiResponse.success(color_schema.dump(color), '更新成功')

    @jwt_required()
    @color_ns.response(200, '删除成功', base_response)
    @color_ns.response(404, '不存在', error_response)
    def delete(self, color_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        color = Color.query.filter_by(id=color_id, is_deleted=0).first()
        if not color:
            return ApiResponse.error('颜色不存在')

        if color.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的颜色', 403)

        color.delete()

        return ApiResponse.success(message='删除成功')
