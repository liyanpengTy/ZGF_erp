"""颜色管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.api.common.context_helpers import get_factory_request_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.api.common.response_helpers import business_error, load_json_or_error, success_schema_page
from app.api.common.serializers import serialize_schema
from app.constants.permissions import (
    PERM_BASE_COLOR_ADD,
    PERM_BASE_COLOR_DELETE,
    PERM_BASE_COLOR_EDIT,
    PERM_BASE_COLOR_QUERY,
)
from app.schemas.base_data.color import ColorCreateSchema, ColorSchema, ColorUpdateSchema
from app.services import ColorService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

color_ns = Namespace('颜色管理-colors', description='颜色管理')

common = get_common_models(color_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']
build_item_response_model = common['build_item_response_model']

color_query_parser = page_parser.copy()
color_query_parser.add_argument('name', type=str, location='args', help='颜色名称')
color_query_parser.add_argument('actual_name', type=str, location='args', help='实际颜色名称')
color_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
color_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])
color_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID，平台内部用户可按工厂筛选')

color_item_model = color_ns.model(
    'ColorItem',
    {
        'id': fields.Integer(description='颜色 ID'),
        'name': fields.String(description='颜色名称'),
        'actual_name': fields.String(description='实际颜色名称'),
        'code': fields.String(description='颜色编码'),
        'factory_id': fields.Integer(description='所属工厂 ID'),
        'sort_order': fields.Integer(description='排序值'),
        'status': fields.Integer(description='状态'),
        'remark': fields.String(description='备注'),
        'create_time': fields.String(description='创建时间'),
        'update_time': fields.String(description='更新时间'),
    },
)

color_list_data = build_page_data_model(color_ns, 'ColorListData', color_item_model, items_description='颜色列表')
color_list_response = build_page_response_model(color_ns, 'ColorListResponse', base_response, color_list_data, '颜色分页数据')
color_item_response = build_item_response_model(color_ns, 'ColorItemResponse', base_response, color_item_model, '颜色详情数据')

color_create_model = color_ns.model(
    'ColorCreate',
    {
        'name': fields.String(required=True, description='颜色名称', example='红色'),
        'actual_name': fields.String(required=True, description='实际颜色名称', example='大红'),
        'code': fields.String(required=True, description='颜色编码', example='RED'),
        'sort_order': fields.Integer(description='排序', default=0, example=0),
        'remark': fields.String(description='备注', example='常用颜色'),
    },
)

color_update_model = color_ns.model(
    'ColorUpdate',
    {
        'name': fields.String(description='颜色名称', example='酒红'),
        'actual_name': fields.String(description='实际颜色名称', example='深酒红'),
        'sort_order': fields.Integer(description='排序', example=10),
        'status': fields.Integer(description='状态', choices=[0, 1], example=1),
        'remark': fields.String(description='备注', example='客户指定颜色'),
    },
)

color_schema = ColorSchema()
colors_schema = ColorSchema(many=True)
color_create_schema = ColorCreateSchema()
color_update_schema = ColorUpdateSchema()


def get_color_request_context(query_factory_id=None, require_write=False):
    """统一解析颜色接口的当前用户与工厂上下文。"""
    return get_factory_request_context(
        query_factory_id=query_factory_id,
        require_write=require_write,
        allow_internal_without_factory=True,
        allow_internal_write_without_factory=True,
    )


@color_ns.route('')
class ColorList(Resource):
    @login_required
    @button_permission(PERM_BASE_COLOR_QUERY)
    @color_ns.expect(color_query_parser)
    @color_ns.response(200, '成功', color_list_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    @color_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询颜色分页列表接口，支持按名称、状态和工厂可见范围筛选。"""
        args = color_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = get_color_request_context(args.get('factory_id'))
        if error_response_data:
            return error_response_data

        result = ColorService.get_color_list(current_user, current_factory_id, args)
        return success_schema_page(result, color_schema)

    @login_required
    @button_permission(PERM_BASE_COLOR_ADD)
    @color_ns.expect(color_create_model)
    @color_ns.response(201, '创建成功', color_item_response)
    @color_ns.response(400, '参数错误', error_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    @color_ns.response(403, '无权限', forbidden_response)
    @color_ns.response(409, '颜色已存在', error_response)
    def post(self):
        """创建颜色接口，用于新增系统颜色或工厂自定义颜色。"""
        current_user, current_factory_id, error_response_data = get_color_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(color_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        color, error = ColorService.create_color(current_user, current_factory_id, data)
        if error:
            return business_error(error)

        return ApiResponse.success(serialize_schema(color_schema, color), '创建成功', 201)


@color_ns.route('/<int:color_id>')
class ColorDetail(Resource):
    @login_required
    @button_permission(PERM_BASE_COLOR_QUERY)
    @color_ns.response(200, '成功', color_item_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    @color_ns.response(403, '无权限', forbidden_response)
    @color_ns.response(404, '颜色不存在', error_response)
    def get(self, color_id):
        """查询颜色详情接口，返回单个颜色完整信息。"""
        current_user, current_factory_id, error_response_data = get_color_request_context()
        if error_response_data:
            return error_response_data

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在', 404)

        has_permission, error = ColorService.check_permission(current_user, current_factory_id, color)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(serialize_schema(color_schema, color))

    @login_required
    @button_permission(PERM_BASE_COLOR_EDIT)
    @color_ns.expect(color_update_model)
    @color_ns.response(200, '更新成功', color_item_response)
    @color_ns.response(400, '参数错误', error_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    @color_ns.response(403, '无权限', forbidden_response)
    @color_ns.response(404, '颜色不存在', error_response)
    def patch(self, color_id):
        """更新颜色接口，可修改颜色名称、别名、排序和状态。"""
        current_user, current_factory_id, error_response_data = get_color_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在', 404)

        can_manage, error = ColorService.check_manage_permission(current_user, current_factory_id, color)
        if not can_manage:
            return ApiResponse.error(error, 403)

        data, validation_error = load_json_or_error(color_update_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        color, error = ColorService.update_color(color, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(color_schema, color), '更新成功')

    @login_required
    @button_permission(PERM_BASE_COLOR_DELETE)
    @color_ns.response(200, '删除成功', base_response)
    @color_ns.response(401, '未登录', unauthorized_response)
    @color_ns.response(403, '无权限', forbidden_response)
    @color_ns.response(404, '颜色不存在', error_response)
    def delete(self, color_id):
        """删除颜色接口，用于移除未被业务引用的颜色数据。"""
        current_user, current_factory_id, error_response_data = get_color_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        color = ColorService.get_color_by_id(color_id)
        if not color:
            return ApiResponse.error('颜色不存在', 404)

        can_manage, error = ColorService.check_manage_permission(current_user, current_factory_id, color)
        if not can_manage:
            return ApiResponse.error(error, 403)

        ColorService.delete_color(color)
        return ApiResponse.success(message='删除成功')
