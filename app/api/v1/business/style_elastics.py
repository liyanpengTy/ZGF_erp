"""款号橡筋管理接口。"""

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
    PERM_BUSINESS_STYLE_ELASTIC_ADD,
    PERM_BUSINESS_STYLE_ELASTIC_DELETE,
    PERM_BUSINESS_STYLE_ELASTIC_EDIT,
    PERM_BUSINESS_STYLE_ELASTIC_QUERY,
)
from app.schemas.business.style_elastic import (
    StyleElasticBatchCreateSchema,
    StyleElasticCreateSchema,
    StyleElasticSchema,
    StyleElasticUpdateSchema,
)
from app.services import StyleElasticService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_elastic_ns = Namespace('款号橡筋管理-style-elastics', description='款号橡筋配置查询与维护')

common = get_common_models(style_elastic_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']
build_item_response_model = common['build_item_response_model']

style_elastic_query_parser = page_parser.copy()
style_elastic_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号 ID')
style_elastic_query_parser.add_argument('size_id', type=int, location='args', help='尺码 ID')
style_elastic_query_parser.add_argument(
    'grouped',
    type=int,
    location='args',
    default=0,
    help='是否按橡筋类型分组返回',
    choices=[0, 1],
)

elastic_detail_model = style_elastic_ns.model('ElasticDetail', {
    'id': fields.Integer(description='明细 ID'),
    'size_id': fields.Integer(description='尺码 ID'),
    'size_name': fields.String(description='尺码名称'),
    'length': fields.Float(description='长度'),
    'quantity': fields.Integer(description='数量'),
    'remark': fields.String(description='备注'),
})

elastic_group_model = style_elastic_ns.model('ElasticGroup', {
    'elastic_type': fields.String(description='橡筋类型'),
    'details': fields.List(fields.Nested(elastic_detail_model), description='橡筋明细列表'),
})

style_elastic_item_model = style_elastic_ns.model('StyleElasticItem', {
    'id': fields.Integer(description='记录 ID'),
    'style_id': fields.Integer(description='款号 ID'),
    'size_id': fields.Integer(description='尺码 ID'),
    'size_name': fields.String(description='尺码名称'),
    'elastic_type': fields.String(description='橡筋类型'),
    'elastic_length': fields.Float(description='橡筋长度'),
    'quantity': fields.Integer(description='数量'),
    'remark': fields.String(description='备注'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_elastic_list_data = build_page_data_model(
    style_elastic_ns,
    'StyleElasticListData',
    style_elastic_item_model,
    items_description='橡筋列表',
)
style_elastic_grouped_data = style_elastic_ns.model('StyleElasticGroupedData', {
    'items': fields.List(fields.Nested(elastic_group_model), description='分组后的橡筋列表'),
})
style_elastic_list_response = build_page_response_model(
    style_elastic_ns,
    'StyleElasticListResponse',
    base_response,
    style_elastic_list_data,
    '橡筋分页数据',
)
style_elastic_grouped_response = style_elastic_ns.clone('StyleElasticGroupedResponse', base_response, {
    'data': fields.Nested(style_elastic_grouped_data, description='橡筋分组数据'),
})
style_elastic_item_response = build_item_response_model(style_elastic_ns, 'StyleElasticItemResponse', base_response, style_elastic_item_model, '橡筋详情数据')

elastic_detail_item_create_model = style_elastic_ns.model('ElasticDetailItem', {
    'size_id': fields.Integer(required=True, description='尺码 ID'),
    'length': fields.Float(required=True, description='长度(cm)'),
    'quantity': fields.Integer(description='数量', default=1),
    'remark': fields.String(description='备注'),
})

elastic_group_item_create_model = style_elastic_ns.model('ElasticGroupItem', {
    'elastic_type': fields.String(required=True, description='橡筋类型'),
    'details': fields.List(fields.Nested(elastic_detail_item_create_model), required=True, description='橡筋明细列表'),
})

style_elastic_batch_create_model = style_elastic_ns.model('StyleElasticBatchCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID'),
    'items': fields.List(fields.Nested(elastic_group_item_create_model), required=True, description='橡筋分组列表'),
})

style_elastic_create_model = style_elastic_ns.model('StyleElasticCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'size_id': fields.Integer(description='尺码 ID', example=1),
    'elastic_type': fields.String(required=True, description='橡筋类型', example='waist'),
    'elastic_length': fields.Float(required=True, description='橡筋长度(cm)', example=32.5),
    'quantity': fields.Integer(description='数量', default=1, example=2),
    'remark': fields.String(description='备注', example='腰头橡筋'),
})

style_elastic_update_model = style_elastic_ns.model('StyleElasticUpdate', {
    'size_id': fields.Integer(description='尺码 ID', example=1),
    'elastic_type': fields.String(description='橡筋类型', example='cuff'),
    'elastic_length': fields.Float(description='橡筋长度(cm)', example=18.0),
    'quantity': fields.Integer(description='数量', example=4),
    'remark': fields.String(description='备注', example='袖口橡筋'),
})

style_elastic_schema = StyleElasticSchema()
style_elastic_create_schema = StyleElasticCreateSchema()
style_elastic_update_schema = StyleElasticUpdateSchema()
style_elastic_batch_create_schema = StyleElasticBatchCreateSchema()


def serialize_style_elastic(elastic):
    """序列化款号橡筋记录并补充尺码名称。"""
    result = serialize_schema(style_elastic_schema, elastic)
    result['size_name'] = StyleElasticService.get_size_name(elastic.size_id)
    return result


def get_accessible_style_for_elastic_or_error(style_id, require_write=False):
    """查询当前上下文可访问的款号，用于橡筋记录读写前校验。"""
    return get_accessible_style_or_error(
        style_id,
        StyleElasticService.check_style_permission,
        require_write=require_write,
    )


def get_accessible_elastic_or_error(elastic_id, require_write=False):
    """查询当前上下文可访问的橡筋记录。"""
    return get_accessible_style_resource_or_error(
        elastic_id,
        StyleElasticService.get_elastic_by_id,
        StyleElasticService.check_elastic_permission,
        '橡筋记录不存在',
        require_write=require_write,
    )


def validate_elastic_size_or_error(size_id):
    """校验尺码是否存在，不存在时返回统一错误响应。"""
    if not size_id:
        return None
    _, error = StyleElasticService.validate_size(size_id)
    if error:
        return ApiResponse.error(error, 400)
    return None


def validate_elastic_batch_or_error(items):
    """校验批量橡筋分组中的尺码是否合法。"""
    for group in items or []:
        for detail in group.get('details') or []:
            size_error_response = validate_elastic_size_or_error(detail.get('size_id'))
            if size_error_response:
                return size_error_response
    return None


@style_elastic_ns.route('')
class StyleElasticList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ELASTIC_QUERY)
    @style_elastic_ns.expect(style_elastic_query_parser)
    @style_elastic_ns.response(200, '查询成功', style_elastic_list_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询款号橡筋分页列表接口。平台内部用户可不切工厂直接按款号查询。"""
        args = style_elastic_query_parser.parse_args()
        _, _, style, error_response_data = get_accessible_style_for_elastic_or_error(args['style_id'])
        if error_response_data:
            return error_response_data

        if args.get('grouped', 0) == 1:
            return ApiResponse.success(StyleElasticService.get_elastic_grouped(style.id))

        result = StyleElasticService.get_elastic_list(style.id, {
            'page': args['page'],
            'page_size': args['page_size'],
            'size_id': args.get('size_id'),
        })
        return success_mapped_page(result, [serialize_style_elastic(elastic) for elastic in result['items']])

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ELASTIC_ADD)
    @style_elastic_ns.expect(style_elastic_create_model)
    @style_elastic_ns.response(201, '创建成功', style_elastic_item_response)
    @style_elastic_ns.response(400, '参数错误', error_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    @style_elastic_ns.response(404, '款号不存在', error_response)
    def post(self):
        """创建款号橡筋记录接口。写操作仍要求当前工厂上下文。"""
        data, validation_error = load_json_or_error(style_elastic_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        _, _, _, error_response_data = get_accessible_style_for_elastic_or_error(data['style_id'], require_write=True)
        if error_response_data:
            return error_response_data

        size_error_response = validate_elastic_size_or_error(data.get('size_id'))
        if size_error_response:
            return size_error_response

        elastic = StyleElasticService.create_elastic(data)
        return ApiResponse.success(serialize_style_elastic(elastic), '创建成功', 201)


@style_elastic_ns.route('/batch')
class StyleElasticBatch(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ELASTIC_ADD)
    @style_elastic_ns.expect(style_elastic_batch_create_model)
    @style_elastic_ns.response(200, '保存成功', base_response)
    @style_elastic_ns.response(400, '参数错误', error_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    @style_elastic_ns.response(404, '款号不存在', error_response)
    def post(self):
        """批量保存款号橡筋配置接口。写操作仍要求当前工厂上下文。"""
        data, validation_error = load_json_or_error(style_elastic_batch_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        _, _, _, error_response_data = get_accessible_style_for_elastic_or_error(data['style_id'], require_write=True)
        if error_response_data:
            return error_response_data

        size_error_response = validate_elastic_batch_or_error(data.get('items'))
        if size_error_response:
            return size_error_response

        StyleElasticService.delete_by_style(data['style_id'])
        if data.get('items'):
            StyleElasticService.create_elastic_batch(data['style_id'], data['items'])
        return ApiResponse.success(message='保存成功')


@style_elastic_ns.route('/<int:elastic_id>')
class StyleElasticDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ELASTIC_QUERY)
    @style_elastic_ns.response(200, '查询成功', style_elastic_item_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    @style_elastic_ns.response(404, '橡筋记录不存在', error_response)
    def get(self, elastic_id):
        """查询款号橡筋详情接口。平台内部用户可跨工厂查看。"""
        _, _, elastic, error_response_data = get_accessible_elastic_or_error(elastic_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(serialize_style_elastic(elastic))

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ELASTIC_EDIT)
    @style_elastic_ns.expect(style_elastic_update_model)
    @style_elastic_ns.response(200, '更新成功', style_elastic_item_response)
    @style_elastic_ns.response(400, '参数错误', error_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    @style_elastic_ns.response(404, '橡筋记录不存在', error_response)
    def patch(self, elastic_id):
        """更新款号橡筋记录接口。写操作仍要求当前工厂上下文。"""
        _, _, elastic, error_response_data = get_accessible_elastic_or_error(elastic_id, require_write=True)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(style_elastic_update_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        size_error_response = validate_elastic_size_or_error(data.get('size_id'))
        if size_error_response:
            return size_error_response

        elastic = StyleElasticService.update_elastic(elastic, data)
        return ApiResponse.success(serialize_style_elastic(elastic), '更新成功')

    @login_required
    @button_permission(PERM_BUSINESS_STYLE_ELASTIC_DELETE)
    @style_elastic_ns.response(200, '删除成功', base_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    @style_elastic_ns.response(403, '无权限', forbidden_response)
    @style_elastic_ns.response(404, '橡筋记录不存在', error_response)
    def delete(self, elastic_id):
        """删除款号橡筋记录接口。写操作仍要求当前工厂上下文。"""
        _, _, elastic, error_response_data = get_accessible_elastic_or_error(elastic_id, require_write=True)
        if error_response_data:
            return error_response_data

        StyleElasticService.delete_elastic(elastic)
        return ApiResponse.success(message='删除成功')
