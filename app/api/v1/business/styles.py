"""款号管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.business.style import StyleCreateSchema, StyleSchema, StyleUpdateSchema
from app.services import StyleService
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
style_query_parser.add_argument('style_no', type=str, location='args', help='款号')
style_query_parser.add_argument('name', type=str, location='args', help='款号名称')
style_query_parser.add_argument('category_id', type=int, location='args', help='分类 ID')
style_query_parser.add_argument('gender', type=str, location='args', help='性别')
style_query_parser.add_argument('season', type=str, location='args', help='季节')
style_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

style_splice_item_model = style_ns.model('StyleSpliceItem', {
    'sequence': fields.Integer(description='拼接顺序', example=1),
    'description': fields.String(description='拼接描述', example='红色棉麻'),
})

style_item_model = style_ns.model('StyleItem', {
    'id': fields.Integer(description='款号ID'),
    'factory_id': fields.Integer(description='所属工厂ID'),
    'style_no': fields.String(description='内部款号'),
    'customer_style_no': fields.String(description='客户款号'),
    'name': fields.String(description='款号名称'),
    'category_id': fields.Integer(description='分类ID'),
    'category_name': fields.String(description='分类名称'),
    'gender': fields.String(description='性别'),
    'season': fields.String(description='季节'),
    'material': fields.String(description='材质'),
    'description': fields.String(description='款号描述'),
    'status': fields.Integer(description='状态'),
    'images': fields.List(fields.String(), description='款号图片列表'),
    'need_cutting': fields.Integer(description='是否需要裁床预留'),
    'cutting_reserve': fields.Float(description='裁床预留值'),
    'custom_attributes': fields.Raw(description='自定义属性键值对象，键为属性名，值建议使用字符串、数字、布尔等标量', example={'fabric': '棉麻', 'pattern': '条纹'}),
    'is_splice': fields.Integer(description='是否拼接款'),
    'splice_data': fields.List(fields.Nested(style_splice_item_model), description='拼接结构列表'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_list_data = build_page_data_model(style_ns, 'StyleListData', style_item_model, items_description='款号列表')
style_list_response = build_page_response_model(style_ns, 'StyleListResponse', base_response, style_list_data, '款号分页数据')
style_item_response = style_ns.clone('StyleItemResponse', base_response, {
    'data': fields.Nested(style_item_model, description='款号详情数据')
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
    'custom_attributes': fields.Raw(description='自定义属性对象，键为属性名，值建议使用字符串、数字、布尔等标量', example={'fabric': '棉麻', 'pattern': '条纹'}),
    'is_splice': fields.Integer(description='是否拼接款', default=0, example=1),
    'splice_data': fields.List(fields.Nested(style_splice_item_model), description='拼接数据列表', example=[{'sequence': 1, 'description': '红色'}, {'sequence': 2, 'description': '黄色'}]),
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
    'custom_attributes': fields.Raw(description='自定义属性对象，键为属性名，值建议使用字符串、数字、布尔等标量', example={'fabric': '棉麻', 'pattern': '条纹'}),
    'is_splice': fields.Integer(description='是否拼接款', example=1),
    'splice_data': fields.List(fields.Nested(style_splice_item_model), description='拼接数据列表', example=[{'sequence': 1, 'description': '红色'}, {'sequence': 2, 'description': '黄色'}]),
})

style_schema = StyleSchema()
styles_schema = StyleSchema(many=True)
style_create_schema = StyleCreateSchema()
style_update_schema = StyleUpdateSchema()


@style_ns.route('')
class StyleList(Resource):
    @login_required
    @style_ns.expect(style_query_parser)
    @style_ns.response(200, '成功', style_list_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询款号分页列表。"""
        args = style_query_parser.parse_args()
        current_user = get_current_user()
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
    @style_ns.expect(style_create_model)
    @style_ns.response(201, '创建成功', style_item_response)
    @style_ns.response(400, '参数错误', error_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(409, '款号已存在', error_response)
    def post(self):
        """创建款号。"""
        current_factory_id = get_current_factory_id()
        if not get_current_user():
            return ApiResponse.error('用户不存在')

        try:
            data = style_create_schema.load(request.get_json() or {})
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
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(404, '款号不存在', error_response)
    def get(self, style_id):
        """查询款号详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        current_user = get_current_user()
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
    @style_ns.expect(style_update_model)
    @style_ns.response(200, '更新成功', style_item_response)
    @style_ns.response(400, '参数错误', error_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(404, '款号不存在', error_response)
    @style_ns.response(409, '款号冲突', error_response)
    def patch(self, style_id):
        """更新款号。"""
        current_factory_id = get_current_factory_id()
        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')
        if not StyleService.check_manage_permission(get_current_user(), current_factory_id, style)[0]:
            return ApiResponse.error('只能修改自己工厂的款号', 403)

        try:
            data = style_update_schema.load(request.get_json() or {})
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
    @style_ns.response(401, '未登录', unauthorized_response)
    @style_ns.response(403, '无权限', forbidden_response)
    @style_ns.response(404, '款号不存在', error_response)
    @style_ns.response(409, '款号已被引用', error_response)
    def delete(self, style_id):
        """删除款号。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        style = StyleService.get_style_by_id(style_id)
        if not style:
            return ApiResponse.error('款号不存在')
        if not StyleService.check_manage_permission(get_current_user(), current_factory_id, style)[0]:
            return ApiResponse.error('只能删除自己工厂的款号', 403)
        success, error = StyleService.delete_style(style)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')
