"""款号橡筋管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.business.style_elastic import (
    StyleElasticSchema, StyleElasticCreateSchema, StyleElasticUpdateSchema
)
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, StyleElasticService

style_elastic_ns = Namespace('style-elastics', description='款号橡筋管理')

shared = get_shared_models(style_elastic_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
style_elastic_query_parser = style_elastic_ns.parser()
style_elastic_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_elastic_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_elastic_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_elastic_query_parser.add_argument('size_id', type=int, location='args', help='尺码ID')
style_elastic_query_parser.add_argument('grouped', type=int, location='args', default=0, help='是否按橡筋种类分组')

# ========== 响应模型 ==========
elastic_detail_model = style_elastic_ns.model('ElasticDetail', {
    'id': fields.Integer(),
    'size_id': fields.Integer(),
    'size_name': fields.String(),
    'length': fields.Float(),
    'quantity': fields.Integer(),
    'remark': fields.String()
})

elastic_group_model = style_elastic_ns.model('ElasticGroup', {
    'elastic_type': fields.String(),
    'details': fields.List(fields.Nested(elastic_detail_model))
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
    'update_time': fields.String()
})

style_elastic_list_data = style_elastic_ns.model('StyleElasticListData', {
    'items': fields.List(fields.Nested(style_elastic_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_elastic_grouped_data = style_elastic_ns.model('StyleElasticGroupedData', {
    'items': fields.List(fields.Nested(elastic_group_model))
})

style_elastic_list_response = style_elastic_ns.clone('StyleElasticListResponse', base_response, {
    'data': fields.Nested(style_elastic_list_data)
})

style_elastic_grouped_response = style_elastic_ns.clone('StyleElasticGroupedResponse', base_response, {
    'data': fields.Nested(style_elastic_grouped_data)
})

style_elastic_item_response = style_elastic_ns.clone('StyleElasticItemResponse', base_response, {
    'data': fields.Nested(style_elastic_item_model)
})

# ========== Schema 初始化 ==========
style_elastic_schema = StyleElasticSchema()
style_elastics_schema = StyleElasticSchema(many=True)
style_elastic_create_schema = StyleElasticCreateSchema()
style_elastic_update_schema = StyleElasticUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@style_elastic_ns.route('')
class StyleElasticList(Resource):
    @login_required
    @style_elastic_ns.expect(style_elastic_query_parser)
    @style_elastic_ns.response(200, '成功', style_elastic_list_response)
    @style_elastic_ns.response(200, '分组成功', style_elastic_grouped_response)
    @style_elastic_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_elastic_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']
        grouped = args.get('grouped', 0)

        # 验证权限
        style, error = StyleElasticService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        # 分组返回
        if grouped == 1:
            items = StyleElasticService.get_elastic_grouped(style_id)
            return ApiResponse.success(items)

        # 列表分页返回
        page = args['page']
        page_size = args['page_size']
        size_id = args.get('size_id')

        result = StyleElasticService.get_elastic_list(style_id, {
            'page': page,
            'page_size': page_size,
            'size_id': size_id
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
            'pages': result['pages']
        })

    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticCreate', {
        'style_id': fields.Integer(required=True, description='款号ID'),
        'size_id': fields.Integer(description='尺码ID'),
        'elastic_type': fields.String(required=True, description='橡筋种类'),
        'elastic_length': fields.Float(required=True, description='橡筋长度(cm)'),
        'quantity': fields.Integer(description='数量', default=1),
        'remark': fields.String(description='备注')
    }))
    @style_elastic_ns.response(201, '创建成功', style_elastic_item_response)
    @style_elastic_ns.response(400, '参数错误', error_response)
    @style_elastic_ns.response(403, '无权限', error_response)
    @style_elastic_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_elastic_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        # 验证款号权限
        style, error = StyleElasticService.check_style_permission(current_user, data['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        # 验证尺码
        if data.get('size_id'):
            size, error = StyleElasticService.validate_size(data['size_id'])
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
        'style_id': fields.Integer(required=True, description='款号ID'),
        'items': fields.List(fields.Nested(style_elastic_ns.model('ElasticGroupItem', {
            'elastic_type': fields.String(required=True, description='橡筋种类'),
            'details': fields.List(fields.Nested(style_elastic_ns.model('ElasticDetailItem', {
                'size_id': fields.Integer(required=True, description='尺码ID'),
                'length': fields.Float(required=True, description='长度(cm)'),
                'quantity': fields.Integer(description='数量', default=1),
                'remark': fields.String(description='备注')
            })), required=True)
        })), required=True)
    }))
    @style_elastic_ns.response(200, '批量保存成功', base_response)
    @style_elastic_ns.response(400, '参数错误', error_response)
    @style_elastic_ns.response(403, '无权限', error_response)
    def post(self):
        """批量保存橡筋需求（先删除旧数据，再创建新数据）"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        data = request.get_json()
        style_id = data.get('style_id')
        items = data.get('items', [])

        if not style_id:
            return ApiResponse.error('请指定款号ID', 400)

        # 验证款号权限
        style, error = StyleElasticService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        # 删除该款号下所有橡筋记录
        StyleElasticService.delete_by_style(style_id)

        # 批量创建
        if items:
            StyleElasticService.create_elastic_batch(style_id, items)

        return ApiResponse.success(message='保存成功')


@style_elastic_ns.route('/<int:elastic_id>')
class StyleElasticDetail(Resource):
    @login_required
    @style_elastic_ns.response(200, '成功', style_elastic_item_response)
    @style_elastic_ns.response(404, '不存在', error_response)
    def get(self, elastic_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        elastic = StyleElasticService.get_elastic_by_id(elastic_id)
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')

        # 验证权限
        has_permission, error = StyleElasticService.check_elastic_permission(current_user, elastic)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = style_elastic_schema.dump(elastic)
        result['size_name'] = StyleElasticService.get_size_name(elastic.size_id)

        return ApiResponse.success(result)

    @login_required
    @style_elastic_ns.expect(style_elastic_ns.model('StyleElasticUpdate', {
        'size_id': fields.Integer(description='尺码ID'),
        'elastic_type': fields.String(description='橡筋种类'),
        'elastic_length': fields.Float(description='橡筋长度(cm)'),
        'quantity': fields.Integer(description='数量'),
        'remark': fields.String(description='备注')
    }))
    @style_elastic_ns.response(200, '更新成功', style_elastic_item_response)
    @style_elastic_ns.response(404, '不存在', error_response)
    def put(self, elastic_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        elastic = StyleElasticService.get_elastic_by_id(elastic_id)
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')

        # 验证权限
        has_permission, error = StyleElasticService.check_elastic_permission(current_user, elastic)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = style_elastic_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        # 验证尺码
        if data.get('size_id'):
            size, error = StyleElasticService.validate_size(data['size_id'])
            if error:
                return ApiResponse.error(error, 400)

        elastic = StyleElasticService.update_elastic(elastic, data)

        result = style_elastic_schema.dump(elastic)
        result['size_name'] = StyleElasticService.get_size_name(elastic.size_id)

        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_elastic_ns.response(200, '删除成功', base_response)
    @style_elastic_ns.response(404, '不存在', error_response)
    def delete(self, elastic_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        elastic = StyleElasticService.get_elastic_by_id(elastic_id)
        if not elastic:
            return ApiResponse.error('橡筋记录不存在')

        # 验证权限
        has_permission, error = StyleElasticService.check_elastic_permission(current_user, elastic)
        if not has_permission:
            return ApiResponse.error(error, 403)

        StyleElasticService.delete_elastic(elastic)

        return ApiResponse.success(message='删除成功')
