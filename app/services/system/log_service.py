"""日志管理服务。"""

from sqlalchemy import func

from app.extensions import db
from app.models.system.log import LoginLog, OperationLog
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService


class LogService(BaseService):
    """日志管理服务。"""

    @staticmethod
    def get_user_factory_ids(user_id):
        """获取用户有效关联的工厂 ID 列表。"""
        user_factories = UserFactory.query.filter_by(user_id=user_id, status=1, is_deleted=0).all()
        return [user_factory.factory_id for user_factory in user_factories]

    @staticmethod
    def get_operation_log_list(current_user, filters):
        """按当前用户数据范围分页查询操作日志。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        operation = filters.get('operation', '')
        status = filters.get('status')
        start_time = filters.get('start_time', '')
        end_time = filters.get('end_time', '')

        query = OperationLog.query
        if current_user.is_internal_user:
            factory_id = filters.get('factory_id')
            if factory_id:
                query = query.filter_by(factory_id=factory_id)
        else:
            factory_ids = LogService.get_user_factory_ids(current_user.id)
            if factory_ids:
                query = query.filter(OperationLog.factory_id.in_(factory_ids))
            else:
                query = query.filter(OperationLog.user_id == current_user.id)

        if username:
            query = query.filter(OperationLog.username.like(f'%{username}%'))
        if operation:
            query = query.filter(OperationLog.operation.like(f'%{operation}%'))
        if status is not None:
            query = query.filter_by(status=status)
        if start_time:
            query = query.filter(OperationLog.create_time >= start_time)
        if end_time:
            query = query.filter(OperationLog.create_time <= end_time)

        pagination = query.order_by(OperationLog.id.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def get_operation_log_by_id(log_id):
        """根据 ID 获取操作日志。"""
        return OperationLog.query.get(log_id)

    @staticmethod
    def check_operation_log_permission(current_user, log):
        """校验当前用户是否可查看指定操作日志。"""
        if current_user.is_internal_user:
            return True, None

        factory_ids = LogService.get_user_factory_ids(current_user.id)
        if log.factory_id in factory_ids or log.user_id == current_user.id:
            return True, None
        return False, '无权限查看'

    @staticmethod
    def get_login_log_list(current_user, filters):
        """按当前用户数据范围分页查询登录日志。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        login_type = filters.get('login_type', '')
        status = filters.get('status')
        start_time = filters.get('start_time', '')
        end_time = filters.get('end_time', '')

        query = LoginLog.query
        if current_user.is_internal_user:
            factory_id = filters.get('factory_id')
            if factory_id:
                user_ids = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id,
                    status=1,
                    is_deleted=0
                ).all()
                user_ids = [user_id for user_id, in user_ids]
                if user_ids:
                    query = query.filter(LoginLog.user_id.in_(user_ids))
        else:
            query = query.filter_by(user_id=current_user.id)

        if username:
            query = query.filter(LoginLog.username.like(f'%{username}%'))
        if login_type:
            query = query.filter_by(login_type=login_type)
        if status is not None:
            query = query.filter_by(status=status)
        if start_time:
            query = query.filter(LoginLog.create_time >= start_time)
        if end_time:
            query = query.filter(LoginLog.create_time <= end_time)

        pagination = query.order_by(LoginLog.id.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def get_login_log_by_id(log_id):
        """根据 ID 获取登录日志。"""
        return LoginLog.query.get(log_id)

    @staticmethod
    def check_login_log_permission(current_user, log):
        """校验当前用户是否可查看指定登录日志。"""
        if current_user.is_internal_user:
            return True, None
        if log.user_id == current_user.id:
            return True, None
        return False, '无权限查看'

    @staticmethod
    def get_log_stats(current_user):
        """汇总当前用户可见范围内的日志统计数据。"""
        query_op = OperationLog.query
        query_login = LoginLog.query

        if not current_user.is_internal_user:
            factory_ids = LogService.get_user_factory_ids(current_user.id)
            if factory_ids:
                query_op = query_op.filter(OperationLog.factory_id.in_(factory_ids))
                query_login = query_login.filter(LoginLog.user_id == current_user.id)
            else:
                query_op = query_op.filter_by(user_id=current_user.id)
                query_login = query_login.filter_by(user_id=current_user.id)

        today = func.date(OperationLog.create_time) == func.current_date()
        today_op_count = query_op.filter(today).count()
        today_login_count = query_login.filter(today).count()
        today_success_login = query_login.filter(today, LoginLog.status == 1).count()
        today_fail_login = query_login.filter(today, LoginLog.status == 0).count()

        return {
            'today_operation_count': today_op_count,
            'today_login_count': today_login_count,
            'today_success_login': today_success_login,
            'today_fail_login': today_fail_login
        }
