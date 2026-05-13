"""款号橡筋管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.business.style_elastic import StyleElasticCreateSchema, StyleElasticSchema, StyleElasticUpdateSchema
from app.services import StyleElasticService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_elastic_ns = Namespace('款号橡筋管理-style-elastics', description='款号橡筋管理')

common = get_common_models(style_elastic_ns)
base_response = common['base_response']
unauthorized_response = common['unauthorized_response']

style_elastic_query_parser = page_parser.copy()
style_elastic_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号 ID')
style_elastic_query_parser.add_argument('size_id', type=int, location='args', help='尺码 ID')
style_elastic_query_parser.add_argument('grouped', type=int, location='args', default=0, help='是否按类型分组返回', choices=[0, 1])

elastic_detail_model = style_elastic_ns.model('ElasticDetail', {
    'id': fields.Integer(),
    'size_id': fields.Integer(),
    'size_name': fields.String(),
    'length': fields.Float(),
    'quantity': fields.Integer(),
    'remark': fields.String(),
})

elastic_group_model = style_elastic_ns.model('ElasticGroup', {
    'elastic_type': fields.String(),
    'details': fields.List(fields.Nested(elastic_detail_model)),
})

style_elastic_item_model = style_elastic_ns.model('StyleElasticItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'size_id': fields.Integer(),
    'size_name': fields.String(),
    'elastic_type': fields.String(),
    'elastic_length': fields.Float(),
    'quantity': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String(),
})

style_elastic_list_data = style_elastic_ns.model('StyleElasticListData', {
    'items': fields.List(fields.Nested(style_elastic_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer(),
})

style_elastic_grouped_data = style_elastic_ns.model('StyleElasticGroupedData', {
    'items': fields.List(fields.Nested(elastic_group_model)),
})

style_elastic_list_response = style_elastic_ns.clone('StyleElasticListResponse', base_response, {'data': fields.Nested(style_elastic_list_data)})
style_elastic_grouped_response = style_elastic_ns.clone('StyleElasticGroupedResponse', base_response, {'data': fields.Nested(style_elastic_grouped_data)})
style_elastic_item_response = style_elastic_ns.clone('StyleElasticItemResponse', base_response, {'data': fields.Nested(style_elastic_item_model)})

style_elastic_schema = StyleElasticSchema()
style_elastic_create_schema = StyleElasticCreateSchema()
style_elastic_update_schema = StyleElasticUpdateSchema()


@style_elastic_ns.route('')
class StyleElasticList(Resource):
    @login_required
    @style_elastic_ns.expect(style_elastic_query_parser)
    @style_elastic_ns.response(200, '成功', style_elastic_list_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询指定款号下的橡筋记录，支持分页或按类型分组。"""
        args = style_elastic_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        style, error = StyleElasticService.check_style_permission(current_factory_id, args['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        if args.get('grouped', 0) == 1:
            items = StyleElasticService.get_elastic_grouped(style.id)
            return ApiResponse.success(items)

        result = StyleElasticService.get_elastic_list(style.id, {
            'page': args['page'],
            'page_size': args['page_size'],
            'size_id': args.get('size_id'),
        })
        items = []
        for elastic in result['items']:
            item = style_elastic_schema.dump(elastic)
            item['size_name'] = StyleElasticService.get_size_name(elastic.size_id)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticCreate', {
        'style_id': fields.Integer(required=True, description='款号 ID'),
        'size_id': fields.Integer(description='尺码 ID'),
        'elastic_type': fields.String(required=True, description='橡筋类型'),
        'elastic_length': fields.Float(required=True, description='橡筋长度(cm)'),
        'quantity': fields.Integer(description='数量', default=1),
        'remark': fields.String(description='备注'),
    }))
    @style_elastic_ns.response(201, '创建成功', style_elastic_item_response)
    def post(self):
        """新增单条款号橡筋记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_elastic_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        _, error = StyleElasticService.check_style_permission(current_factory_id, data['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        if data.get('size_id'):
            _, error = StyleElasticService.validate_size(data['size_id'])
            if error:
                return ApiResponse.error(error, 400)

        elastic = StyleElasticService.create_elastic(data)
        result = style_elastic_schema.dump(elastic)
        result['size_name'] = StyleElasticService.get_size_name(elastic.size_id)
        return ApiResponse.success(result, '创建成功', 201)


@style_elastic_ns.route('/batch')
class StyleElasticBatch(Resource):
    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticBatchCreate', {
        'style_id': fields.Integer(required=True, description='款号 ID'),
        'items': fields.List(fields.Nested(style_elastic_ns.model('ElasticGroupItem', {
            'elastic_type': fields.String(required=True, description='橡筋类型'),
            'details': fields.List(fields.Nested(style_elastic_ns.model('ElasticDetailItem', {
                'size_id': fields.Integer(required=True, description='尺码 ID'),
                'length': fields.Float(required=True, description='长度(cm)'),
                'quantity': fields.Integer(description='数量', default=1),
                'remark': fields.String(description='备注'),
            })), required=True),
        })), required=True),
    }))
    @style_elastic_ns.response(200, '保存成功', base_response)
    def post(self):
        """按分组批量覆盖保存指定款号的橡筋配置。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')

        data = request.get_json() or {}
        style_id = data.get('style_id')
        items = data.get('items', [])
        if not style_id:
            return ApiResponse.error('请指定款号 ID', 400)

        _, error = StyleElasticService.check_style_permission(current_factory_id, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        StyleElasticService.delete_by_style(style_id)
        if items:
            StyleElasticService.create_elastic_batch(style_id, items)

        return ApiResponse.success(message='保存成功')


@style_elastic_ns.route('/<int:elastic_id>')
class StyleElasticDetail(Resource):
    @login_required
    @style_elastic_ns.response(200, '成功', style_elastic_item_response)
    def get(self, elastic_id):
        """查看单条款号橡筋记录详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')
        elastic = StyleElasticService.get_elastic_by_id(elastic_id)
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')
        has_permission, error = StyleElasticService.check_elastic_permission(current_factory_id, elastic)
        if not has_permission:
            return ApiResponse.error(error, 403)
        result = style_elastic_schema.dump(elastic)
        result['size_name'] = StyleElasticService.get_size_name(elastic.size_id)
        return ApiResponse.success(result)

    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticUpdate', {
        'size_id': fields.Integer(description='尺码 ID'),
        'elastic_type': fields.String(description='橡筋类型'),
        'elastic_length': fields.Float(description='橡筋长度(cm)'),
        'quantity': fields.Integer(description='数量'),
        'remark': fields.String(description='备注'),
    }))
    @style_elastic_ns.response(200, '更新成功', style_elastic_item_response)
    def patch(self, elastic_id):
        """更新单条款号橡筋记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')
        elastic = StyleElasticService.get_elastic_by_id(elastic_id)
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')
        has_permission, error = StyleElasticService.check_elastic_permission(current_factory_id, elastic)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = style_elastic_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        if data.get('size_id'):
            _, error = StyleElasticService.validate_size(data['size_id'])
            if error:
                return ApiResponse.error(error, 400)

        elastic = StyleElasticService.update_elastic(elastic, data)
        result = style_elastic_schema.dump(elastic)
        result['size_name'] = StyleElasticService.get_size_name(elastic.size_id)
        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_elastic_ns.response(200, '删除成功', base_response)
    def delete(self, elastic_id):
        """删除单条款号橡筋记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')
        elastic = StyleElasticService.get_elastic_by_id(elastic_id)
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')
        has_permission, error = StyleElasticService.check_elastic_permission(current_factory_id, elastic)
        if not has_permission:
            return ApiResponse.error(error, 403)
        StyleElasticService.delete_elastic(elastic)
        return ApiResponse.success(message='删除成功')
