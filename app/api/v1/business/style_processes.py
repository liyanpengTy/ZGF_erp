"""款号工艺管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.business.style_process import StyleProcessCreateSchema, StyleProcessSchema, StyleProcessUpdateSchema
from app.services import StyleProcessService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

style_process_ns = Namespace('款号工艺管理-style-processes', description='款号工艺管理')

common = get_common_models(style_process_ns)
base_response = common['base_response']
unauthorized_response = common['unauthorized_response']

style_process_query_parser = page_parser.copy()
style_process_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号 ID')
style_process_query_parser.add_argument('process_type', type=str, location='args', help='工艺类型', choices=['embroidery', 'print', 'other'])

style_process_item_model = style_process_ns.model('StyleProcessItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'process_type': fields.String(),
    'process_type_label': fields.String(),
    'process_name': fields.String(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String(),
})

style_process_list_data = style_process_ns.model('StyleProcessListData', {
    'items': fields.List(fields.Nested(style_process_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer(),
})

style_process_list_response = style_process_ns.clone('StyleProcessListResponse', base_response, {'data': fields.Nested(style_process_list_data)})
style_process_item_response = style_process_ns.clone('StyleProcessItemResponse', base_response, {'data': fields.Nested(style_process_item_model)})

style_process_schema = StyleProcessSchema()
style_process_create_schema = StyleProcessCreateSchema()
style_process_update_schema = StyleProcessUpdateSchema()


@style_process_ns.route('')
class StyleProcessList(Resource):
    @login_required
    @style_process_ns.expect(style_process_query_parser)
    @style_process_ns.response(200, '成功', style_process_list_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询指定款号下的工艺记录。"""
        args = style_process_query_parser.parse_args()
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        style, error = StyleProcessService.check_style_permission(current_factory_id, args['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        result = StyleProcessService.get_process_list(style.id, args)
        items = []
        for process in result['items']:
            item = style_process_schema.dump(process)
            items.append(StyleProcessService.enrich_with_label(item, process))

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @style_process_ns.expect(style_process_ns.model('StyleProcessCreate', {
        'style_id': fields.Integer(required=True, description='款号 ID'),
        'process_type': fields.String(required=True, description='工艺类型', choices=['embroidery', 'print', 'other']),
        'process_name': fields.String(description='工艺名称'),
        'remark': fields.String(description='备注'),
    }))
    @style_process_ns.response(201, '创建成功', style_process_item_response)
    def post(self):
        """为指定款号新增工艺记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_process_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        _, error = StyleProcessService.check_style_permission(current_factory_id, data['style_id'])
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error or '切换' in error else 404)

        process = StyleProcessService.create_process(data)
        result = style_process_schema.dump(process)
        return ApiResponse.success(StyleProcessService.enrich_with_label(result, process), '创建成功', 201)


@style_process_ns.route('/<int:process_id>')
class StyleProcessDetail(Resource):
    @login_required
    @style_process_ns.response(200, '成功', style_process_item_response)
    def get(self, process_id):
        """查看单条款号工艺记录详情。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')
        process = StyleProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工艺记录不存在')
        has_permission, error = StyleProcessService.check_process_permission(current_factory_id, process)
        if not has_permission:
            return ApiResponse.error(error, 403)
        result = style_process_schema.dump(process)
        return ApiResponse.success(StyleProcessService.enrich_with_label(result, process))

    @login_required
    @style_process_ns.expect(style_process_ns.model('StyleProcessUpdate', {
        'process_type': fields.String(description='工艺类型', choices=['embroidery', 'print', 'other']),
        'process_name': fields.String(description='工艺名称'),
        'remark': fields.String(description='备注'),
    }))
    @style_process_ns.response(200, '更新成功', style_process_item_response)
    def patch(self, process_id):
        """更新单条款号工艺记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')
        process = StyleProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工艺记录不存在')
        has_permission, error = StyleProcessService.check_process_permission(current_factory_id, process)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = style_process_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        process = StyleProcessService.update_process(process, data)
        result = style_process_schema.dump(process)
        return ApiResponse.success(StyleProcessService.enrich_with_label(result, process), '更新成功')

    @login_required
    @style_process_ns.response(200, '删除成功', base_response)
    def delete(self, process_id):
        """删除单条款号工艺记录。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')
        process = StyleProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工艺记录不存在')
        has_permission, error = StyleProcessService.check_process_permission(current_factory_id, process)
        if not has_permission:
            return ApiResponse.error(error, 403)
        StyleProcessService.delete_process(process)
        return ApiResponse.success(message='删除成功')
