"""尺码管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.constants.permissions import (
    PERM_BASE_SIZE_ADD,
    PERM_BASE_SIZE_DELETE,
    PERM_BASE_SIZE_EDIT,
    PERM_BASE_SIZE_QUERY,
)
from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.base_data.size import SizeCreateSchema, SizeSchema, SizeUpdateSchema
from app.services import SizeService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

size_ns = Namespace('尺码管理-sizes', description='尺码管理')

common = get_common_models(size_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

size_query_parser = page_parser.copy()
size_query_parser.add_argument('name', type=str, location='args', help='尺码名称')
size_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
size_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查询工厂自定义数据', choices=[0, 1])
size_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID，平台内部用户可按工厂筛选')

size_item_model = size_ns.model('SizeItem', {
    'id': fields.Integer(description='尺码ID'),
    'name': fields.String(description='尺码名称'),
    'code': fields.String(description='尺码编码'),
    'factory_id': fields.Integer(description='所属工厂ID'),
    'sort_order': fields.Integer(description='排序值'),
    'status': fields.Integer(description='状态'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

size_list_data = build_page_data_model(size_ns, 'SizeListData', size_item_model, items_description='尺码列表')
size_list_response = build_page_response_model(size_ns, 'SizeListResponse', base_response, size_list_data, '尺码分页数据')
size_item_response = size_ns.clone('SizeItemResponse', base_response, {
    'data': fields.Nested(size_item_model, description='尺码详情数据')
})

size_create_model = size_ns.model('SizeCreate', {
    'name': fields.String(required=True, description='尺码名称', example='M'),
    'code': fields.String(required=True, description='尺码编码', example='M'),
    'sort_order': fields.Integer(description='排序', default=0, example=0),
})

size_update_model = size_ns.model('SizeUpdate', {
    'name': fields.String(description='尺码名称', example='L'),
    'sort_order': fields.Integer(description='排序', example=10),
    'status': fields.Integer(description='状态', choices=[0, 1], example=1),
})

size_schema = SizeSchema()
sizes_schema = SizeSchema(many=True)
size_create_schema = SizeCreateSchema()
size_update_schema = SizeUpdateSchema()


def get_size_request_context(query_factory_id=None, require_write=False):
    """统一解析尺码接口的当前用户与工厂上下文。"""
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


@size_ns.route('')
class SizeList(Resource):
    @login_required
    @button_permission(PERM_BASE_SIZE_QUERY)
    @size_ns.expect(size_query_parser)
    @size_ns.response(200, '成功', size_list_response)
    @size_ns.response(401, '未登录', unauthorized_response)
    @size_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询尺码分页列表接口，支持按名称、状态和工厂可见范围筛选。"""
        args = size_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = get_size_request_context(args.get('factory_id'))
        if error_response_data:
            return error_response_data

        result = SizeService.get_size_list(current_user, current_factory_id, args)
        return ApiResponse.success_page_result(result, sizes_schema.dump(result['items']))

    @login_required
    @button_permission(PERM_BASE_SIZE_ADD)
    @size_ns.expect(size_create_model)
    @size_ns.response(201, '创建成功', size_item_response)
    @size_ns.response(400, '参数错误', error_response)
    @size_ns.response(401, '未登录', unauthorized_response)
    @size_ns.response(403, '无权限', forbidden_response)
    @size_ns.response(409, '尺码已存在', error_response)
    def post(self):
        """创建尺码接口，用于新增系统尺码或工厂自定义尺码。"""
        current_user, current_factory_id, error_response_data = get_size_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        try:
            data = size_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        size, error = SizeService.create_size(current_user, current_factory_id, data)
        if error:
            status_code = 409 if '已存在' in error else 403 if '权限' in error or '管理员' in error else 400
            return ApiResponse.error(error, status_code)

        return ApiResponse.success(size_schema.dump(size), '创建成功', 201)


@size_ns.route('/<int:size_id>')
class SizeDetail(Resource):
    @login_required
    @button_permission(PERM_BASE_SIZE_QUERY)
    @size_ns.response(200, '成功', size_item_response)
    @size_ns.response(401, '未登录', unauthorized_response)
    @size_ns.response(403, '无权限', forbidden_response)
    @size_ns.response(404, '尺码不存在', error_response)
    def get(self, size_id):
        """查询尺码详情接口，返回单个尺码完整信息。"""
        current_user, current_factory_id, error_response_data = get_size_request_context()
        if error_response_data:
            return error_response_data

        size = SizeService.get_size_by_id(size_id)
        if not size:
            return ApiResponse.error('尺码不存在', 404)

        has_permission, error = SizeService.check_permission(current_user, current_factory_id, size)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(size_schema.dump(size))

    @login_required
    @button_permission(PERM_BASE_SIZE_EDIT)
    @size_ns.expect(size_update_model)
    @size_ns.response(200, '更新成功', size_item_response)
    @size_ns.response(400, '参数错误', error_response)
    @size_ns.response(401, '未登录', unauthorized_response)
    @size_ns.response(403, '无权限', forbidden_response)
    @size_ns.response(404, '尺码不存在', error_response)
    def patch(self, size_id):
        """更新尺码接口，可修改尺码名称、编码、排序和状态。"""
        current_user, current_factory_id, error_response_data = get_size_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        size = SizeService.get_size_by_id(size_id)
        if not size:
            return ApiResponse.error('尺码不存在', 404)

        can_manage, error = SizeService.check_manage_permission(current_user, current_factory_id, size)
        if not can_manage:
            return ApiResponse.error(error, 403)

        try:
            data = size_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        size, error = SizeService.update_size(size, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(size_schema.dump(size), '更新成功')

    @login_required
    @button_permission(PERM_BASE_SIZE_DELETE)
    @size_ns.response(200, '删除成功', base_response)
    @size_ns.response(401, '未登录', unauthorized_response)
    @size_ns.response(403, '无权限', forbidden_response)
    @size_ns.response(404, '尺码不存在', error_response)
    def delete(self, size_id):
        """删除尺码接口，用于移除未被业务引用的尺码数据。"""
        current_user, current_factory_id, error_response_data = get_size_request_context(require_write=True)
        if error_response_data:
            return error_response_data
        size = SizeService.get_size_by_id(size_id)
        if not size:
            return ApiResponse.error('尺码不存在', 404)
        can_manage, error = SizeService.check_manage_permission(current_user, current_factory_id, size)
        if not can_manage:
            return ApiResponse.error(error, 403)
        SizeService.delete_size(size)
        return ApiResponse.success(message='删除成功')
