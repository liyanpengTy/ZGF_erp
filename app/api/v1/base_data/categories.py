"""分类管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.base_data.category import CategorySchema, CategoryCreateSchema, CategoryUpdateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, CategoryService

category_ns = Namespace('categories', description='分类管理')

shared = get_shared_models(category_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
category_query_parser = category_ns.parser()
category_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
category_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
category_query_parser.add_argument('name', type=str, location='args', help='分类名称')
category_query_parser.add_argument('parent_id', type=int, location='args', help='父分类ID')
category_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
category_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])

# ========== 响应模型 ==========
category_item_model = category_ns.model('CategoryItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'parent_id': fields.Integer(),
    'code': fields.String(),
    'factory_id': fields.Integer(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'update_time': fields.String(),
    'children': fields.List(fields.Raw)
})

category_list_data = category_ns.model('CategoryListData', {
    'items': fields.List(fields.Nested(category_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

category_list_response = category_ns.clone('CategoryListResponse', base_response, {
    'data': fields.Nested(category_list_data)
})

category_item_response = category_ns.clone('CategoryItemResponse', base_response, {
    'data': fields.Nested(category_item_model)
})

category_tree_response = category_ns.clone('CategoryTreeResponse', base_response, {
    'data': fields.List(fields.Nested(category_item_model))
})

# ========== Schema 初始化 ==========
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@category_ns.route('')
class CategoryList(Resource):
    @login_required
    @category_ns.expect(category_query_parser)
    @category_ns.response(200, '成功', category_list_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = category_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = CategoryService.get_category_list(current_user, args)

        return ApiResponse.success({
            'items': categories_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @category_ns.expect(category_ns.model('CategoryCreate', {
        'name': fields.String(required=True, description='分类名称'),
        'code': fields.String(required=True, description='分类编码'),
        'parent_id': fields.Integer(description='父分类ID'),
        'sort_order': fields.Integer(description='排序')
    }))
    @category_ns.response(201, '创建成功', category_item_response)
    @category_ns.response(400, '参数错误', error_response)
    @category_ns.response(409, '编码已存在', error_response)
    def post(self):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = category_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        category, error = CategoryService.create_category(current_user, data)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(category_schema.dump(category), '创建成功', 201)


@category_ns.route('/tree')
class CategoryTree(Resource):
    @login_required
    @category_ns.response(200, '成功', category_tree_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        tree = CategoryService.get_category_tree(current_user)

        return ApiResponse.success(tree)


@category_ns.route('/<int:category_id>')
class CategoryDetail(Resource):
    @login_required
    @category_ns.response(200, '成功', category_item_response)
    @category_ns.response(404, '不存在', error_response)
    def get(self, category_id):
        current_user = get_current_user()

        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')

        has_permission, error = CategoryService.check_permission(current_user, category)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(category_schema.dump(category))

    @login_required
    @category_ns.expect(category_ns.model('CategoryUpdate', {
        'name': fields.String(description='分类名称'),
        'parent_id': fields.Integer(description='父分类ID'),
        'sort_order': fields.Integer(description='排序'),
        'status': fields.Integer(description='状态', choices=[0, 1])
    }))
    @category_ns.response(200, '更新成功', category_item_response)
    @category_ns.response(404, '不存在', error_response)
    def put(self, category_id):
        current_user = get_current_user()

        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')

        if category.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的分类', 403)

        try:
            data = category_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        category, error = CategoryService.update_category(category, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(category_schema.dump(category), '更新成功')

    @login_required
    @category_ns.response(200, '删除成功', base_response)
    @category_ns.response(404, '不存在', error_response)
    def delete(self, category_id):
        current_user = get_current_user()

        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')

        if category.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的分类', 403)

        success, error = CategoryService.delete_category(category)
        if not success:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(message='删除成功')
