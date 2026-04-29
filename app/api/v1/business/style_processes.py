"""款号工艺管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.business.style_process import (
    StyleProcessSchema, StyleProcessCreateSchema, StyleProcessUpdateSchema
)
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, StyleProcessService

style_process_ns = Namespace('style-processes', description='款号工艺管理')

shared = get_shared_models(style_process_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
style_process_query_parser = style_process_ns.parser()
style_process_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_process_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_process_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_process_query_parser.add_argument('process_type', type=str, location='args', help='工艺类型',
                                        choices=['embroidery', 'print', 'other'])

# ========== 响应模型 ==========
style_process_item_model = style_process_ns.model('StyleProcessItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'process_type': fields.String(),
    'process_type_label': fields.String(),
    'process_name': fields.String(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_process_list_data = style_process_ns.model('StyleProcessListData', {
    'items': fields.List(fields.Nested(style_process_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_process_list_response = style_process_ns.clone('StyleProcessListResponse', base_response, {
    'data': fields.Nested(style_process_list_data)
})

style_process_item_response = style_process_ns.clone('StyleProcessItemResponse', base_response, {
    'data': fields.Nested(style_process_item_model)
})

# ========== Schema 初始化 ==========
style_process_schema = StyleProcessSchema()
style_processes_schema = StyleProcessSchema(many=True)
style_process_create_schema = StyleProcessCreateSchema()
style_process_update_schema = StyleProcessUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@style_process_ns.route('')
class StyleProcessList(Resource):
    @login_required
    @style_process_ns.expect(style_process_query_parser)
    @style_process_ns.response(200, '成功', style_process_list_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_process_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']

        # 验证权限
        style, error = StyleProcessService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        result = StyleProcessService.get_process_list(style_id, args)

        items = []
        for process in result['items']:
            item = style_process_schema.dump(process)
            item = StyleProcessService.enrich_with_label(item, process)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @style_process_ns.expect(style_process_ns.model('StyleProcessCreate', {
        'style_id': fields.Integer(required=True, description='款号ID'),
        'process_type': fields.String(required=True, description='工艺类型',
                                      choices=['embroidery', 'print', 'other']),
        'process_name': fields.String(description='工艺名称'),
        'remark': fields.String(description='备注')
    }))
    @style_process_ns.response(201, '创建成功', style_process_item_response)
    @style_process_ns.response(400, '参数错误', error_response)
    @style_process_ns.response(403, '无权限', error_response)
    @style_process_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_process_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        # 验证权限
        style, error = StyleProcessService.check_style_permission(current_user, data['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        process = StyleProcessService.create_process(data)

        result = style_process_schema.dump(process)
        result = StyleProcessService.enrich_with_label(result, process)

        return ApiResponse.success(result, '创建成功', 201)


@style_process_ns.route('/<int:process_id>')
class StyleProcessDetail(Resource):
    @login_required
    @style_process_ns.response(200, '成功', style_process_item_response)
    @style_process_ns.response(404, '不存在', error_response)
    def get(self, process_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        process = StyleProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工艺记录不存在')

        # 验证权限
        has_permission, error = StyleProcessService.check_process_permission(current_user, process)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = style_process_schema.dump(process)
        result = StyleProcessService.enrich_with_label(result, process)

        return ApiResponse.success(result)

    @login_required
    @style_process_ns.expect(style_process_ns.model('StyleProcessUpdate', {
        'process_type': fields.String(description='工艺类型', choices=['embroidery', 'print', 'other']),
        'process_name': fields.String(description='工艺名称'),
        'remark': fields.String(description='备注')
    }))
    @style_process_ns.response(200, '更新成功', style_process_item_response)
    @style_process_ns.response(404, '不存在', error_response)
    def put(self, process_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        process = StyleProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工艺记录不存在')

        # 验证权限
        has_permission, error = StyleProcessService.check_process_permission(current_user, process)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = style_process_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        process = StyleProcessService.update_process(process, data)

        result = style_process_schema.dump(process)
        result = StyleProcessService.enrich_with_label(result, process)

        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_process_ns.response(200, '删除成功', base_response)
    @style_process_ns.response(404, '不存在', error_response)
    def delete(self, process_id):
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        process = StyleProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工艺记录不存在')

        # 验证权限
        has_permission, error = StyleProcessService.check_process_permission(current_user, process)
        if not has_permission:
            return ApiResponse.error(error, 403)

        StyleProcessService.delete_process(process)

        return ApiResponse.success(message='删除成功')
