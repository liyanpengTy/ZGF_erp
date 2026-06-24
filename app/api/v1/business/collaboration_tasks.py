"""主体协作任务接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import Schema, fields as ma_fields, validate

from app.api.common.business_resource_helpers import get_business_request_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.api.common.response_helpers import load_json_or_error, success_mapped_page
from app.constants.identity import (
    COLLABORATION_STATUS_ACCEPTED,
    COLLABORATION_STATUS_COMPLETED,
    COLLABORATION_STATUS_IN_PROGRESS,
    COLLABORATION_STATUS_PENDING,
)
from app.services import CollaborationTaskService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

collaboration_task_ns = Namespace('协作任务-collaboration-tasks', description='协作任务')

common = get_common_models(collaboration_task_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']
build_item_response_model = common['build_item_response_model']

COLLABORATION_STATUS_CHOICES = [
    COLLABORATION_STATUS_PENDING,
    COLLABORATION_STATUS_ACCEPTED,
    COLLABORATION_STATUS_IN_PROGRESS,
    COLLABORATION_STATUS_COMPLETED,
]


class CollaborationTaskCreateSchema(Schema):
    """创建协作任务入参。"""

    to_subject_id = ma_fields.Int(required=True, validate=validate.Range(min=1))
    source_order_id = ma_fields.Int(required=True, validate=validate.Range(min=1))
    process_name = ma_fields.Str(required=True, validate=validate.Length(min=1, max=100))
    quantity = ma_fields.Int(required=True, validate=validate.Range(min=1))
    deliver_at = ma_fields.Str(validate=validate.Regexp(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'))
    remark = ma_fields.Str(validate=validate.Length(max=500))


class CollaborationTaskStatusSchema(Schema):
    """更新协作任务状态入参。"""

    status = ma_fields.Str(required=True, validate=validate.OneOf(COLLABORATION_STATUS_CHOICES))


collaboration_task_create_schema = CollaborationTaskCreateSchema()
collaboration_task_status_schema = CollaborationTaskStatusSchema()

collaboration_task_query_parser = page_parser.copy()
collaboration_task_query_parser.add_argument(
    'factory_id',
    type=int,
    location='args',
    help='主体 ID；平台内部人员可传入指定主体过滤',
)
collaboration_task_query_parser.add_argument(
    'direction',
    type=str,
    location='args',
    help='任务方向',
    choices=['all', 'inbound', 'outbound'],
)
collaboration_task_query_parser.add_argument(
    'status',
    type=str,
    location='args',
    help='协作状态',
    choices=COLLABORATION_STATUS_CHOICES,
)
collaboration_task_query_parser.add_argument('source_order_id', type=int, location='args', help='原始订单 ID')

collaboration_task_item_model = collaboration_task_ns.model('CollaborationTaskItem', {
    'id': fields.Integer(description='协作任务 ID', example=1),
    'from_subject_id': fields.Integer(description='发起主体 ID', example=1),
    'from_subject_name': fields.String(description='发起主体名称', example='测试工厂'),
    'to_subject_id': fields.Integer(description='接收主体 ID', example=2),
    'to_subject_name': fields.String(description='接收主体名称', example='专机钉扣店'),
    'source_order_id': fields.Integer(description='原始订单 ID', example=10),
    'source_order_no': fields.String(description='原始订单号', example='ORD1202606050001'),
    'process_name': fields.String(description='协作工序名称', example='钉扣'),
    'quantity': fields.Integer(description='协作数量', example=100),
    'deliver_at': fields.String(description='交付时间', example='2026-06-10T18:00:00'),
    'status': fields.String(description='状态', example='pending'),
    'remark': fields.String(description='备注', example='加急处理'),
    'create_time': fields.String(description='创建时间', example='2026-06-05T10:00:00'),
    'update_time': fields.String(description='更新时间', example='2026-06-05T10:00:00'),
})

collaboration_task_create_model = collaboration_task_ns.model('CollaborationTaskCreate', {
    'to_subject_id': fields.Integer(required=True, description='接收主体 ID', example=2),
    'source_order_id': fields.Integer(required=True, description='原始订单 ID', example=10),
    'process_name': fields.String(required=True, description='协作工序名称', example='钉扣'),
    'quantity': fields.Integer(required=True, description='协作数量', example=100),
    'deliver_at': fields.String(description='交付时间，格式 yyyy-MM-dd HH:mm:ss', example='2026-06-10 18:00:00'),
    'remark': fields.String(description='备注', example='加急处理'),
})

collaboration_task_status_model = collaboration_task_ns.model('CollaborationTaskStatusUpdate', {
    'status': fields.String(
        required=True,
        description='协作任务状态',
        choices=COLLABORATION_STATUS_CHOICES,
        example='accepted',
    ),
})

collaboration_task_page_data = build_page_data_model(
    collaboration_task_ns,
    'CollaborationTaskPageData',
    collaboration_task_item_model,
    items_description='协作任务列表',
)
collaboration_task_page_response = build_page_response_model(
    collaboration_task_ns,
    'CollaborationTaskPageResponse',
    base_response,
    collaboration_task_page_data,
    '协作任务分页数据',
)
collaboration_task_item_response = build_item_response_model(
    collaboration_task_ns,
    'CollaborationTaskItemResponse',
    base_response,
    collaboration_task_item_model,
    '协作任务详情',
)


def get_accessible_collaboration_task_or_error(task_id):
    """查询当前上下文可访问的协作任务。"""
    raw_factory_id = request.args.get('factory_id')
    try:
        query_factory_id = int(raw_factory_id) if raw_factory_id not in (None, '') else None
    except ValueError:
        return None, None, None, ApiResponse.error('factory_id 必须为整数', 400)

    current_user, current_subject_id, error_response_data = get_business_request_context(
        query_factory_id=query_factory_id,
        allow_internal_without_factory=True,
    )
    if error_response_data:
        return None, None, None, error_response_data

    task = CollaborationTaskService.get_accessible_task(current_user, current_subject_id, task_id)
    if not task:
        return None, None, None, ApiResponse.error('协作任务不存在', 404)
    return current_user, current_subject_id, task, None


@collaboration_task_ns.route('')
class CollaborationTaskList(Resource):
    @login_required
    @collaboration_task_ns.expect(collaboration_task_query_parser)
    @collaboration_task_ns.response(200, '成功', collaboration_task_page_response)
    @collaboration_task_ns.response(401, '未登录', unauthorized_response)
    @collaboration_task_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询协作任务列表接口，按发起主体和接收主体进行数据隔离。"""
        args = collaboration_task_query_parser.parse_args()
        current_user, current_subject_id, error_response_data = get_business_request_context(
            query_factory_id=args.get('factory_id'),
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        result = CollaborationTaskService.get_task_list(current_user, current_subject_id, args)
        items = [CollaborationTaskService.serialize_task(task) for task in result['items']]
        return success_mapped_page(result, items)

    @login_required
    @collaboration_task_ns.expect(collaboration_task_create_model)
    @collaboration_task_ns.response(201, '创建成功', collaboration_task_item_response)
    @collaboration_task_ns.response(400, '参数错误', error_response)
    @collaboration_task_ns.response(401, '未登录', unauthorized_response)
    @collaboration_task_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """创建协作任务接口，由当前主体向其他主体派发工序任务。"""
        current_user, current_subject_id, error_response_data = get_business_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(collaboration_task_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        task, error = CollaborationTaskService.create_task(current_user, current_subject_id, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(CollaborationTaskService.serialize_task(task), '创建成功', 201)


@collaboration_task_ns.route('/<int:task_id>')
class CollaborationTaskDetail(Resource):
    @login_required
    @collaboration_task_ns.response(200, '成功', collaboration_task_item_response)
    @collaboration_task_ns.response(401, '未登录', unauthorized_response)
    @collaboration_task_ns.response(403, '无权限', forbidden_response)
    @collaboration_task_ns.response(404, '协作任务不存在', error_response)
    def get(self, task_id):
        """查询协作任务详情接口。"""
        _, _, task, error_response_data = get_accessible_collaboration_task_or_error(task_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(CollaborationTaskService.serialize_task(task))

    @login_required
    @collaboration_task_ns.response(200, '删除成功', base_response)
    @collaboration_task_ns.response(401, '未登录', unauthorized_response)
    @collaboration_task_ns.response(403, '无权限', forbidden_response)
    @collaboration_task_ns.response(404, '协作任务不存在', error_response)
    def delete(self, task_id):
        """删除协作任务接口，仅逻辑删除当前可访问任务。"""
        _, _, task, error_response_data = get_accessible_collaboration_task_or_error(task_id)
        if error_response_data:
            return error_response_data
        CollaborationTaskService.delete_task(task)
        return ApiResponse.success(message='删除成功')


@collaboration_task_ns.route('/<int:task_id>/status')
class CollaborationTaskStatus(Resource):
    @login_required
    @collaboration_task_ns.expect(collaboration_task_status_model)
    @collaboration_task_ns.response(200, '更新成功', collaboration_task_item_response)
    @collaboration_task_ns.response(400, '参数错误', error_response)
    @collaboration_task_ns.response(401, '未登录', unauthorized_response)
    @collaboration_task_ns.response(403, '无权限', forbidden_response)
    @collaboration_task_ns.response(404, '协作任务不存在', error_response)
    def post(self, task_id):
        """更新协作任务状态接口，支持 pending、accepted、in_progress、completed。"""
        _, _, task, error_response_data = get_accessible_collaboration_task_or_error(task_id)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(collaboration_task_status_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        task, error = CollaborationTaskService.update_task_status(task, data['status'])
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(CollaborationTaskService.serialize_task(task), '更新成功')
