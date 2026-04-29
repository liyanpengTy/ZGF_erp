"""款号管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.business.style import StyleSchema, StyleCreateSchema, StyleUpdateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, StyleService

style_ns = Namespace('styles', description='款号管理')

shared = get_shared_models(style_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
style_query_parser = style_ns.parser()
style_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_query_parser.add_argument('style_no', type=str, location='args', help='款号')
style_query_parser.add_argument('name', type=str, location='args', help='款号名称')
style_query_parser.add_argument('category_id', type=int, location='args', help='分类ID')
style_query_parser.add_argument('gender', type=str, location='args', help='性别')
style_query_parser.add_argument('season', type=str, location='args', help='季节')
style_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

# ========== 响应模型 ==========
style_item_model = style_ns.model('StyleItem', {
    'id': fields.Integer(),
    'factory_id': fields.Integer(),
    'style_no': fields.String(),
    'customer_style_no': fields.String(),
    'name': fields.String(),
    'category_id': fields.Integer(),
    'category_name': fields.String(),
    'gender': fields.String(),
    'season': fields.String(),
    'material': fields.String(),
    'description': fields.String(),
    'status': fields.Integer(),
    'images': fields.List(fields.String()),
    'need_cutting': fields.Integer(),
    'cutting_reserve': fields.Float(),
    'custom_attributes': fields.Raw(),
    'is_splice': fields.Integer(description='是否拼接款：0-否，1-是'),
    'splice_data': fields.List(fields.Raw(), description='拼接数据，格式：[{"sequence":1,"description":"红色棉麻"}]'),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_list_data = style_ns.model('StyleListData', {
    'items': fields.List(fields.Nested(style_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_list_response = style_ns.clone('StyleListResponse', base_response, {
    'data': fields.Nested(style_list_data)
})

style_item_response = style_ns.clone('StyleItemResponse', base_response, {
    'data': fields.Nested(style_item_model)
})

# ========== Schema 初始化 ==========
style_schema = StyleSchema()
styles_schema = StyleSchema(many=True)
style_create_schema = StyleCreateSchema()
style_update_schema = StyleUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@style_ns.route('')
class StyleList(Resource):
    @login_required
    @style_ns.expect(style_query_parser)
    @style_ns.response(200, '成功', style_list_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = StyleService.get_style_list(current_user, args)

        items = []
        for style in result['items']:
            item = style_schema.dump(style)
            item['category_name'] = StyleService.get_category_name(style.category_id)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @style_ns.expect(style_ns.model('StyleCreate', {
        'style_no': fields.String(required=True, description='款号'),
        'customer_style_no': fields.String(description='客户款号'),
        'name': fields.String(description='款号名称'),
        'category_id': fields.Integer(description='分类ID'),
        'gender': fields.String(description='性别'),
        'season': fields.String(description='季节'),
        'material': fields.String(description='材质'),
        'description': fields.String(description='描述'),
        'images': fields.List(fields.String(), description='图片列表'),
        'need_cutting': fields.Integer(description='是否需要裁切', default=0),
        'cutting_reserve': fields.Float(description='裁切预留', default=0),
        'custom_attributes': fields.Raw(description='自定义属性'),
        'is_splice': fields.Integer(description='是否拼接款', default=0),
        'splice_data': fields.List(fields.Raw(), description='拼接数据，格式：[{"sequence":1,"description":"红色棉麻"}]')
    }))
    @style_ns.response(201, '创建成功', style_item_response)
    @style_ns.response(400, '参数错误', error_response)
    @style_ns.response(409, '款号已存在', error_response)
    def post(self):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style, error = StyleService.create_style(current_user, data, style_schema)
        if error:
            return ApiResponse.error(error, 409)

        result = style_schema.dump(style)
        result['category_name'] = StyleService.get_category_name(style.category_id)

        return ApiResponse.success(result, '创建成功', 201)


@style_ns.route('/<int:style_id>')
class StyleDetail(Resource):
    @login_required
    @style_ns.response(200, '成功', style_item_response)
    @style_ns.response(404, '不存在', error_response)
    def get(self, style_id):
        current_user = get_current_user()

        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')

        has_permission, error = StyleService.check_permission(current_user, style)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = style_schema.dump(style)
        result['category_name'] = StyleService.get_category_name(style.category_id)

        return ApiResponse.success(result)

    @login_required
    @style_ns.expect(style_ns.model('StyleUpdate', {
        'style_no': fields.String(description='款号'),
        'customer_style_no': fields.String(description='客户款号'),
        'name': fields.String(description='款号名称'),
        'category_id': fields.Integer(description='分类ID'),
        'gender': fields.String(description='性别'),
        'season': fields.String(description='季节'),
        'material': fields.String(description='材质'),
        'description': fields.String(description='描述'),
        'status': fields.Integer(description='状态', choices=[0, 1]),
        'images': fields.List(fields.String(), description='图片列表'),
        'need_cutting': fields.Integer(description='是否需要裁切'),
        'cutting_reserve': fields.Float(description='裁切预留'),
        'custom_attributes': fields.Raw(description='自定义属性'),
        'is_splice': fields.Integer(description='是否拼接款'),
        'splice_data': fields.List(fields.Raw(), description='拼接数据，格式：[{"sequence":1,"description":"红色棉麻"}]')
    }))
    @style_ns.response(200, '更新成功', style_item_response)
    @style_ns.response(404, '不存在', error_response)
    def put(self, style_id):
        current_user = get_current_user()

        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')

        if style.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的款号', 403)

        try:
            data = style_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style, error = StyleService.update_style(style, data, current_user)
        if error:
            return ApiResponse.error(error, 409)

        result = style_schema.dump(style)
        result['category_name'] = StyleService.get_category_name(style.category_id)

        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_ns.response(200, '删除成功', base_response)
    @style_ns.response(404, '不存在', error_response)
    def delete(self, style_id):
        current_user = get_current_user()

        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')

        if style.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的款号', 403)

        success, error = StyleService.delete_style(style)
        if not success:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(message='删除成功')
