"""款号工艺管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.api.common.response_helpers import load_json_or_error, success_mapped_page
from app.api.common.serializers import serialize_schema
from app.api.common.style_relation_helpers import (
    get_accessible_style_or_error,
    get_accessible_style_resource_or_error,
)
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
build_item_response_model = common['build_item_response_model']

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
style_process_item_response = build_item_response_model(style_process_ns, 'StyleProcessItemResponse', base_response, style_process_item_model, '工艺详情数据')

style_process_create_model = style_process_ns.model('StyleProcessCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'process_type': fields.String(required=True, description='工艺类型', choices=['embroidery', 'print', 'other'], example='print'),
    'process_name': fields.String(required=True, description='工艺名称', example='丝网印花'),
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


def serialize_style_process(process):
    """序列化款号工艺记录并补充工艺类型名称。"""
    return StyleProcessService.enrich_with_label(serialize_schema(style_process_schema, process), process)


def get_accessible_style_for_process_or_error(style_id, require_write=False):
    """查询当前上下文可访问的款号，用于工艺记录读写前校验。"""
    return get_accessible_style_or_error(
        style_id,
        StyleProcessService.check_style_permission,
        require_write=require_write,
    )


def get_accessible_style_process_or_error(process_id, require_write=False):
    """查询当前上下文可访问的工艺记录。"""
    return get_accessible_style_resource_or_error(
        process_id,
        StyleProcessService.get_process_by_id,
        StyleProcessService.check_process_permission,
        '工艺记录不存在',
        require_write=require_write,
    )


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
        return success_mapped_page(result, [serialize_style_process(process) for process in result['items']])

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
        data, validation_error = load_json_or_error(style_process_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

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

        data, validation_error = load_json_or_error(style_process_update_schema, request.get_json() or {})
        if validation_error:
            return validation_error

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
