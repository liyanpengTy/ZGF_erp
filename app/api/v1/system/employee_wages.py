"""员工计酬管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.system.employee_wage import EmployeeWageCreateSchema, EmployeeWageSchema, EmployeeWageUpdateSchema
from app.services import EmployeeWageService
from app.utils.permissions import login_required, permission_required
from app.utils.response import ApiResponse

employee_wage_ns = Namespace('员工计酬管理-employee-wages', description='员工计酬管理')

common = get_common_models(employee_wage_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

wage_query_parser = page_parser.copy()
wage_query_parser.add_argument('user_id', type=int, location='args', help='员工ID')
wage_query_parser.add_argument('process_id', type=int, location='args', help='工序ID')
wage_query_parser.add_argument(
    'wage_type',
    type=str,
    location='args',
    help='计酬方式',
    choices=['monthly', 'piece', 'base_piece', 'hourly']
)

employee_wage_item_model = employee_wage_ns.model('EmployeeWageItem', {
    'id': fields.Integer(description='薪资记录ID', example=1),
    'user_id': fields.Integer(description='员工ID', example=2),
    'username': fields.String(description='用户名', example='factory_employee'),
    'nickname': fields.String(description='昵称', example='工厂员工'),
    'process_id': fields.Integer(description='工序ID', example=3),
    'process_name': fields.String(description='工序名称', example='锁边'),
    'wage_type': fields.String(description='计酬方式', example='piece'),
    'wage_type_label': fields.String(description='计酬方式名称', example='计件'),
    'monthly_salary': fields.Float(description='月薪金额', example=None),
    'piece_rate': fields.Float(description='计件单价', example=1.2),
    'base_salary': fields.Float(description='底薪', example=None),
    'base_piece_rate': fields.Float(description='保底计件单价', example=None),
    'hourly_rate': fields.Float(description='计时单价', example=None),
    'effective_date': fields.String(description='生效日期', example='2026-05-01'),
    'remark': fields.String(description='备注', example='夏季工价'),
    'create_time': fields.String(description='创建时间', example='2026-05-01 10:00:00')
})

wage_list_data = build_page_data_model(employee_wage_ns, 'WageListData', employee_wage_item_model, items_description='计酬列表')
wage_list_response = build_page_response_model(employee_wage_ns, 'WageListResponse', base_response, wage_list_data, '计酬分页数据')

wage_item_response = employee_wage_ns.clone('WageItemResponse', base_response, {
    'data': fields.Nested(employee_wage_item_model, description='薪资详情数据')
})

wage_calculate_result_model = employee_wage_ns.model('WageCalculateResult', {
    'user_id': fields.Integer(description='员工ID', example=2),
    'process_id': fields.Integer(description='工序ID', example=3),
    'wage_amount': fields.Float(description='试算工资金额', example=128.5)
})

wage_calculate_response = employee_wage_ns.clone('WageCalculateResponse', base_response, {
    'data': fields.Nested(wage_calculate_result_model, description='试算结果数据')
})

employee_wage_create_model = employee_wage_ns.model('EmployeeWageCreate', {
    'user_id': fields.Integer(required=True, description='员工ID', example=2),
    'process_id': fields.Integer(required=True, description='工序ID', example=3),
    'wage_type': fields.String(required=True, description='计酬方式', choices=['monthly', 'piece', 'base_piece', 'hourly'], example='piece'),
    'monthly_salary': fields.Float(description='月薪金额', example=6000),
    'piece_rate': fields.Float(description='计件单价', example=1.2),
    'base_salary': fields.Float(description='底薪', example=3000),
    'base_piece_rate': fields.Float(description='保底计件单价', example=0.8),
    'hourly_rate': fields.Float(description='计时单价', example=25),
    'effective_date': fields.String(required=True, description='生效日期', example='2026-05-01'),
    'remark': fields.String(description='备注', example='夏季工价')
})

employee_wage_update_model = employee_wage_ns.model('EmployeeWageUpdate', {
    'wage_type': fields.String(description='计酬方式', choices=['monthly', 'piece', 'base_piece', 'hourly'], example='hourly'),
    'monthly_salary': fields.Float(description='月薪金额', example=6500),
    'piece_rate': fields.Float(description='计件单价', example=1.5),
    'base_salary': fields.Float(description='底薪', example=3200),
    'base_piece_rate': fields.Float(description='保底计件单价', example=1.0),
    'hourly_rate': fields.Float(description='计时单价', example=28),
    'effective_date': fields.String(description='生效日期', example='2026-06-01'),
    'remark': fields.String(description='备注', example='更新工价')
})

wage_calculate_model = employee_wage_ns.model('WageCalculate', {
    'user_id': fields.Integer(required=True, description='员工ID', example=2),
    'process_id': fields.Integer(required=True, description='工序ID', example=3),
    'quantity': fields.Integer(description='完成数量', default=0, example=100),
    'work_hours': fields.Float(description='工作小时数', default=0, example=8),
    'work_days': fields.Float(description='工作天数', default=1, example=1),
    'total_work_days': fields.Float(description='当月总工作天数', default=22, example=22),
    'work_date': fields.String(description='工作日期', example='2026-05-15')
})

wage_schema = EmployeeWageSchema()
wages_schema = EmployeeWageSchema(many=True)
wage_create_schema = EmployeeWageCreateSchema()
wage_update_schema = EmployeeWageUpdateSchema()


def check_wage_view_permission(current_user):
    """校验计酬查看权限，允许平台内部人员访问。"""
    if not current_user:
        return False, '用户不存在'
    if not current_user.is_internal_user:
        return False, '无权限查看'
    return True, None


def check_wage_write_permission(current_user):
    """校验计酬写权限，仅平台管理员可维护。"""
    if not current_user:
        return False, '用户不存在'
    if not current_user.is_platform_admin:
        return False, '只有平台管理员可以维护计酬配置'
    return True, None


@employee_wage_ns.route('')
class EmployeeWageList(Resource):
    @login_required
    @permission_required('system:employee_wage:view')
    @employee_wage_ns.expect(wage_query_parser)
    @employee_wage_ns.response(200, '成功', wage_list_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询员工计酬分页列表。"""
        args = wage_query_parser.parse_args()
        current_user = get_current_user()

        has_permission, error = check_wage_view_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = EmployeeWageService.get_wage_list(args)
        return ApiResponse.success({
            'items': wages_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @permission_required('system:employee_wage:add')
    @employee_wage_ns.expect(employee_wage_create_model)
    @employee_wage_ns.response(201, '创建成功', wage_item_response)
    @employee_wage_ns.response(400, '参数错误', error_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    @employee_wage_ns.response(409, '配置已存在', error_response)
    def post(self):
        """创建员工计酬配置。"""
        current_user = get_current_user()
        has_permission, error = check_wage_write_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = wage_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        wage, service_error = EmployeeWageService.create_wage(data)
        if service_error:
            return ApiResponse.error(service_error, 409)

        return ApiResponse.success(wage_schema.dump(wage), '创建成功', 201)


@employee_wage_ns.route('/<int:wage_id>')
class EmployeeWageDetail(Resource):
    @login_required
    @permission_required('system:employee_wage:view')
    @employee_wage_ns.response(200, '成功', wage_item_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(404, '不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def get(self, wage_id):
        """查询计酬配置详情。"""
        current_user = get_current_user()
        has_permission, error = check_wage_view_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        wage = EmployeeWageService.get_wage_by_id(wage_id)
        if not wage:
            return ApiResponse.error('计酬配置不存在')

        return ApiResponse.success(wage_schema.dump(wage))

    @login_required
    @permission_required('system:employee_wage:edit')
    @employee_wage_ns.expect(employee_wage_update_model)
    @employee_wage_ns.response(200, '更新成功', wage_item_response)
    @employee_wage_ns.response(400, '参数错误', error_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(404, '不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def patch(self, wage_id):
        """更新计酬配置。"""
        current_user = get_current_user()
        has_permission, error = check_wage_write_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        wage = EmployeeWageService.get_wage_by_id(wage_id)
        if not wage:
            return ApiResponse.error('计酬配置不存在')

        try:
            data = wage_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        wage, service_error = EmployeeWageService.update_wage(wage, data)
        if service_error:
            return ApiResponse.error(service_error, 400)

        return ApiResponse.success(wage_schema.dump(wage), '更新成功')

    @login_required
    @permission_required('system:employee_wage:delete')
    @employee_wage_ns.response(200, '删除成功', base_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(404, '不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def delete(self, wage_id):
        """删除计酬配置。"""
        current_user = get_current_user()
        has_permission, error = check_wage_write_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        wage = EmployeeWageService.get_wage_by_id(wage_id)
        if not wage:
            return ApiResponse.error('计酬配置不存在')

        EmployeeWageService.delete_wage(wage)
        return ApiResponse.success(message='删除成功')


@employee_wage_ns.route('/calculate')
class WageCalculate(Resource):
    @login_required
    @permission_required('system:employee_wage:view')
    @employee_wage_ns.expect(wage_calculate_model)
    @employee_wage_ns.response(200, '成功', wage_calculate_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """试算工资金额。"""
        current_user = get_current_user()
        has_permission, error = check_wage_view_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        data = request.get_json() or {}
        user_id = data.get('user_id')
        process_id = data.get('process_id')
        quantity = data.get('quantity', 0)
        work_hours = data.get('work_hours', 0)
        work_days = data.get('work_days', 1)
        total_work_days = data.get('total_work_days', 22)
        work_date = data.get('work_date')

        wage_amount = EmployeeWageService.calculate_wage(
            user_id=user_id,
            process_id=process_id,
            quantity=quantity,
            work_hours=work_hours,
            work_days=work_days,
            total_work_days=total_work_days,
            work_date=work_date
        )

        return ApiResponse.success({
            'user_id': user_id,
            'process_id': process_id,
            'wage_amount': wage_amount
        })
