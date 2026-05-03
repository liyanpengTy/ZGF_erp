"""工序管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.business.process import (
    ProcessSchema, ProcessCreateSchema, ProcessUpdateSchema,
    StyleProcessMappingSchema, StyleProcessMappingCreateSchema
)
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, ProcessService

process_ns = Namespace('工序管理-processes', description='工序管理')

shared = get_shared_models(process_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']

# ========== 请求解析器 ==========
process_query_parser = process_ns.parser()
process_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
process_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
process_query_parser.add_argument('name', type=str, location='args', help='工序名称')
process_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

# ========== 响应模型 ==========
process_item_model = process_ns.model('ProcessItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'code': fields.String(),
    'description': fields.String(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

process_list_data = process_ns.model('ProcessListData', {
    'items': fields.List(fields.Nested(process_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

process_list_response = process_ns.clone('ProcessListResponse', base_response, {
    'data': fields.Nested(process_list_data)
})

process_item_response = process_ns.clone('ProcessItemResponse', base_response, {
    'data': fields.Nested(process_item_model)
})

# 款号工序模型
style_process_item_model = process_ns.model('StyleProcessItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'process_id': fields.Integer(),
    'process_name': fields.String(),
    'process_code': fields.String(),
    'sequence': fields.Integer(),
    'remark': fields.String()
})

style_process_list_response = process_ns.clone('StyleProcessListResponse', base_response, {
    'data': fields.List(fields.Nested(style_process_item_model))
})

style_process_item_response = process_ns.clone('StyleProcessItemResponse', base_response, {
    'data': fields.Nested(style_process_item_model)
})

# ========== Schema 初始化 ==========
process_schema = ProcessSchema()
processes_schema = ProcessSchema(many=True)
process_create_schema = ProcessCreateSchema()
process_update_schema = ProcessUpdateSchema()
style_process_mapping_schema = StyleProcessMappingSchema()
style_process_mapping_create_schema = StyleProcessMappingCreateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    return AuthService.get_current_user()


# ========== 工序定义接口 ==========
@process_ns.route('')
class ProcessList(Resource):
    @login_required
    @process_ns.expect(process_query_parser)
    @process_ns.response(200, '成功', process_list_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """工序列表"""
        args = process_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = ProcessService.get_process_list(args)

        return ApiResponse.success({
            'items': processes_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @process_ns.expect(process_ns.model('ProcessCreate', {
        'name': fields.String(required=True, description='工序名称'),
        'code': fields.String(required=True, description='工序编码'),
        'description': fields.String(description='工序描述'),
        'sort_order': fields.Integer(description='排序', default=0)
    }))
    @process_ns.response(201, '创建成功', process_item_response)
    @process_ns.response(400, '参数错误', error_response)
    @process_ns.response(409, '工序编码已存在', error_response)
    def post(self):
        """创建工序"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以创建工序
        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建工序', 403)

        try:
            data = process_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        process, error = ProcessService.create_process(data)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(process_schema.dump(process), '创建成功', 201)


@process_ns.route('/<int:process_id>')
class ProcessDetail(Resource):
    @login_required
    @process_ns.response(200, '成功', process_item_response)
    @process_ns.response(404, '不存在', error_response)
    def get(self, process_id):
        """工序详情"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        process = ProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工序不存在')

        return ApiResponse.success(process_schema.dump(process))

    @login_required
    @process_ns.expect(process_ns.model('ProcessUpdate', {
        'name': fields.String(description='工序名称'),
        'description': fields.String(description='工序描述'),
        'sort_order': fields.Integer(description='排序'),
        'status': fields.Integer(description='状态', choices=[0, 1])
    }))
    @process_ns.response(200, '更新成功', process_item_response)
    @process_ns.response(404, '不存在', error_response)
    def patch(self, process_id):
        """更新工序"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以更新工序', 403)

        process = ProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工序不存在')

        try:
            data = process_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        process, error = ProcessService.update_process(process, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(process_schema.dump(process), '更新成功')

    @login_required
    @process_ns.response(200, '删除成功', base_response)
    @process_ns.response(404, '不存在', error_response)
    @process_ns.response(409, '被引用无法删除', error_response)
    def delete(self, process_id):
        """删除工序"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除工序', 403)

        process = ProcessService.get_process_by_id(process_id)
        if not process:
            return ApiResponse.error('工序不存在')

        success, error = ProcessService.delete_process(process)
        if not success:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(message='删除成功')


@process_ns.route('/enabled')
class EnabledProcesses(Resource):
    @login_required
    @process_ns.response(200, '成功', base_response)
    @process_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """获取所有启用的工序（用于下拉选择）"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        processes = ProcessService.get_all_enabled_processes()

        return ApiResponse.success(processes_schema.dump(processes))


# ========== 款号工序关联接口 ==========
@process_ns.route('/styles/<int:style_id>/processes')
class StyleProcesses(Resource):
    @login_required
    @process_ns.response(200, '成功', style_process_list_response)
    @process_ns.response(404, '款号不存在', error_response)
    def get(self, style_id):
        """获取款号的工序列表"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 验证权限
        style, error = ProcessService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        mappings = ProcessService.get_style_processes(style_id)

        return ApiResponse.success(style_process_mapping_schema.dump(mappings, many=True))

    @login_required
    @process_ns.expect(process_ns.model('StyleProcessBatchSave', {
        'mappings': fields.List(fields.Nested(process_ns.model('StyleProcessItemCreate', {
            'process_id': fields.Integer(required=True, description='工序ID'),
            'sequence': fields.Integer(description='工序顺序', default=1),
            'remark': fields.String(description='备注')
        })), required=True, description='工序列表')
    }))
    @process_ns.response(200, '保存成功', style_process_list_response)
    @process_ns.response(404, '款号不存在', error_response)
    def post(self, style_id):
        """批量保存款号工序（全量替换）"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 验证权限
        style, error = ProcessService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        data = request.get_json()
        mappings_data = data.get('mappings', [])

        mappings = ProcessService.batch_save_style_processes(style_id, mappings_data)

        return ApiResponse.success(
            style_process_mapping_schema.dump(mappings, many=True),
            '保存成功'
        )


@process_ns.route('/styles/<int:style_id>/processes/<int:mapping_id>')
class StyleProcessDetail(Resource):
    @login_required
    @process_ns.response(200, '删除成功', base_response)
    @process_ns.response(404, '不存在', error_response)
    def delete(self, style_id, mapping_id):
        """删除款号工序"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 验证款号权限
        style, error = ProcessService.check_style_permission(current_user, style_id)
        if error:
            return ApiResponse.error(error, 403 if '无权限' in error else 404)

        mapping = ProcessService.get_style_process_mapping_by_id(mapping_id)
        if not mapping or mapping.style_id != style_id:
            return ApiResponse.error('工序关联不存在')

        ProcessService.delete_style_process(mapping)

        return ApiResponse.success(message='删除成功')
