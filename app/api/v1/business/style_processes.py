"""款号工艺管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.constants.permissions import (
    PERM_BUSINESS_STYLE_PROCESS_ADD,
    PERM_BUSINESS_STYLE_PROCESS_DELETE,
    PERM_BUSINESS_STYLE_PROCESS_EDIT,
    PERM_BUSINESS_STYLE_PROCESS_QUERY,
)
from app.schemas.business.style_process import StyleProcessCreateSchema, StyleProcessSchema, StyleProcessUpdateSchema
from app.services import StyleProcessService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_process_ns = Namespace('款号工艺管理-style-processes', description='款号工艺记录查询与维护')

common = get_common_models(style_process_ns)
base_response = common['base_response']
unauthorized_response = common['unauthorized_response']
error_response = common['error_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

style_process_query_parser = page_parser.copy()
style_process_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号 ID')
style_process_query_parser.add_argument(
    'process_type',
    type=str,
    location='args',
    help='工艺类型',
    choices=['embroidery', 'print', 'other'],
)

style_process_item_model = style_process_ns.model('StyleProcessItem', {
    'id': fields.Integer(description='工艺记录 ID'),
    'style_id': fields.Integer(description='款号 ID'),
    'process_type': fields.String(description='工艺类型'),
    'process_type_label': fields.String(description='工艺类型名称'),
    'process_name': fields.String(description='工艺名称'),
    'remark': fields.String(description='备注'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_process_list_data = build_page_data_model(
    style_process_ns,
    'StyleProcessListData',
    style_process_item_model,
    items_description='工艺列表',
)
style_process_list_response = build_page_response_model(
    style_process_ns,
    'StyleProcessListResponse',
    base_response,
    style_process_list_data,
    '工艺分页数据',
)
style_process_item_response = style_process_ns.clone('StyleProcessItemResponse', base_response, {
    'data': fields.Nested(style_process_item_model, description='工艺详情数据'),
})

style_process_create_model = style_process_ns.model('StyleProcessCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'process_type': fields.String(required=True, description='工艺类型', choices=['embroidery', 'print', 'other'], example='print'),
    'process_name': fields.String(description='工艺名称', example='丝网印花'),
    'remark': fields.String(description='备注', example='前胸图案'),
})

style_process_update_model = style_process_ns.model('StyleProcessUpdate', {
    'process_type': fields.String(description='工艺类型', choices=['embroidery', 'print', 'other'], example='embroidery'),
    'process_name': fields.String(description='工艺名称', example='电脑刺绣'),
    'remark': fields.String(description='备注', example='左胸 logo'),
})

style_process_schema = StyleProcessSchema()
style_process_create_schema = StyleProcessCreateSchema()
style_process_update_schema = StyleProcessUpdateSchema()


def build_style_process_access_error(error):
    """根据款号工艺访问错误内容推导响应状态码。"""
    return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)


def serialize_style_process(process):
    """序列化款号工艺记录并补充工艺类型名称。"""
    return StyleProcessService.enrich_with_label(style_process_schema.dump(process), process)


def get_accessible_style_for_process_or_error(style_id, require_write=False):
    """查询当前上下文可访问的款号，用于工艺记录读写前校验。"""
    if require_write:
        current_user, current_factory_id, error_response_obj = resolve_write_factory_context()
    else:
        current_user, current_factory_id, error_response_obj = resolve_read_factory_context(
            allow_internal_without_factory=True,
        )
    if error_response_obj:
        return None, None, None, error_response_obj

    style, error = StyleProcessService.check_style_permission(current_user, current_factory_id, style_id)
    if error:
        return None, None, None, build_style_process_access_error(error)
    return current_user, current_factory_id, style, None


def get_accessible_style_process_or_error(process_id, require_write=False):
    """查询当前上下文可访问的工艺记录。"""
    if require_write:
        current_user, current_factory_id, error_response_obj = resolve_write_factory_context()
    else:
        current_user, current_factory_id, error_response_obj = resolve_read_factory_context(
            allow_internal_without_factory=True,
        )
    if error_response_obj:
        return None, None, None, error_response_obj

    process = StyleProcessService.get_process_by_id(process_id)
    if not process:
        return None, None, None, ApiResponse.error('工艺记录不存在', 404)

    has_permission, error = StyleProcessService.check_process_permission(current_user, current_factory_id, process)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, process, None


@style_process_ns.route('')
class StyleProcessList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_QUERY)
    @style_process_ns.expect(style_process_query_parser)
    @style_process_ns.response(200, '查询成功', style_process_list_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询款号工艺分页列表接口。平台内部用户可不切工厂直接按款号查询。"""
        args = style_process_query_parser.parse_args()
        _, _, style, error_response_data = get_accessible_style_for_process_or_error(args['style_id'])
        if error_response_data:
            return error_response_data

        result = StyleProcessService.get_process_list(style.id, args)
        return ApiResponse.success_page_result(result, [serialize_style_process(process) for process in result['items']])

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_ADD)
    @style_process_ns.expect(style_process_create_model)
    @style_process_ns.response(201, '创建成功', style_process_item_response)
    @style_process_ns.response(400, '参数错误', error_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '款号不存在', error_response)
    def post(self):
        """创建款号工艺记录接口。写操作仍要求当前工厂上下文。"""
        try:
            data = style_process_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        _, _, _, error_response_data = get_accessible_style_for_process_or_error(data['style_id'], require_write=True)
        if error_response_data:
            return error_response_data

        process = StyleProcessService.create_process(data)
        return ApiResponse.success(serialize_style_process(process), '创建成功', 201)


@style_process_ns.route('/<int:process_id>')
class StyleProcessDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_QUERY)
    @style_process_ns.response(200, '查询成功', style_process_item_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '工艺记录不存在', error_response)
    def get(self, process_id):
        """查询款号工艺详情接口。平台内部用户可跨工厂查看。"""
        _, _, process, error_response_data = get_accessible_style_process_or_error(process_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(serialize_style_process(process))

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_EDIT)
    @style_process_ns.expect(style_process_update_model)
    @style_process_ns.response(200, '更新成功', style_process_item_response)
    @style_process_ns.response(400, '参数错误', error_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '工艺记录不存在', error_response)
    def patch(self, process_id):
        """更新款号工艺记录接口。写操作仍要求当前工厂上下文。"""
        _, _, process, error_response_data = get_accessible_style_process_or_error(process_id, require_write=True)
        if error_response_data:
            return error_response_data

        try:
            data = style_process_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        process = StyleProcessService.update_process(process, data)
        return ApiResponse.success(serialize_style_process(process), '更新成功')

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_PROCESS_DELETE)
    @style_process_ns.response(200, '删除成功', base_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '工艺记录不存在', error_response)
    def delete(self, process_id):
        """删除款号工艺记录接口。写操作仍要求当前工厂上下文。"""
        _, _, process, error_response_data = get_accessible_style_process_or_error(process_id, require_write=True)
        if error_response_data:
            return error_response_data

        StyleProcessService.delete_process(process)
        return ApiResponse.success(message='删除成功')
