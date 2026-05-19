"""分类管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.constants.permissions import (
    PERM_BASE_CATEGORY_ADD,
    PERM_BASE_CATEGORY_DELETE,
    PERM_BASE_CATEGORY_EDIT,
    PERM_BASE_CATEGORY_QUERY,
)
from app.schemas.base_data.category import CategoryCreateSchema, CategorySchema, CategoryUpdateSchema
from app.services import CategoryService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

category_ns = Namespace('分类管理-categories', description='分类管理')

common = get_common_models(category_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

category_query_parser = page_parser.copy()
category_query_parser.add_argument('name', type=str, location='args', help='分类名称')
category_query_parser.add_argument('parent_id', type=int, location='args', help='父分类ID')
category_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
category_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义分类', choices=[0, 1])
category_query_parser.add_argument('category_type', type=str, location='args', help='分类类型', choices=['style', 'material', 'order'])

category_option_query_parser = new_query_parser()
category_option_query_parser.add_argument('name', type=str, location='args', help='分类名称')
category_option_query_parser.add_argument('parent_id', type=int, location='args', help='父分类ID')
category_option_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
category_option_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义分类', choices=[0, 1])
category_option_query_parser.add_argument('category_type', type=str, location='args', help='分类类型', choices=['style', 'material', 'order'])

category_item_model = category_ns.model('CategoryItem', {
    'id': fields.Integer(description='分类ID'),
    'name': fields.String(description='分类名称'),
    'parent_id': fields.Integer(description='父级分类ID'),
    'code': fields.String(description='分类编码'),
    'category_type': fields.String(description='分类类型'),
    'factory_id': fields.Integer(description='所属工厂ID'),
    'sort_order': fields.Integer(description='排序值'),
    'status': fields.Integer(description='状态'),
    'remark': fields.String(description='备注'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
    'children': fields.List(fields.Raw, description='递归子分类列表；结构与当前分类节点一致'),
})

category_option_model = category_ns.model('CategoryOptionItem', {
    'id': fields.Integer(description='分类ID', example=1),
    'name': fields.String(description='分类名称', example='针织'),
    'code': fields.String(description='分类编码', example='KNIT'),
    'parent_id': fields.Integer(description='父分类ID', example=0),
    'category_type': fields.String(description='分类类型', example='material'),
    'factory_id': fields.Integer(description='所属工厂ID', example=1),
})

category_list_data = build_page_data_model(category_ns, 'CategoryListData', category_item_model, items_description='分类列表')
category_list_response = build_page_response_model(category_ns, 'CategoryListResponse', base_response, category_list_data, '分类分页数据')
category_item_response = category_ns.clone('CategoryItemResponse', base_response, {
    'data': fields.Nested(category_item_model, description='分类详情数据'),
})
category_tree_response = category_ns.clone('CategoryTreeResponse', base_response, {
    'data': fields.List(fields.Nested(category_item_model), description='分类树数据'),
})
category_options_response = category_ns.clone('CategoryOptionsResponse', base_response, {
    'data': fields.List(fields.Nested(category_option_model), description='分类下拉选项列表'),
})

category_create_model = category_ns.model('CategoryCreate', {
    'name': fields.String(required=True, description='分类名称', example='针织'),
    'code': fields.String(required=True, description='分类编码', example='KNIT'),
    'parent_id': fields.Integer(description='父分类ID', default=0, example=0),
    'category_type': fields.String(
        description='分类类型',
        default='style',
        choices=['style', 'material', 'order'],
        example='material',
    ),
    'sort_order': fields.Integer(description='排序', default=0, example=0),
    'remark': fields.String(description='备注', example='物料分类'),
})

category_update_model = category_ns.model('CategoryUpdate', {
    'name': fields.String(description='分类名称', example='棉麻'),
    'parent_id': fields.Integer(description='父分类ID', example=0),
    'category_type': fields.String(description='分类类型', choices=['style', 'material', 'order'], example='material'),
    'sort_order': fields.Integer(description='排序', example=10),
    'status': fields.Integer(description='状态', choices=[0, 1], example=1),
    'remark': fields.String(description='备注', example='基础面料分类'),
})

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()


@category_ns.route('')
class CategoryList(Resource):
    @login_required
    @button_permission(PERM_BASE_CATEGORY_QUERY)
    @category_ns.expect(category_query_parser)
    @category_ns.response(200, '成功', category_list_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询分类列表。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        result = CategoryService.get_category_list(current_user, get_current_factory_id(), category_query_parser.parse_args())
        return ApiResponse.success({
            'items': categories_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @button_permission(PERM_BASE_CATEGORY_ADD)
    @category_ns.expect(category_create_model)
    @category_ns.response(201, '创建成功', category_item_response)
    @category_ns.response(400, '参数错误', error_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(409, '分类已存在', error_response)
    def post(self):
        """创建分类。"""
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
            status_code = 409 if '已存在' in error else 403 if '权限' in error or '管理员' in error else 400
            return ApiResponse.error(error, status_code)

        return ApiResponse.success(category_schema.dump(category), '创建成功', 201)


@category_ns.route('/options')
class CategoryOptions(Resource):
    @login_required
    @button_permission(PERM_BASE_CATEGORY_QUERY)
    @category_ns.expect(category_option_query_parser)
    @category_ns.response(200, '成功', category_options_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询分类下拉选项列表，供分类选择器直接使用。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        categories = CategoryService.get_category_options(get_current_factory_id(), category_option_query_parser.parse_args())
        return ApiResponse.success([
            {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'parent_id': category.parent_id,
                'category_type': category.category_type,
                'factory_id': category.factory_id,
            }
            for category in categories
        ])


@category_ns.route('/tree')
class CategoryTree(Resource):
    @login_required
    @button_permission(PERM_BASE_CATEGORY_QUERY)
    @category_ns.response(200, '成功', category_tree_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询分类树。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')

        tree = CategoryService.get_category_tree(current_user, current_factory_id, request.args.get('category_type'))
        return ApiResponse.success(tree)


@category_ns.route('/<int:category_id>')
class CategoryDetail(Resource):
    @login_required
    @button_permission(PERM_BASE_CATEGORY_QUERY)
    @category_ns.response(200, '成功', category_item_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(403, '无权限', forbidden_response)
    @category_ns.response(404, '分类不存在', error_response)
    def get(self, category_id):
        """查询分类详情。"""
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
    @button_permission(PERM_BASE_CATEGORY_EDIT)
    @category_ns.expect(category_update_model)
    @category_ns.response(200, '更新成功', category_item_response)
    @category_ns.response(400, '参数错误', error_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(403, '无权限', forbidden_response)
    @category_ns.response(404, '分类不存在', error_response)
    def patch(self, category_id):
        """更新分类。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')

        can_manage, error = CategoryService.check_manage_permission(current_user, current_factory_id, category)
        if not can_manage:
            return ApiResponse.error(error, 403)

        try:
            data = category_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        category, error = CategoryService.update_category(category, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(category_schema.dump(category), '更新成功')

    @login_required
    @button_permission(PERM_BASE_CATEGORY_DELETE)
    @category_ns.response(200, '删除成功', base_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(403, '无权限', forbidden_response)
    @category_ns.response(404, '分类不存在', error_response)
    @category_ns.response(409, '分类存在子项或被引用', error_response)
    def delete(self, category_id):
        """删除分类。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在')

        can_manage, error = CategoryService.check_manage_permission(current_user, current_factory_id, category)
        if not can_manage:
            return ApiResponse.error(error, 403)

        success, error = CategoryService.delete_category(category)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')
