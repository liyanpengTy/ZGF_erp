"""员工计薪管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import require_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.system.employee_wage import EmployeeWageCreateSchema, EmployeeWageSchema, EmployeeWageUpdateSchema, WageCalculateSchema
from app.services import EmployeeWageService
from app.utils.permissions import login_required, permission_required
from app.utils.response import ApiResponse

employee_wage_ns = Namespace('鍛樺伐璁¤柂绠＄悊-employee-wages', description='鍛樺伐璁¤柂绠＄悊')

common = get_common_models(employee_wage_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

wage_query_parser = page_parser.copy()
wage_query_parser.add_argument('factory_id', type=int, location='args', help='工厂 ID')
wage_query_parser.add_argument('user_id', type=int, location='args', help='员工 ID')
wage_query_parser.add_argument('process_id', type=int, location='args', help='工序 ID')
wage_query_parser.add_argument(
    'wage_type',
    type=str,
    location='args',
    help='计薪方式',
    choices=['monthly', 'piece', 'base_piece', 'hourly'],
)

employee_wage_item_model = employee_wage_ns.model('EmployeeWageItem', {
    'id': fields.Integer(description='工资记录 ID', example=1),
    'factory_id': fields.Integer(description='工厂 ID', example=1),
    'factory_name': fields.String(description='工厂名称', example='示例工厂'),
    'user_id': fields.Integer(description='员工 ID', example=2),
    'username': fields.String(description='用户名', example='factory_employee'),
    'nickname': fields.String(description='昵称', example='工厂员工'),
    'process_id': fields.Integer(description='工序 ID', example=3),
    'process_name': fields.String(description='工序名称', example='锁边'),
    'wage_type': fields.String(description='计薪方式', example='piece'),
    'wage_type_label': fields.String(description='计薪方式名称', example='计件制'),
    'monthly_salary': fields.Float(description='月薪金额', example=None),
    'piece_rate': fields.Float(description='计件单价', example=1.2),
    'base_salary': fields.Float(description='保底工资', example=None),
    'base_piece_rate': fields.Float(description='保底计件单价', example=None),
    'hourly_rate': fields.Float(description='计时单价', example=None),
    'effective_date': fields.String(description='生效日期', example='2026-05-01'),
    'remark': fields.String(description='备注', example='夏季工价'),
    'create_time': fields.String(description='创建时间', example='2026-05-01 10:00:00'),
})

wage_list_data = build_page_data_model(employee_wage_ns, 'WageListData', employee_wage_item_model, items_description='计薪列表')
wage_list_response = build_page_response_model(employee_wage_ns, 'WageListResponse', base_response, wage_list_data, '计薪分页数据')
wage_item_response = employee_wage_ns.clone('WageItemResponse', base_response, {
    'data': fields.Nested(employee_wage_item_model, description='工资详情数据'),
})

wage_calculate_result_model = employee_wage_ns.model('WageCalculateResult', {
    'factory_id': fields.Integer(description='工厂 ID', example=1),
    'user_id': fields.Integer(description='员工 ID', example=2),
    'process_id': fields.Integer(description='工序 ID', example=3),
    'wage_amount': fields.Float(description='试算工资金额', example=128.5),
})

wage_calculate_response = employee_wage_ns.clone('WageCalculateResponse', base_response, {
    'data': fields.Nested(wage_calculate_result_model, description='试算结果数据'),
})

employee_wage_create_model = employee_wage_ns.model('EmployeeWageCreate', {
    'factory_id': fields.Integer(required=True, description='工厂 ID', example=1),
    'user_id': fields.Integer(required=True, description='员工 ID', example=2),
    'process_id': fields.Integer(required=True, description='工序 ID', example=3),
    'wage_type': fields.String(
        required=True,
        description='计薪方式',
        choices=['monthly', 'piece', 'base_piece', 'hourly'],
        example='piece',
    ),
    'monthly_salary': fields.Float(description='月薪金额', example=6000),
    'piece_rate': fields.Float(description='计件单价', example=1.2),
    'base_salary': fields.Float(description='保底工资', example=3000),
    'base_piece_rate': fields.Float(description='保底计件单价', example=0.8),
    'hourly_rate': fields.Float(description='计时单价', example=25),
    'effective_date': fields.String(required=True, description='生效日期', example='2026-05-01'),
    'remark': fields.String(description='备注', example='夏季工价'),
})

employee_wage_update_model = employee_wage_ns.model('EmployeeWageUpdate', {
    'factory_id': fields.Integer(description='工厂 ID', example=1),
    'wage_type': fields.String(
        description='计薪方式',
        choices=['monthly', 'piece', 'base_piece', 'hourly'],
        example='hourly',
    ),
    'monthly_salary': fields.Float(description='月薪金额', example=6500),
    'piece_rate': fields.Float(description='计件单价', example=1.5),
    'base_salary': fields.Float(description='保底工资', example=3200),
    'base_piece_rate': fields.Float(description='保底计件单价', example=1.0),
    'hourly_rate': fields.Float(description='计时单价', example=28),
    'effective_date': fields.String(description='生效日期', example='2026-06-01'),
    'remark': fields.String(description='备注', example='更新工价'),
})

wage_calculate_model = employee_wage_ns.model('WageCalculate', {
    'factory_id': fields.Integer(required=True, description='工厂 ID', example=1),
    'user_id': fields.Integer(required=True, description='员工 ID', example=2),
    'process_id': fields.Integer(required=True, description='工序 ID', example=3),
    'quantity': fields.Integer(description='完成数量', default=0, example=100),
    'work_hours': fields.Float(description='工作小时数', default=0, example=8),
    'work_days': fields.Float(description='工作天数', default=1, example=1),
    'total_work_days': fields.Float(description='当月总工作天数', default=22, example=22),
    'work_date': fields.String(description='工作日期', example='2026-05-15'),
})

wage_schema = EmployeeWageSchema()
wages_schema = EmployeeWageSchema(many=True)
wage_create_schema = EmployeeWageCreateSchema()
wage_update_schema = EmployeeWageUpdateSchema()
wage_calculate_schema = WageCalculateSchema()


def build_wage_calculate_payload(factory_id, user_id, process_id, wage_amount):
    """构造工资试算接口的返回数据。"""
    return {
        'factory_id': factory_id,
        'user_id': user_id,
        'process_id': process_id,
        'wage_amount': wage_amount,
    }


def check_wage_view_permission(current_user):
    """校验计薪查看权限，仅平台内部用户允许访问。"""
    if not current_user:
        return False, '用户不存在'
    if not current_user.is_internal_user:
        return False, '无权限查看'
    return True, None


def check_wage_write_permission(current_user):
    """校验计薪维护权限，仅平台管理员允许维护配置。"""
    if not current_user:
        return False, '用户不存在'
    if not current_user.is_platform_admin:
        return False, '只有平台管理员可以维护计薪配置'
    return True, None


def get_employee_wage_user_or_error():
    """获取员工计薪接口当前用户，不存在时返回统一错误响应。"""
    return require_current_user()


def get_wage_or_error(wage_id):
    """根据计薪配置 ID 查询记录，不存在时返回统一错误响应。"""
    wage = EmployeeWageService.get_wage_by_id(wage_id)
    if not wage:
        return None, ApiResponse.error('计薪配置不存在', 404)
    return wage, None


@employee_wage_ns.route('')
class EmployeeWageList(Resource):
    @login_required
    @permission_required('factory-management.employee-wages.browse')
    @employee_wage_ns.expect(wage_query_parser)
    @employee_wage_ns.response(200, '成功', wage_list_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询员工计薪分页列表接口，支持按工厂、员工、工序和计薪方式筛选。"""
        args = wage_query_parser.parse_args()
        current_user, error_response_data = get_employee_wage_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = check_wage_view_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = EmployeeWageService.get_wage_list(args)
        return ApiResponse.success_page_result(result, wages_schema.dump(result['items']))

    @login_required
    @permission_required('factory-management.employee-wages.create')
    @employee_wage_ns.expect(employee_wage_create_model)
    @employee_wage_ns.response(201, '创建成功', wage_item_response)
    @employee_wage_ns.response(400, '参数错误', error_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    @employee_wage_ns.response(409, '配置已存在', error_response)
    def post(self):
        """创建员工计薪配置接口，用于维护员工在指定工厂和工序下的工资规则。"""
        current_user, error_response_data = get_employee_wage_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = check_wage_write_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = wage_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        wage, service_error = EmployeeWageService.create_wage(data)
        if service_error:
            status_code = 409 if '已存在' in service_error else 400
            return ApiResponse.error(service_error, status_code)

        return ApiResponse.success(wage_schema.dump(wage), '创建成功', 201)


@employee_wage_ns.route('/<int:wage_id>')
class EmployeeWageDetail(Resource):
    @login_required
    @permission_required('factory-management.employee-wages.browse')
    @employee_wage_ns.response(200, '成功', wage_item_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(404, '记录不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def get(self, wage_id):
        """查询计薪配置详情接口，返回单条工资规则完整信息。"""
        current_user, error_response_data = get_employee_wage_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = check_wage_view_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        wage, error_response_data = get_wage_or_error(wage_id)
        if error_response_data:
            return error_response_data

        return ApiResponse.success(wage_schema.dump(wage))

    @login_required
    @permission_required('factory-management.employee-wages.update')
    @employee_wage_ns.expect(employee_wage_update_model)
    @employee_wage_ns.response(200, '更新成功', wage_item_response)
    @employee_wage_ns.response(400, '参数错误', error_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(404, '记录不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def patch(self, wage_id):
        """更新计薪配置接口，可调整工厂、生效日期、计薪方式和金额字段。"""
        current_user, error_response_data = get_employee_wage_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = check_wage_write_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        wage, error_response_data = get_wage_or_error(wage_id)
        if error_response_data:
            return error_response_data

        try:
            data = wage_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        wage, service_error = EmployeeWageService.update_wage(wage, data)
        if service_error:
            return ApiResponse.error(service_error, 400)

        return ApiResponse.success(wage_schema.dump(wage), '更新成功')

    @login_required
    @permission_required('factory-management.employee-wages.delete')
    @employee_wage_ns.response(200, '删除成功', base_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(404, '记录不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def delete(self, wage_id):
        """删除计薪配置接口，用于移除失效或误建的工资规则。"""
        current_user, error_response_data = get_employee_wage_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = check_wage_write_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        wage, error_response_data = get_wage_or_error(wage_id)
        if error_response_data:
            return error_response_data

        EmployeeWageService.delete_wage(wage)
        return ApiResponse.success(message='删除成功')


@employee_wage_ns.route('/calculate')
class WageCalculate(Resource):
    @login_required
    @permission_required('factory-management.employee-wages.browse')
    @employee_wage_ns.expect(wage_calculate_model)
    @employee_wage_ns.response(200, '成功', wage_calculate_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """试算工资金额接口，按工厂、产量、工时和日期计算预估工资。"""
        current_user, error_response_data = get_employee_wage_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = check_wage_view_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = wage_calculate_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        wage_amount = EmployeeWageService.calculate_wage(
            factory_id=data['factory_id'],
            user_id=data['user_id'],
            process_id=data['process_id'],
            quantity=data.get('quantity', 0),
            work_hours=data.get('work_hours', 0),
            work_days=data.get('work_days', 1),
            total_work_days=data.get('total_work_days', 22),
            work_date=data.get('work_date'),
        )

        return ApiResponse.success(
            build_wage_calculate_payload(data['factory_id'], data['user_id'], data['process_id'], wage_amount)
        )
