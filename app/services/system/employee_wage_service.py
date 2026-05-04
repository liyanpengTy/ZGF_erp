"""员工计酬服务"""
from datetime import datetime
from app.models.system.employee_wage import EmployeeWage
from app.models.auth.user import User
from app.models.business.process import Process
from app.services.base.base_service import BaseService


class EmployeeWageService(BaseService):
    """员工计酬服务"""

    @staticmethod
    def get_wage_by_id(wage_id):
        """根据ID获取计酬配置"""
        return EmployeeWage.query.filter_by(id=wage_id, is_deleted=0).first()

    @staticmethod
    def get_wage_list(filters):
        """获取计酬配置列表"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        user_id = filters.get('user_id')
        process_id = filters.get('process_id')
        wage_type = filters.get('wage_type')

        query = EmployeeWage.query.filter_by(is_deleted=0)

        if user_id:
            query = query.filter_by(user_id=user_id)
        if process_id:
            query = query.filter_by(process_id=process_id)
        if wage_type:
            query = query.filter_by(wage_type=wage_type)

        pagination = query.order_by(EmployeeWage.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def create_wage(data):
        """创建计酬配置"""
        # 验证用户是否存在
        user = User.query.filter_by(id=data['user_id'], is_deleted=0).first()
        if not user:
            return None, '用户不存在'

        # 验证工序是否存在
        process = Process.query.filter_by(id=data['process_id'], is_deleted=0).first()
        if not process:
            return None, '工序不存在'

        # 检查同一用户同一工序同一生效日期是否已有配置
        existing = EmployeeWage.query.filter_by(
            user_id=data['user_id'],
            process_id=data['process_id'],
            effective_date=datetime.strptime(data['effective_date'], '%Y-%m-%d').date(),
            is_deleted=0
        ).first()

        if existing:
            return None, '该用户此工序在该日期已有计酬配置'

        wage = EmployeeWage(
            user_id=data['user_id'],
            process_id=data['process_id'],
            wage_type=data['wage_type'],
            monthly_salary=data.get('monthly_salary', 0),
            piece_rate=data.get('piece_rate', 0),
            base_salary=data.get('base_salary', 0),
            base_piece_rate=data.get('base_piece_rate', 0),
            hourly_rate=data.get('hourly_rate', 0),
            effective_date=datetime.strptime(data['effective_date'], '%Y-%m-%d').date(),
            remark=data.get('remark', '')
        )
        wage.save()

        return wage, None

    @staticmethod
    def update_wage(wage, data):
        """更新计酬配置"""
        if 'wage_type' in data:
            wage.wage_type = data['wage_type']
        if 'monthly_salary' in data:
            wage.monthly_salary = data['monthly_salary']
        if 'piece_rate' in data:
            wage.piece_rate = data['piece_rate']
        if 'base_salary' in data:
            wage.base_salary = data['base_salary']
        if 'base_piece_rate' in data:
            wage.base_piece_rate = data['base_piece_rate']
        if 'hourly_rate' in data:
            wage.hourly_rate = data['hourly_rate']
        if 'effective_date' in data:
            wage.effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d').date()
        if 'remark' in data:
            wage.remark = data['remark']

        wage.save()
        return wage, None

    @staticmethod
    def delete_wage(wage):
        """删除计酬配置（软删除）"""
        wage.is_deleted = 1
        wage.save()
        return True

    @staticmethod
    def get_current_wage(user_id, process_id, work_date=None):
        """
        获取员工在指定日期的计酬配置
        work_date: 工作日期，用于取当天生效的配置
        """
        if not work_date:
            work_date = datetime.now().date()

        wage = EmployeeWage.query.filter(
            EmployeeWage.user_id == user_id,
            EmployeeWage.process_id == process_id,
            EmployeeWage.effective_date <= work_date,
            EmployeeWage.is_deleted == 0
        ).order_by(EmployeeWage.effective_date.desc()).first()

        return wage

    @staticmethod
    def calculate_wage(user_id, process_id, quantity, work_hours, work_days, total_work_days, work_date=None):
        """
        计算工资
        quantity: 完成数量（件）
        work_hours: 工作小时数
        work_days: 实际工作天数
        total_work_days: 当月总工作天数
        """
        wage_config = EmployeeWageService.get_current_wage(user_id, process_id, work_date)

        if not wage_config:
            return 0

        wage_type = wage_config.wage_type

        if wage_type == 'monthly':
            # 月薪制：按比例计算
            return float(wage_config.monthly_salary) * (work_days / total_work_days) if total_work_days > 0 else 0

        elif wage_type == 'piece':
            # 纯计件
            return float(wage_config.piece_rate) * quantity

        elif wage_type == 'base_piece':
            # 底薪 + 计件
            base = float(wage_config.base_salary) * (work_days / total_work_days) if total_work_days > 0 else 0
            piece = float(wage_config.base_piece_rate) * quantity
            return base + piece

        elif wage_type == 'hourly':
            # 计时制
            return float(wage_config.hourly_rate) * work_hours

        return 0
