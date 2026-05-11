"""款号管理接口"""
from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.business.style import StyleCreateSchema, StyleSchema, StyleUpdateSchema
from app.services import AuthService, StyleService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_ns = Namespace('款号管理-styles', description='款号管理')

common = get_common_models(style_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']

style_query_parser = page_parser.copy()
style_query_parser.add_argument('style_no', type=str, location='args', help='款号')
style_query_parser.add_argument('name', type=str, location='args', help='款号名称')
style_query_parser.add_argument('category_id', type=int, location='args', help='分类ID')
style_query_parser.add_argument('gender', type=str, location='args', help='性别')
style_query_parser.add_argument('season', type=str, location='args', help='季节')
style_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

style_item_model = style_ns.model('StyleItem', {
    'id': fields.Integer(),
    'factory_id': fields.Integer(),
    'style_no': fields.String(),
    'customer_style_no': fields.String(),
    'name': fields.String(),
    'category_id': fields.Integer(),
    'category_name': fields.String(),
    'gender': fields.String(),
    'season': fields.String(),
    'material': fields.String(),
    'description': fields.String(),
    'status': fields.Integer(),
    'images': fields.List(fields.String()),
    'need_cutting': fields.Integer(),
    'cutting_reserve': fields.Float(),
    'custom_attributes': fields.Raw(),
    'is_splice': fields.Integer(),
    'splice_data': fields.List(fields.Raw()),
    'create_time': fields.String(),
    'update_time': fields.String(),
})

style_list_data = style_ns.model('StyleListData', {
    'items': fields.List(fields.Nested(style_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer(),
})

style_list_response = style_ns.clone('StyleListResponse', base_response, {'data': fields.Nested(style_list_data)})
style_item_response = style_ns.clone('StyleItemResponse', base_response, {'data': fields.Nested(style_item_model)})

style_schema = StyleSchema()
styles_schema = StyleSchema(many=True)
style_create_schema = StyleCreateSchema()
style_update_schema = StyleUpdateSchema()


def get_current_user():
    return AuthService.get_current_user()


def get_current_factory_id():
    return AuthService.get_current_factory_id()


@style_ns.route('')
class StyleList(Resource):
    @login_required
    @style_ns.expect(style_query_parser)
    @style_ns.response(200, '成功', style_list_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = StyleService.get_style_list(current_factory_id, args)
        items = []
        for style in result['items']:
            item = style_schema.dump(style)
            item['category_name'] = StyleService.get_category_name(style.category_id)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @style_ns.expect(style_ns.model('StyleCreate', {
        'style_no': fields.String(required=True, description='款号'),
        'customer_style_no': fields.String(description='客户款号'),
        'name': fields.String(description='款号名称'),
        'category_id': fields.Integer(description='分类ID'),
        'gender': fields.String(description='性别'),
        'season': fields.String(description='季节'),
        'material': fields.String(description='材质'),
        'description': fields.String(description='描述'),
        'images': fields.List(fields.String(), description='图片列表'),
        'need_cutting': fields.Integer(description='是否需要裁切', default=0),
        'cutting_reserve': fields.Float(description='裁切预留', default=0),
        'custom_attributes': fields.Raw(description='自定义属性'),
        'is_splice': fields.Integer(description='是否拼接款', default=0),
        'splice_data': fields.List(fields.Raw(), description='拼接数据'),
    }))
    @style_ns.response(201, '创建成功', style_item_response)
    def post(self):
        current_factory_id = get_current_factory_id()
        if not get_current_user():
            return ApiResponse.error('用户不存在')

        try:
            data = style_create_schema.load(request.get_json())
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        style, error = StyleService.create_style(current_factory_id, data, style_schema)
        if error:
            return ApiResponse.error(error, 409 if '已存在' in error else 400)

        result = style_schema.dump(style)
        result['category_name'] = StyleService.get_category_name(style.category_id)
        return ApiResponse.success(result, '创建成功', 201)


@style_ns.route('/<int:style_id>')
class StyleDetail(Resource):
    @login_required
    @style_ns.response(200, '成功', style_item_response)
    def get(self, style_id):
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')

        has_permission, error = StyleService.check_permission(current_user, current_factory_id, style)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = style_schema.dump(style)
        result['category_name'] = StyleService.get_category_name(style.category_id)
        return ApiResponse.success(result)

    @login_required
    @style_ns.expect(style_ns.model('StyleUpdate', {
        'style_no': fields.String(description='款号'),
        'customer_style_no': fields.String(description='客户款号'),
        'name': fields.String(description='款号名称'),
        'category_id': fields.Integer(description='分类ID'),
        'gender': fields.String(description='性别'),
        'season': fields.String(description='季节'),
        'material': fields.String(description='材质'),
        'description': fields.String(description='描述'),
        'status': fields.Integer(description='状态', choices=[0, 1]),
        'images': fields.List(fields.String(), description='图片列表'),
        'need_cutting': fields.Integer(description='是否需要裁切'),
        'cutting_reserve': fields.Float(description='裁切预留'),
        'custom_attributes': fields.Raw(description='自定义属性'),
        'is_splice': fields.Integer(description='是否拼接款'),
        'splice_data': fields.List(fields.Raw(), description='拼接数据'),
    }))
    @style_ns.response(200, '更新成功', style_item_response)
    def patch(self, style_id):
        current_factory_id = get_current_factory_id()
        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')
        if style.factory_id != current_factory_id:
            return ApiResponse.error('只能修改自己工厂的款号', 403)

        try:
            data = style_update_schema.load(request.get_json())
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        style, error = StyleService.update_style(style, data, current_factory_id)
        if error:
            return ApiResponse.error(error, 409)

        result = style_schema.dump(style)
        result['category_name'] = StyleService.get_category_name(style.category_id)
        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_ns.response(200, '删除成功', base_response)
    def delete(self, style_id):
        current_factory_id = get_current_factory_id()
        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')
        if style.factory_id != current_factory_id:
            return ApiResponse.error('只能删除自己工厂的款号', 403)
        success, error = StyleService.delete_style(style)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')
