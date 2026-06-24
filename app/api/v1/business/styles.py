"""款号管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.constants.permissions import (
    PERM_BUSINESS_STYLE_ADD,
    PERM_BUSINESS_STYLE_DELETE,
    PERM_BUSINESS_STYLE_EDIT,
    PERM_BUSINESS_STYLE_QUERY,
)
from app.api.common.business_resource_helpers import (
    get_accessible_business_resource_or_error,
    get_business_request_context,
)
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.api.common.response_helpers import load_json_or_error, success_mapped_page
from app.api.common.serializers import build_mapping_serializer, serialize_schema
from app.schemas.business.style import StyleCreateSchema, StyleSchema, StyleUpdateSchema
from app.services import StyleService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_ns = Namespace('款号管理-styles', description='款号管理')

common = get_common_models(style_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

style_query_parser = page_parser.copy()
style_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID')
style_query_parser.add_argument('style_no', type=str, location='args', help='款号')
style_query_parser.add_argument('name', type=str, location='args', help='款号名称')
style_query_parser.add_argument('category_id', type=int, location='args', help='分类 ID')
style_query_parser.add_argument('gender', type=str, location='args', help='性别')
style_query_parser.add_argument('season', type=str, location='args', help='季节')
style_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

style_option_query_parser = new_query_parser()
style_option_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID')
style_option_query_parser.add_argument('style_no', type=str, location='args', help='款号')
style_option_query_parser.add_argument('name', type=str, location='args', help='款号名称')
style_option_query_parser.add_argument('category_id', type=int, location='args', help='分类 ID')
style_option_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

style_splice_item_model = style_ns.model('StyleSpliceItem', {
    'sequence': fields.Integer(description='拼接节位顺序', example=1),
    'description': fields.String(description='拼接节位描述', example='红色棉麻'),
})

style_item_model = style_ns.model('StyleItem', {
    'id': fields.Integer(description='款号 ID'),
    'factory_id': fields.Integer(description='所属工厂 ID'),
    'style_no': fields.String(description='内部款号'),
    'customer_style_no': fields.String(description='客户款号'),
    'name': fields.String(description='款号名称'),
    'category_id': fields.Integer(description='分类 ID'),
    'category_name': fields.String(description='分类名称'),
    'gender': fields.String(description='性别'),
    'season': fields.String(description='季节'),
    'material': fields.String(description='材质'),
    'description': fields.String(description='款号描述'),
    'status': fields.Integer(description='状态'),
    'images': fields.List(fields.String(), description='款号图片列表'),
    'need_cutting': fields.Integer(description='是否需要裁床预留'),
    'cutting_reserve': fields.Float(description='裁床预留值'),
    'custom_attributes': fields.Raw(
        description='自定义属性对象，键为属性名，值建议使用字符串、数字、布尔等标量',
        example={'fabric': '棉麻', 'pattern': '条纹'},
    ),
    'is_splice': fields.Integer(description='是否为拼接款'),
    'splice_data': fields.List(fields.Nested(style_splice_item_model), description='拼接结构列表'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_option_model = style_ns.model('StyleOptionItem', {
    'id': fields.Integer(description='款号 ID', example=1),
    'style_no': fields.String(description='款号', example='1235#'),
    'name': fields.String(description='款号名称', example='圆领短袖'),
    'customer_style_no': fields.String(description='客户款号', example='C-1235'),
    'category_id': fields.Integer(description='分类 ID', example=1),
    'category_name': fields.String(description='分类名称', example='针织'),
    'status': fields.Integer(description='状态', example=1),
})

style_list_data = build_page_data_model(style_ns, 'StyleListData', style_item_model, items_description='款号列表')
style_list_response = build_page_response_model(style_ns, 'StyleListResponse', base_response, style_list_data, '款号分页数据')
style_item_response = style_ns.clone('StyleItemResponse', base_response, {
    'data': fields.Nested(style_item_model, description='款号详情数据'),
})
style_options_response = style_ns.clone('StyleOptionsResponse', base_response, {
    'data': fields.List(fields.Nested(style_option_model), description='款号下拉选项列表'),
})

style_create_model = style_ns.model('StyleCreate', {
    'style_no': fields.String(required=True, description='款号', example='1235#'),
    'customer_style_no': fields.String(description='客户款号', example='C-1235'),
    'name': fields.String(description='款号名称', example='圆领短袖'),
    'category_id': fields.Integer(description='分类 ID', example=1),
    'gender': fields.String(description='性别', example='unisex'),
    'season': fields.String(description='季节', example='summer'),
    'material': fields.String(description='材质', example='棉麻'),
    'description': fields.String(description='描述', example='V1 基础款'),
    'images': fields.List(fields.String(), description='图片列表', example=['/uploads/styles/1235-1.jpg']),
    'need_cutting': fields.Integer(description='是否需要裁床预留', default=0, example=0),
    'cutting_reserve': fields.Float(description='裁床预留值', default=0, example=0),
    'custom_attributes': fields.Raw(
        description='自定义属性对象，键为属性名，值建议使用字符串、数字、布尔等标量',
        example={'fabric': '棉麻', 'pattern': '条纹'},
    ),
    'is_splice': fields.Integer(description='是否为拼接款', default=0, example=1),
    'splice_data': fields.List(
        fields.Nested(style_splice_item_model),
        description='拼接数据列表',
        example=[{'sequence': 1, 'description': '红色'}, {'sequence': 2, 'description': '黄色'}],
    ),
})

style_update_model = style_ns.model('StyleUpdate', {
    'style_no': fields.String(description='款号', example='1235#'),
    'customer_style_no': fields.String(description='客户款号', example='C-1235'),
    'name': fields.String(description='款号名称', example='圆领短袖升级版'),
    'category_id': fields.Integer(description='分类 ID', example=1),
    'gender': fields.String(description='性别', example='unisex'),
    'season': fields.String(description='季节', example='summer'),
    'material': fields.String(description='材质', example='棉麻'),
    'description': fields.String(description='描述', example='更新后的说明'),
    'status': fields.Integer(description='状态', choices=[0, 1], example=1),
    'images': fields.List(fields.String(), description='图片列表', example=['/uploads/styles/1235-1.jpg']),
    'need_cutting': fields.Integer(description='是否需要裁床预留', example=1),
    'cutting_reserve': fields.Float(description='裁床预留值', example=0.5),
    'custom_attributes': fields.Raw(
        description='自定义属性对象，键为属性名，值建议使用字符串、数字、布尔等标量',
        example={'fabric': '棉麻', 'pattern': '条纹'},
    ),
    'is_splice': fields.Integer(description='是否为拼接款', example=1),
    'splice_data': fields.List(
        fields.Nested(style_splice_item_model),
        description='拼接数据列表',
        example=[{'sequence': 1, 'description': '红色'}, {'sequence': 2, 'description': '黄色'}],
    ),
})

style_schema = StyleSchema()
style_create_schema = StyleCreateSchema()
style_update_schema = StyleUpdateSchema()


def get_style_request_context(query_factory_id=None, require_write=False, allow_internal_without_factory=False):
    """获取款号接口通用的当前用户与工厂上下文。"""
    return get_business_request_context(
        query_factory_id=query_factory_id,
        require_write=require_write,
        allow_internal_without_factory=allow_internal_without_factory,
    )


def get_accessible_style_or_error(style_id):
    """查询当前上下文可访问的款号，不可访问时返回统一错误响应。"""
    return get_accessible_business_resource_or_error(
        style_id,
        StyleService.get_style_by_id,
        StyleService.check_permission,
        '款号不存在',
        allow_internal_without_factory=True,
    )


def _enrich_style_payload(payload, style):
    """补充款号接口需要的分类名称字段。"""
    payload['category_name'] = style.category.name if style.category else None
    return payload


def serialize_style(style):
    """序列化单个款号，并补充分类型名称。"""
    return serialize_schema(style_schema, style, enricher=_enrich_style_payload)


serialize_style_option = build_mapping_serializer(
    {
        'id': 'id',
        'style_no': 'style_no',
        'name': 'name',
        'customer_style_no': 'customer_style_no',
        'category_id': 'category_id',
        'category_name': lambda style: style.category.name if style.category else None,
        'status': 'status',
    }
)


@style_ns.route('')
class StyleList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_QUERY)
    @style_ns.expect(style_query_parser)
    @style_ns.response(200, '成功', style_list_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询款号分页列表接口，支持按款号、名称、客户款号和分类筛选。"""
        args = style_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = get_style_request_context(
            query_factory_id=args.get('factory_id'),
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        result = StyleService.get_style_list(current_user, current_factory_id, args)
        return success_mapped_page(result, [serialize_style(style) for style in result['items']])

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ADD)
    @style_ns.expect(style_create_model)
    @style_ns.response(201, '创建成功', style_item_response)
    @style_ns.response(400, '参数错误', error_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(409, '款号已存在', error_response)
    def post(self):
        """创建款号接口，支持维护图片、自定义属性和拼接配置。"""
        current_user, current_factory_id, error_response_data = get_style_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(style_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        style, error = StyleService.create_style(current_user, current_factory_id, data, style_schema)
        if error:
            status_code = 409 if '已存在' in error else 403 if '权限' in error or '管理员' in error else 400
            return ApiResponse.error(error, status_code)

        return ApiResponse.success(serialize_style(style), '创建成功', 201)


@style_ns.route('/options')
class StyleOptions(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_QUERY)
    @style_ns.expect(style_option_query_parser)
    @style_ns.response(200, '成功', style_options_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询款号下拉选项接口，供款号选择器直接使用。"""
        args = style_option_query_parser.parse_args()
        current_user, current_factory_id, error_response_data = get_style_request_context(
            query_factory_id=args.get('factory_id'),
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        styles = StyleService.get_style_options(current_user, current_factory_id, args)
        return ApiResponse.success_list([serialize_style_option(style) for style in styles])


@style_ns.route('/<int:style_id>')
class StyleDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_QUERY)
    @style_ns.response(200, '成功', style_item_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(404, '款号不存在', error_response)
    def get(self, style_id):
        """查询款号详情接口，返回款号基础信息、图片和扩展属性。"""
        _, _, style, error_response_data = get_accessible_style_or_error(style_id)
        if error_response_data:
            return error_response_data

        return ApiResponse.success(serialize_style(style))

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_EDIT)
    @style_ns.expect(style_update_model)
    @style_ns.response(200, '更新成功', style_item_response)
    @style_ns.response(400, '参数错误', error_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(404, '款号不存在', error_response)
    @style_ns.response(409, '款号冲突', error_response)
    def patch(self, style_id):
        """更新款号接口，可调整基础信息、图片、自定义属性和拼接数据。"""
        current_user, current_factory_id, style, error_response_data = get_accessible_style_or_error(style_id)
        if error_response_data:
            return error_response_data

        can_manage, error = StyleService.check_manage_permission(current_user, current_factory_id, style)
        if not can_manage:
            return ApiResponse.error(error, 403)

        data, validation_error = load_json_or_error(style_update_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        style, error = StyleService.update_style(style, data, current_factory_id)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(serialize_style(style), '更新成功')

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_DELETE)
    @style_ns.response(200, '删除成功', base_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(404, '款号不存在', error_response)
    @style_ns.response(409, '款号已被引用', error_response)
    def delete(self, style_id):
        """删除款号接口，已被业务引用的款号不允许删除。"""
        current_user, current_factory_id, style, error_response_data = get_accessible_style_or_error(style_id)
        if error_response_data:
            return error_response_data

        can_manage, error = StyleService.check_manage_permission(current_user, current_factory_id, style)
        if not can_manage:
            return ApiResponse.error(error, 403)

        success, error = StyleService.delete_style(style)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')
