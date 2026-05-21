"""工序管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import require_current_user
from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.constants.permissions import (
    PERM_BUSINESS_PROCESS_ADD,
    PERM_BUSINESS_PROCESS_DELETE,
    PERM_BUSINESS_PROCESS_EDIT,
    PERM_BUSINESS_PROCESS_QUERY,
    PERM_BUSINESS_STYLE_PROCESS_ADD,
    PERM_BUSINESS_STYLE_PROCESS_DELETE,
    PERM_BUSINESS_STYLE_PROCESS_QUERY,
)
from app.schemas.business.process import ProcessCreateSchema, ProcessSchema, ProcessUpdateSchema, StyleProcessMappingSchema
from app.services import ProcessService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

process_ns = Namespace('工序管理-processes', description='工序管理')

common = get_common_models(process_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

process_query_parser = page_parser.copy()
process_query_parser.add_argument('name', type=str, location='args', help='工序名称')
process_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

process_option_query_parser = new_query_parser()
process_option_query_parser.add_argument('name', type=str, location='args', help='工序名称')
process_option_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

process_item_model = process_ns.model('ProcessItem', {
    'id': fields.Integer(description='工序 ID'),
    'name': fields.String(description='工序名称'),
    'code': fields.String(description='工序编码'),
    'description': fields.String(description='工序描述'),
    'sort_order': fields.Integer(description='排序值'),
    'status': fields.Integer(description='状态'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

process_option_model = process_ns.model('ProcessOptionItem', {
    'id': fields.Integer(description='工序 ID', example=1),
    'name': fields.String(description='工序名称', example='裁床'),
    'code': fields.String(description='工序编码', example='CUT'),
    'status': fields.Integer(description='状态', example=1),
})

process_list_data = build_page_data_model(process_ns, 'ProcessListData', process_item_model, items_description='工序列表')
process_list_response = build_page_response_model(process_ns, 'ProcessListResponse', base_response, process_list_data, '工序分页数据')
process_item_response = process_ns.clone('ProcessItemResponse', base_response, {
    'data': fields.Nested(process_item_model, description='工序详情数据')
})
process_options_response = process_ns.clone('ProcessOptionsResponse', base_response, {
    'data': fields.List(fields.Nested(process_option_model), description='工序下拉选项列表')
})

style_process_item_model = process_ns.model('ProcessStyleProcessItem', {
    'id': fields.Integer(description='映射 ID'),
    'style_id': fields.Integer(description='款号 ID'),
    'process_id': fields.Integer(description='工序 ID'),
    'process_name': fields.String(description='工序名称'),
    'process_code': fields.String(description='工序编码'),
    'sequence': fields.Integer(description='工序顺序'),
    'remark': fields.String(description='备注'),
})

style_process_list_response = process_ns.clone(
    'StyleProcessListResponse',
    base_response,
    {'data': fields.List(fields.Nested(style_process_item_model), description='款号工序映射列表')}
)

style_process_item_create_model = process_ns.model('StyleProcessItemCreate', {
    'process_id': fields.Integer(required=True, description='工序 ID'),
    'sequence': fields.Integer(description='工序顺序', default=1),
    'remark': fields.String(description='备注'),
})

style_process_batch_save_model = process_ns.model('StyleProcessBatchSave', {
    'mappings': fields.List(fields.Nested(style_process_item_create_model), required=True, description='工序列表'),
})

process_create_model = process_ns.model('ProcessCreate', {
    'name': fields.String(required=True, description='工序名称', example='裁床'),
    'code': fields.String(required=True, description='工序编码', example='CUT'),
    'description': fields.String(description='工序描述', example='裁片前置工序'),
    'sort_order': fields.Integer(description='排序', default=0, example=0),
})

process_update_model = process_ns.model('ProcessUpdate', {
    'name': fields.String(description='工序名称', example='缝制'),
    'description': fields.String(description='工序描述', example='主线缝制工序'),
    'sort_order': fields.Integer(description='排序', example=10),
    'status': fields.Integer(description='状态', choices=[0, 1], example=1),
})

process_schema = ProcessSchema()
processes_schema = ProcessSchema(many=True)
process_create_schema = ProcessCreateSchema()
process_update_schema = ProcessUpdateSchema()
style_process_mapping_schema = StyleProcessMappingSchema()


def get_required_process_user():
    """获取工序接口当前用户，不存在时返回统一错误响应。"""
    return require_current_user()


def get_process_or_error(process_id):
    """根据工序 ID 查询工序，不存在时返回统一错误响应。"""
    process = ProcessService.get_process_by_id(process_id)
    if not process:
        return None, ApiResponse.error('工序不存在')
    return process, None


def serialize_process_option(process):
    """序列化工序下拉选项。"""
    return {
        'id': process.id,
        'name': process.name,
        'code': process.code,
        'status': process.status,
    }


def check_process_admin_permission(current_user):
    """校验工序主数据维护权限，仅允许平台管理员维护。"""
    if not current_user:
        return False, '用户不存在'
    if not current_user.is_platform_admin:
        return False, '只有平台管理员可以维护工序'
    return True, None


def get_accessible_style_for_process_or_error(style_id, require_write=False):
    """获取当前上下文下可访问的款号工序映射目标。"""
    if require_write:
        current_user, current_factory_id, error_response_data = resolve_write_factory_context()
    else:
        current_user, current_factory_id, error_response_data = resolve_read_factory_context(
            allow_internal_without_factory=True,
        )
    if error_response_data:
        return None, None, error_response_data

    _, error = ProcessService.check_style_permission(current_user, current_factory_id, style_id)
    if error:
        return None, None, ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)
    return current_user, current_factory_id, None


@process_ns.route('')
class ProcessList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_QUERY)
    @process_ns.expect(process_query_parser)
    @process_ns.response(200, '成功', process_list_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询工序分页列表接口，支持按名称和状态筛选系统工序。"""
        _, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data
        args = process_query_parser.parse_args()
        result = ProcessService.get_process_list(args)
        return ApiResponse.success_page_result(result, processes_schema.dump(result['items']))

    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_ADD)
    @process_ns.expect(process_create_model)
    @process_ns.response(201, '创建成功', process_item_response)
    @process_ns.response(400, '参数错误', error_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(409, '工序已存在', error_response)
    def post(self):
        """创建工序接口，用于新增平台级工序主数据。"""
        current_user, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data
        has_permission, error = check_process_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = process_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        process, service_error = ProcessService.create_process(data)
        if service_error:
            return ApiResponse.error(service_error, 409)
        return ApiResponse.success(process_schema.dump(process), '创建成功', 201)


@process_ns.route('/options')
class ProcessOptions(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_QUERY)
    @process_ns.expect(process_option_query_parser)
    @process_ns.response(200, '成功', process_options_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询工序下拉选项列表，供工序选择器直接使用。"""
        _, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data

        processes = ProcessService.get_process_options(process_option_query_parser.parse_args())
        return ApiResponse.success_list([serialize_process_option(process) for process in processes])


@process_ns.route('/<int:process_id>')
class ProcessDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_QUERY)
    @process_ns.response(200, '成功', process_item_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(404, '工序不存在', error_response)
    def get(self, process_id):
        """查询工序详情接口，返回单个工序的完整配置。"""
        _, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data
        process, error_response_data = get_process_or_error(process_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(process_schema.dump(process))

    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_EDIT)
    @process_ns.expect(process_update_model)
    @process_ns.response(200, '更新成功', process_item_response)
    @process_ns.response(400, '参数错误', error_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(404, '工序不存在', error_response)
    def patch(self, process_id):
        """更新工序接口，可修改工序名称、编码、描述和状态。"""
        current_user, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data
        has_permission, error = check_process_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        process, error_response_data = get_process_or_error(process_id)
        if error_response_data:
            return error_response_data

        try:
            data = process_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        process, service_error = ProcessService.update_process(process, data)
        if service_error:
            return ApiResponse.error(service_error, 400)
        return ApiResponse.success(process_schema.dump(process), '更新成功')

    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_DELETE)
    @process_ns.response(200, '删除成功', base_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(404, '工序不存在', error_response)
    @process_ns.response(409, '工序已被引用', error_response)
    def delete(self, process_id):
        """删除工序接口，已被业务引用的工序不允许删除。"""
        current_user, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data
        has_permission, error = check_process_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        process, error_response_data = get_process_or_error(process_id)
        if error_response_data:
            return error_response_data

        success, service_error = ProcessService.delete_process(process)
        if not success:
            return ApiResponse.error(service_error, 409)
        return ApiResponse.success(message='删除成功')


@process_ns.route('/enabled')
class EnabledProcesses(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_PROCESS_QUERY)
    @process_ns.response(200, '成功', base_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询启用工序列表接口，返回当前可选的工序主数据。"""
        _, error_response_data = get_required_process_user()
        if error_response_data:
            return error_response_data
        processes = ProcessService.get_all_enabled_processes()
        return ApiResponse.success_list(processes_schema.dump(processes))


@process_ns.route('/styles/<int:style_id>/processes')
class StyleProcesses(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_QUERY)
    @process_ns.response(200, '成功', style_process_list_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(404, '款号不存在', error_response)
    def get(self, style_id):
        """查询款号工序映射列表接口，返回款号当前绑定的工序顺序。"""
        _, _, error_response_data = get_accessible_style_for_process_or_error(style_id)
        if error_response_data:
            return error_response_data

        mappings = ProcessService.get_style_processes(style_id)
        return ApiResponse.success(style_process_mapping_schema.dump(mappings, many=True))

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_ADD)
    @process_ns.expect(style_process_batch_save_model)
    @process_ns.response(200, '保存成功', style_process_list_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(404, '款号不存在', error_response)
    def post(self, style_id):
        """批量保存款号工序映射接口，用于整体重建款号工序顺序。"""
        _, _, error_response_data = get_accessible_style_for_process_or_error(style_id, require_write=True)
        if error_response_data:
            return error_response_data

        data = request.get_json() or {}
        mappings = ProcessService.batch_save_style_processes(style_id, data.get('mappings', []))
        return ApiResponse.success(style_process_mapping_schema.dump(mappings, many=True), '保存成功')


@process_ns.route('/styles/<int:style_id>/processes/<int:mapping_id>')
class StyleProcessDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_DELETE)
    @process_ns.response(200, '删除成功', base_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    @process_ns.response(403, '无权限', forbidden_response)
    @process_ns.response(404, '映射不存在', error_response)
    def delete(self, style_id, mapping_id):
        """删除款号工序映射接口，用于移除单条款号工序关联。"""
        _, _, error_response_data = get_accessible_style_for_process_or_error(style_id, require_write=True)
        if error_response_data:
            return error_response_data

        mapping = ProcessService.get_style_process_mapping_by_id(mapping_id)
        if not mapping or mapping.style_id != style_id:
            return ApiResponse.error('工序关联不存在')

        ProcessService.delete_style_process(mapping)
        return ApiResponse.success(message='删除成功')
