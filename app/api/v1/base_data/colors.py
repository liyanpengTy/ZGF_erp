"""颜色管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.base_data.color import ColorCreateSchema, ColorSchema, ColorUpdateSchema
from app.services import ColorService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

color_ns = Namespace('颜色管理-colors', description='颜色管理')

common = get_common_models(color_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']

color_query_parser = page_parser.copy()
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
    'update_time': fields.String(),
})

color_list_data = color_ns.model('ColorListData', {
    'items': fields.List(fields.Nested(color_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer(),
})

color_list_response = color_ns.clone('ColorListResponse', base_response, {'data': fields.Nested(color_list_data)})
color_item_response = color_ns.clone('ColorItemResponse', base_response, {'data': fields.Nested(color_item_model)})

color_schema = ColorSchema()
colors_schema = ColorSchema(many=True)
color_create_schema = ColorCreateSchema()
color_update_schema = ColorUpdateSchema()


@color_ns.route('')
class ColorList(Resource):
    @login_required
    @color_ns.expect(color_query_parser)
    @color_ns.response(200, '成功', color_list_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询颜色列表，支持按名称、实际名称和状态筛选。"""
        args = color_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = ColorService.get_color_list(current_user, current_factory_id, args)
        return ApiResponse.success({
            'items': colors_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @color_ns.expect(color_ns.model('ColorCreate', {
        'name': fields.String(required=True, description='颜色名称'),
        'actual_name': fields.String(required=True, description='实际颜色名称'),
        'code': fields.String(required=True, description='颜色编码'),
        'sort_order': fields.Integer(description='排序', default=0),
        'remark': fields.String(description='备注'),
    }))
    @color_ns.response(201, '创建成功', color_item_response)
    def post(self):
        """在当前工厂上下文下创建颜色。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = color_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        color, error = ColorService.create_color(current_user, current_factory_id, data)
        if error:
            return ApiResponse.error(error, 409 if '已存在' in error else 400)

        return ApiResponse.success(color_schema.dump(color), '创建成功', 201)


@color_ns.route('/<int:color_id>')
class ColorDetail(Resource):
    @login_required
    @color_ns.response(200, '成功', color_item_response)
    def get(self, color_id):
        """查看单个颜色详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在')

        has_permission, error = ColorService.check_permission(current_user, current_factory_id, color)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(color_schema.dump(color))

    @login_required
    @color_ns.expect(color_ns.model('ColorUpdate', {
        'name': fields.String(description='颜色名称'),
        'actual_name': fields.String(description='实际颜色名称'),
        'sort_order': fields.Integer(description='排序'),
        'status': fields.Integer(description='状态', choices=[0, 1]),
        'remark': fields.String(description='备注'),
    }))
    @color_ns.response(200, '更新成功', color_item_response)
    def patch(self, color_id):
        """更新当前工厂自有的颜色信息。"""
        current_factory_id = get_current_factory_id()
        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在')
        if color.factory_id != current_factory_id:
            return ApiResponse.error('只能修改自己工厂的颜色', 403)

        try:
            data = color_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        color, error = ColorService.update_color(color, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(color_schema.dump(color), '更新成功')

    @login_required
    @color_ns.response(200, '删除成功', base_response)
    def delete(self, color_id):
        """删除当前工厂自有的颜色。"""
        current_factory_id = get_current_factory_id()
        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在')
        if color.factory_id != current_factory_id:
            return ApiResponse.error('只能删除自己工厂的颜色', 403)
        ColorService.delete_color(color)
        return ApiResponse.success(message='删除成功')
