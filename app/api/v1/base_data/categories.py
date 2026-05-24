"""分类管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
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
category_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID，平台内部用户可按工厂筛选')
category_query_parser.add_argument('parent_id', type=int, location='args', help='父分类ID')
category_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
category_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义分类', choices=[0, 1])
category_query_parser.add_argument('category_type', type=str, location='args', help='分类类型', choices=['style', 'material', 'order'])

category_option_query_parser = new_query_parser()
category_option_query_parser.add_argument('name', type=str, location='args', help='分类名称')
category_option_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID，平台内部用户可按工厂筛选')
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
})
category_item_model['children'] = fields.List(
    fields.Nested(category_item_model),
    description='递归子分类列表；结构与当前分类节点一致',
)

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


def serialize_category_option(category):
    """序列化分类下拉选项。"""
    return {
        'id': category.id,
        'name': category.name,
        'code': category.code,
        'parent_id': category.parent_id,
        'category_type': category.category_type,
        'factory_id': category.factory_id,
    }


def get_category_request_context(query_factory_id=None, require_write=False):
    """统一解析分类接口的当前用户与工厂上下文。"""
    if not require_write:
        return resolve_read_factory_context(query_factory_id=query_factory_id, allow_internal_without_factory=True)

    current_user, current_factory_id, error_response_data = resolve_read_factory_context(
        allow_internal_without_factory=True,
    )
    if error_response_data:
        return None, None, error_response_data
    if current_user and current_user.is_internal_user and not current_factory_id:
        return current_user, current_factory_id, None
    return resolve_write_factory_context()


@category_ns.route('')
class CategoryList(Resource):
    @login_required
    @button_permission(PERM_BASE_CATEGORY_QUERY)
    @category_ns.expect(category_query_parser)
    @category_ns.response(200, '成功', category_list_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询分类分页列表接口，支持按分类类型、状态和工厂可见范围筛选。"""
        args = category_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = get_category_request_context(args.get('factory_id'))
        if error_response_data:
            return error_response_data

        result = CategoryService.get_category_list(current_user, current_factory_id, args)
        return ApiResponse.success_page_result(result, categories_schema.dump(result['items']))

    @login_required
    @button_permission(PERM_BASE_CATEGORY_ADD)
    @category_ns.expect(category_create_model)
    @category_ns.response(201, '创建成功', category_item_response)
    @category_ns.response(400, '参数错误', error_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(403, '无权限', forbidden_response)
    @category_ns.response(409, '分类已存在', error_response)
    def post(self):
        """创建分类接口，用于新增平台公共分类或工厂自定义分类。"""
        current_user, current_factory_id, error_response_data = get_category_request_context(require_write=True)
        if error_response_data:
            return error_response_data

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
    @category_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询分类下拉选项列表，供分类选择器直接使用。"""
        args = category_option_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = get_category_request_context(args.get('factory_id'))
        if error_response_data:
            return error_response_data

        categories = CategoryService.get_category_options(current_user, current_factory_id, args)
        return ApiResponse.success_list([serialize_category_option(category) for category in categories])


@category_ns.route('/tree')
class CategoryTree(Resource):
    @login_required
    @button_permission(PERM_BASE_CATEGORY_QUERY)
    @category_ns.response(200, '成功', category_tree_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    @category_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询分类树接口，返回树形结构供分类配置与选择使用。"""
        current_user, current_factory_id, error_response_data = get_category_request_context(
            request.args.get('factory_id', type=int)
        )
        if error_response_data:
            return error_response_data

        tree = CategoryService.get_category_tree(
            current_user,
            current_factory_id,
            request.args.get('category_type'),
        )
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
        """查询分类详情接口，返回单个分类的完整信息。"""
        current_user, current_factory_id, error_response_data = get_category_request_context(
            request.args.get('factory_id', type=int)
        )
        if error_response_data:
            return error_response_data
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在', 404)

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
        """更新分类接口，可调整名称、编码、父级、排序和状态。"""
        current_user, current_factory_id, error_response_data = get_category_request_context(require_write=True)
        if error_response_data:
            return error_response_data
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在', 404)

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
        """删除分类接口，存在子项或被业务引用时会阻止删除。"""
        current_user, current_factory_id, error_response_data = get_category_request_context(require_write=True)
        if error_response_data:
            return error_response_data
        category = CategoryService.get_category_by_id(category_id)
        if not category:
            return ApiResponse.error('分类不存在', 404)

        can_manage, error = CategoryService.check_manage_permission(current_user, current_factory_id, category)
        if not can_manage:
            return ApiResponse.error(error, 403)

        success, error = CategoryService.delete_category(category)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')
