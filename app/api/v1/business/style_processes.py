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
error_response = common['error_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

style_process_query_parser = page_parser.copy()
style_process_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号 ID')
style_process_query_parser.add_argument('process_type', type=str, location='args', help='工艺类型', choices=['embroidery', 'print', 'other'])

style_process_item_model = style_process_ns.model('StyleProcessItem', {
    'id': fields.Integer(description='工艺记录ID'),
    'style_id': fields.Integer(description='款号ID'),
    'process_type': fields.String(description='工艺类型'),
    'process_type_label': fields.String(description='工艺类型名称'),
    'process_name': fields.String(description='工艺名称'),
    'remark': fields.String(description='备注'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

style_process_list_data = build_page_data_model(style_process_ns, 'StyleProcessListData', style_process_item_model, items_description='工艺列表')
style_process_list_response = build_page_response_model(style_process_ns, 'StyleProcessListResponse', base_response, style_process_list_data, '工艺分页数据')
style_process_item_response = style_process_ns.clone('StyleProcessItemResponse', base_response, {
    'data': fields.Nested(style_process_item_model, description='工艺详情数据')
})

style_process_create_model = style_process_ns.model('StyleProcessCreate', {
    'style_id': fields.Integer(required=True, description='款号 ID', example=1),
    'process_type': fields.String(required=True, description='工艺类型', choices=['embroidery', 'print', 'other'], example='print'),
    'process_name': fields.String(description='工艺名称', example='丝网印花'),
    'remark': fields.String(description='备注', example='前胸图案'),
})

style_process_update_model = style_process_ns.model('StyleProcessUpdate', {
    'process_type': fields.String(description='工艺类型', choices=['embroidery', 'print', 'other'], example='embroidery'),
    'process_name': fields.String(description='工艺名称', example='电脑绣花'),
    'remark': fields.String(description='备注', example='左胸 logo'),
})

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
        """查询款号工艺分页列表。"""
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
    @style_process_ns.expect(style_process_create_model)
    @style_process_ns.response(201, '创建成功', style_process_item_response)
    @style_process_ns.response(400, '参数错误', error_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '款号不存在', error_response)
    def post(self):
        """创建款号工艺记录。"""
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
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '工艺记录不存在', error_response)
    def get(self, process_id):
        """查询款号工艺详情。"""
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
    @style_process_ns.expect(style_process_update_model)
    @style_process_ns.response(200, '更新成功', style_process_item_response)
    @style_process_ns.response(400, '参数错误', error_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '工艺记录不存在', error_response)
    def patch(self, process_id):
        """更新款号工艺记录。"""
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
    @style_process_ns.response(401, '未登录', unauthorized_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '工艺记录不存在', error_response)
    def delete(self, process_id):
        """删除款号工艺记录。"""
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
