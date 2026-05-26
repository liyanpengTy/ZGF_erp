"""员工计薪服务。"""

from datetime import datetime

from app.models.auth.user import User
from app.models.business.process import Process
from app.models.system.employee_wage import EmployeeWage
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService


class EmployeeWageService(BaseService):
    """封装员工计薪配置的查询、维护与试算逻辑。"""

    @staticmethod
    def get_wage_by_id(wage_id):
        """根据 ID 获取计薪配置。"""
        return EmployeeWage.query.filter_by(id=wage_id, is_deleted=0).first()

    @staticmethod
    def get_wage_list(filters):
        """分页查询计薪配置列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        factory_id = filters.get('factory_id')
        user_id = filters.get('user_id')
        process_id = filters.get('process_id')
        wage_type = filters.get('wage_type')

        query = EmployeeWage.query.filter_by(is_deleted=0)
        if factory_id:
            query = query.filter_by(factory_id=factory_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if process_id:
            query = query.filter_by(process_id=process_id)
        if wage_type:
            query = query.filter_by(wage_type=wage_type)

        pagination = query.order_by(EmployeeWage.id.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False,
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def validate_factory(factory_id):
        """校验工厂是否存在。"""
        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return None, '工厂不存在'
        return factory, None

    @staticmethod
    def validate_user_factory_relation(user_id, factory_id):
        """校验用户是否已绑定到指定工厂。"""
        relation = UserFactory.query.filter_by(
            user_id=user_id,
            factory_id=factory_id,
            status=1,
            is_deleted=0,
        ).first()
        if not relation:
            return None, '该用户未绑定到指定工厂，不能维护该工厂计薪配置'
        return relation, None

    @staticmethod
    def create_wage(data):
        """创建员工计薪配置。"""
        _, error = EmployeeWageService.validate_factory(data['factory_id'])
        if error:
            return None, error

        user = User.query.filter_by(id=data['user_id'], is_deleted=0).first()
        if not user:
            return None, '用户不存在'

        _, error = EmployeeWageService.validate_user_factory_relation(data['user_id'], data['factory_id'])
        if error:
            return None, error

        process = Process.query.filter_by(id=data['process_id'], is_deleted=0).first()
        if not process:
            return None, '工序不存在'

        effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d').date()
        existing = EmployeeWage.query.filter_by(
            factory_id=data['factory_id'],
            user_id=data['user_id'],
            process_id=data['process_id'],
            effective_date=effective_date,
            is_deleted=0,
        ).first()
        if existing:
            return None, '该工厂下该用户该工序在该日期已存在计薪配置'

        wage = EmployeeWage(
            factory_id=data['factory_id'],
            user_id=data['user_id'],
            process_id=data['process_id'],
            wage_type=data['wage_type'],
            monthly_salary=data.get('monthly_salary', 0),
            piece_rate=data.get('piece_rate', 0),
            base_salary=data.get('base_salary', 0),
            base_piece_rate=data.get('base_piece_rate', 0),
            hourly_rate=data.get('hourly_rate', 0),
            effective_date=effective_date,
            remark=data.get('remark', ''),
        )
        wage.save()
        return wage, None

    @staticmethod
    def update_wage(wage, data):
        """更新员工计薪配置。"""
        target_factory_id = data.get('factory_id', wage.factory_id)
        target_effective_date = wage.effective_date

        if 'factory_id' in data:
            _, error = EmployeeWageService.validate_factory(data['factory_id'])
            if error:
                return None, error
            _, error = EmployeeWageService.validate_user_factory_relation(wage.user_id, data['factory_id'])
            if error:
                return None, error

        if 'effective_date' in data:
            target_effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d').date()

        duplicate = EmployeeWage.query.filter_by(
            factory_id=target_factory_id,
            user_id=wage.user_id,
            process_id=wage.process_id,
            effective_date=target_effective_date,
            is_deleted=0,
        ).filter(EmployeeWage.id != wage.id).first()
        if duplicate:
            return None, '该工厂下该用户该工序在该日期已存在计薪配置'

        if 'factory_id' in data:
            wage.factory_id = data['factory_id']
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
            wage.effective_date = target_effective_date
        if 'remark' in data:
            wage.remark = data['remark']

        wage.save()
        return wage, None

    @staticmethod
    def delete_wage(wage):
        """删除员工计薪配置，采用逻辑删除。"""
        wage.is_deleted = 1
        wage.save()
        return True

    @staticmethod
    def get_current_wage(factory_id, user_id, process_id, work_date=None):
        """获取员工在指定工厂和日期生效的计薪配置。"""
        if not work_date:
            work_date = datetime.now().date()
        elif isinstance(work_date, str):
            work_date = datetime.strptime(work_date, '%Y-%m-%d').date()

        return EmployeeWage.query.filter(
            EmployeeWage.factory_id == factory_id,
            EmployeeWage.user_id == user_id,
            EmployeeWage.process_id == process_id,
            EmployeeWage.effective_date <= work_date,
            EmployeeWage.is_deleted == 0,
        ).order_by(EmployeeWage.effective_date.desc()).first()

    @staticmethod
    def calculate_wage(factory_id, user_id, process_id, quantity, work_hours, work_days, total_work_days, work_date=None):
        """按工厂维度试算工资金额。"""
        wage_config = EmployeeWageService.get_current_wage(factory_id, user_id, process_id, work_date)
        if not wage_config:
            return 0

        wage_type = wage_config.wage_type
        if wage_type == 'monthly':
            return float(wage_config.monthly_salary) * (work_days / total_work_days) if total_work_days > 0 else 0
        if wage_type == 'piece':
            return float(wage_config.piece_rate) * quantity
        if wage_type == 'base_piece':
            base = float(wage_config.base_salary) * (work_days / total_work_days) if total_work_days > 0 else 0
            piece = float(wage_config.base_piece_rate) * quantity
            return base + piece
        if wage_type == 'hourly':
            return float(wage_config.hourly_rate) * work_hours
        return 0
