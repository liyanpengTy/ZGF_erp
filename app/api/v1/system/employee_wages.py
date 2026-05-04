"""员工计酬管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.system.employee_wage import (
    EmployeeWageSchema, EmployeeWageCreateSchema, EmployeeWageUpdateSchema
)
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required, permission_required
from app.services import AuthService, EmployeeWageService

employee_wage_ns = Namespace('employee-wages', description='员工计酬管理')

shared = get_shared_models(employee_wage_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

# ========== 请求解析器 ==========
wage_query_parser = employee_wage_ns.parser()
wage_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
wage_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
wage_query_parser.add_argument('user_id', type=int, location='args', help='员工ID')
wage_query_parser.add_argument('process_id', type=int, location='args', help='工序ID')
wage_query_parser.add_argument('wage_type', type=str, location='args', help='计酬方式',
                               choices=['monthly', 'piece', 'base_piece', 'hourly'])

# ========== 响应模型 ==========
employee_wage_item_model = employee_wage_ns.model('EmployeeWageItem', {
    'id': fields.Integer(),
    'user_id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'process_id': fields.Integer(),
    'process_name': fields.String(),
    'wage_type': fields.String(),
    'wage_type_label': fields.String(),
    'monthly_salary': fields.Float(),
    'piece_rate': fields.Float(),
    'base_salary': fields.Float(),
    'base_piece_rate': fields.Float(),
    'hourly_rate': fields.Float(),
    'effective_date': fields.String(),
    'remark': fields.String(),
    'create_time': fields.String()
})

wage_list_data = employee_wage_ns.model('WageListData', {
    'items': fields.List(fields.Nested(employee_wage_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

wage_list_response = employee_wage_ns.clone('WageListResponse', base_response, {
    'data': fields.Nested(wage_list_data)
})

wage_item_response = employee_wage_ns.clone('WageItemResponse', base_response, {
    'data': fields.Nested(employee_wage_item_model)
})

# ========== Schema 初始化 ==========
wage_schema = EmployeeWageSchema()
wages_schema = EmployeeWageSchema(many=True)
wage_create_schema = EmployeeWageCreateSchema()
wage_update_schema = EmployeeWageUpdateSchema()


def get_current_user():
    return AuthService.get_current_user()


@employee_wage_ns.route('')
class EmployeeWageList(Resource):
    @login_required
    @permission_required('system:employee_wage:view')
    @employee_wage_ns.expect(wage_query_parser)
    @employee_wage_ns.response(200, '成功', wage_list_response)
    @employee_wage_ns.response(401, '未登录', unauthorized_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """获取员工计酬列表"""
        args = wage_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以查看
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

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
    @employee_wage_ns.expect(employee_wage_ns.model('EmployeeWageCreate', {
        'user_id': fields.Integer(required=True, description='员工ID'),
        'process_id': fields.Integer(required=True, description='工序ID'),
        'wage_type': fields.String(required=True, description='计酬方式',
                                   choices=['monthly', 'piece', 'base_piece', 'hourly']),
        'monthly_salary': fields.Float(description='月薪金额'),
        'piece_rate': fields.Float(description='计件单价'),
        'base_salary': fields.Float(description='底薪'),
        'base_piece_rate': fields.Float(description='计件单价'),
        'hourly_rate': fields.Float(description='计时单价'),
        'effective_date': fields.String(required=True, description='生效日期', example='2024-01-01'),
        'remark': fields.String(description='备注')
    }))
    @employee_wage_ns.response(201, '创建成功', wage_item_response)
    @employee_wage_ns.response(400, '参数错误', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    @employee_wage_ns.response(409, '配置已存在', error_response)
    def post(self):
        """创建员工计酬配置"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建计酬配置', 403)

        try:
            data = wage_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        wage, error = EmployeeWageService.create_wage(data)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(wage_schema.dump(wage), '创建成功', 201)


@employee_wage_ns.route('/<int:wage_id>')
class EmployeeWageDetail(Resource):
    @login_required
    @permission_required('system:employee_wage:view')
    @employee_wage_ns.response(200, '成功', wage_item_response)
    @employee_wage_ns.response(404, '不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def get(self, wage_id):
        """获取计酬配置详情"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        wage = EmployeeWageService.get_wage_by_id(wage_id)
        if not wage:
            return ApiResponse.error('计酬配置不存在')

        return ApiResponse.success(wage_schema.dump(wage))

    @login_required
    @permission_required('system:employee_wage:edit')
    @employee_wage_ns.expect(employee_wage_ns.model('EmployeeWageUpdate', {
        'wage_type': fields.String(description='计酬方式', choices=['monthly', 'piece', 'base_piece', 'hourly']),
        'monthly_salary': fields.Float(description='月薪金额'),
        'piece_rate': fields.Float(description='计件单价'),
        'base_salary': fields.Float(description='底薪'),
        'base_piece_rate': fields.Float(description='计件单价'),
        'hourly_rate': fields.Float(description='计时单价'),
        'effective_date': fields.String(description='生效日期', example='2024-01-01'),
        'remark': fields.String(description='备注')
    }))
    @employee_wage_ns.response(200, '更新成功', wage_item_response)
    @employee_wage_ns.response(404, '不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def patch(self, wage_id):
        """更新计酬配置"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以更新计酬配置', 403)

        wage = EmployeeWageService.get_wage_by_id(wage_id)
        if not wage:
            return ApiResponse.error('计酬配置不存在')

        try:
            data = wage_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        wage, error = EmployeeWageService.update_wage(wage, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(wage_schema.dump(wage), '更新成功')

    @login_required
    @permission_required('system:employee_wage:delete')
    @employee_wage_ns.response(200, '删除成功', base_response)
    @employee_wage_ns.response(404, '不存在', error_response)
    @employee_wage_ns.response(403, '无权限', forbidden_response)
    def delete(self, wage_id):
        """删除计酬配置"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除计酬配置', 403)

        wage = EmployeeWageService.get_wage_by_id(wage_id)
        if not wage:
            return ApiResponse.error('计酬配置不存在')

        EmployeeWageService.delete_wage(wage)

        return ApiResponse.success(message='删除成功')


@employee_wage_ns.route('/calculate')
class WageCalculate(Resource):
    @login_required
    @permission_required('system:employee_wage:view')
    @employee_wage_ns.expect(employee_wage_ns.model('WageCalculate', {
        'user_id': fields.Integer(required=True, description='员工ID'),
        'process_id': fields.Integer(required=True, description='工序ID'),
        'quantity': fields.Integer(description='完成数量', default=0),
        'work_hours': fields.Float(description='工作小时数', default=0),
        'work_days': fields.Float(description='工作天数', default=1),
        'total_work_days': fields.Float(description='当月总工作天数', default=22),
        'work_date': fields.String(description='工作日期', example='2024-01-15')
    }))
    @employee_wage_ns.response(200, '成功', base_response)
    def post(self):
        """计算工资（测试用）"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        data = request.get_json()
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
