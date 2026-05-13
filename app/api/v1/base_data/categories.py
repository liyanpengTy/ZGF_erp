"""分类管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.base_data.category import CategoryCreateSchema, CategorySchema, CategoryUpdateSchema
from app.services import CategoryService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

category_ns = Namespace('分类管理-categories', description='分类管理')

common = get_common_models(category_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']

category_query_parser = page_parser.copy()
category_query_parser.add_argument('name', type=str, location='args', help='分类名称')
category_query_parser.add_argument('parent_id', type=int, location='args', help='父分类ID')
category_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
category_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])
category_query_parser.add_argument('category_type', type=str, location='args', help='分类类型', choices=['style', 'material', 'order'])

category_item_model = category_ns.model('CategoryItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'parent_id': fields.Integer(),
    'code': fields.String(),
    'category_type': fields.String(),
    'factory_id': fields.Integer(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String(),
    'children': fields.List(fields.Raw),
})

category_list_data = category_ns.model('CategoryListData', {
    'items': fields.List(fields.Nested(category_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer(),
})

category_list_response = category_ns.clone('CategoryListResponse', base_response, {'data': fields.Nested(category_list_data)})
category_item_response = category_ns.clone('CategoryItemResponse', base_response, {'data': fields.Nested(category_item_model)})
category_tree_response = category_ns.clone('CategoryTreeResponse', base_response, {'data': fields.List(fields.Nested(category_item_model))})

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()


@category_ns.route('')
class CategoryList(Resource):
    @login_required
    @category_ns.expect(category_query_parser)
    @category_ns.response(200, '成功', category_list_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询分类列表，支持按名称、父分类、状态和分类类型筛选。"""
        args = category_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = CategoryService.get_category_list(current_user, current_factory_id, args)
        return ApiResponse.success({
            'items': categories_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @category_ns.expect(category_ns.model('CategoryCreate', {
        'name': fields.String(required=True, description='分类名称'),
        'code': fields.String(required=True, description='分类编码'),
        'parent_id': fields.Integer(description='父分类ID', default=0),
        'category_type': fields.String(description='分类类型', default='style', choices=['style', 'material', 'order']),
        'sort_order': fields.Integer(description='排序', default=0),
        'remark': fields.String(description='备注'),
    }))
    @category_ns.response(201, '创建成功', category_item_response)
    def post(self):
        """在当前工厂上下文下创建分类。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = category_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        category, error = CategoryService.create_category(current_user, current_factory_id, data)
        if error:
            return ApiResponse.error(error, 409 if '已存在' in error else 400)

        return ApiResponse.success(category_schema.dump(category), '创建成功', 201)


@category_ns.route('/tree')
class CategoryTree(Resource):
    @login_required
    @category_ns.response(200, '成功', category_tree_response)
    def get(self):
        """按树形结构返回当前可见的分类数据。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        category_type = request.args.get('category_type')
        tree = CategoryService.get_category_tree(current_user, current_factory_id, category_type)
        return ApiResponse.success(tree)


@category_ns.route('/<int:category_id>')
class CategoryDetail(Resource):
    @login_required
    @category_ns.response(200, '成功', category_item_response)
    def get(self, category_id):
        """查看单个分类详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')

        has_permission, error = CategoryService.check_permission(current_user, current_factory_id, category)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(category_schema.dump(category))

    @login_required
    @category_ns.expect(category_ns.model('CategoryUpdate', {
        'name': fields.String(description='分类名称'),
        'parent_id': fields.Integer(description='父分类ID'),
        'category_type': fields.String(description='分类类型', choices=['style', 'material', 'order']),
        'sort_order': fields.Integer(description='排序'),
        'status': fields.Integer(description='状态', choices=[0, 1]),
        'remark': fields.String(description='备注'),
    }))
    @category_ns.response(200, '更新成功', category_item_response)
    def patch(self, category_id):
        """更新当前工厂自有的分类信息。"""
        current_factory_id = get_current_factory_id()
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')
        if category.factory_id != current_factory_id:
            return ApiResponse.error('只能修改自己工厂的分类', 403)

        try:
            data = category_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        category, error = CategoryService.update_category(category, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(category_schema.dump(category), '更新成功')

    @login_required
    @category_ns.response(200, '删除成功', base_response)
    def delete(self, category_id):
        """删除当前工厂自有的分类。"""
        current_factory_id = get_current_factory_id()
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')
        if category.factory_id != current_factory_id:
            return ApiResponse.error('只能删除自己工厂的分类', 403)
        success, error = CategoryService.delete_category(category)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')
