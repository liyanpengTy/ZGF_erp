"""颜色管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.base_data.color import ColorSchema, ColorCreateSchema, ColorUpdateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, ColorService

color_ns = Namespace('颜色管理-colors', description='颜色管理')

shared = get_shared_models(color_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
color_query_parser = color_ns.parser()
color_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
color_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
color_query_parser.add_argument('name', type=str, location='args', help='颜色名称')
color_query_parser.add_argument('actual_name', type=str, location='args', help='实际颜色名称')
color_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
color_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])

# ========== 响应模型 ==========
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

# ========== Schema 初始化 ==========
color_schema = ColorSchema()
colors_schema = ColorSchema(many=True)
color_create_schema = ColorCreateSchema()
color_update_schema = ColorUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@color_ns.route('')
class ColorList(Resource):
    @login_required
    @color_ns.expect(color_query_parser)
    @color_ns.response(200, '成功', color_list_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """颜色列表"""
        args = color_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = ColorService.get_color_list(current_user, args)

        return ApiResponse.success({
            'items': colors_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @color_ns.expect(color_ns.model('ColorCreate', {
        'name': fields.String(required=True, description='颜色名称'),
        'actual_name': fields.String(required=True, description='实际颜色名称'),
        'code': fields.String(required=True, description='颜色编码'),
        'sort_order': fields.Integer(description='排序', default=0),
        'remark': fields.String(description='备注')
    }))
    @color_ns.response(201, '创建成功', color_item_response)
    @color_ns.response(400, '参数错误', error_response)
    @color_ns.response(409, '编码已存在', error_response)
    def post(self):
        """创建颜色"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = color_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        color, error = ColorService.create_color(current_user, data)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(color_schema.dump(color), '创建成功', 201)


@color_ns.route('/<int:color_id>')
class ColorDetail(Resource):
    @login_required
    @color_ns.response(200, '成功', color_item_response)
    @color_ns.response(404, '不存在', error_response)
    def get(self, color_id):
        """颜色详情"""
        current_user = get_current_user()

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在')

        has_permission, error = ColorService.check_permission(current_user, color)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(color_schema.dump(color))

    @login_required
    @color_ns.expect(color_ns.model('ColorUpdate', {
        'name': fields.String(description='颜色名称'),
        'actual_name': fields.String(description='实际颜色名称'),
        'sort_order': fields.Integer(description='排序'),
        'status': fields.Integer(description='状态', choices=[0, 1]),
        'remark': fields.String(description='备注')
    }))
    @color_ns.response(200, '更新成功', color_item_response)
    @color_ns.response(404, '不存在', error_response)
    def patch(self, color_id):
        """更新颜色"""
        current_user = get_current_user()

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在')

        if color.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的颜色', 403)

        try:
            data = color_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        color, error = ColorService.update_color(color, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(color_schema.dump(color), '更新成功')

    @login_required
    @color_ns.response(200, '删除成功', base_response)
    @color_ns.response(404, '不存在', error_response)
    def delete(self, color_id):
        """删除颜色"""
        current_user = get_current_user()

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在')

        if color.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的颜色', 403)

        ColorService.delete_color(color)

        return ApiResponse.success(message='删除成功')
