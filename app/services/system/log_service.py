"""日志管理服务"""
from sqlalchemy import func
from app.extensions import db
from app.models.system.log import OperationLog, LoginLog
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService


class LogService(BaseService):
    """日志管理服务"""

    @staticmethod
    def get_user_factory_ids(user_id):
        """获取用户关联的工厂ID列表"""
        user_factories = UserFactory.query.filter_by(
            user_id=user_id, status=1, is_deleted=0
        ).all()
        return [uf.factory_id for uf in user_factories]

    @staticmethod
    def get_operation_log_list(current_user, filters):
        """
        获取操作日志列表
        filters: page, page_size, username, operation, status, start_time, end_time, factory_id
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        operation = filters.get('operation', '')
        status = filters.get('status')
        start_time = filters.get('start_time', '')
        end_time = filters.get('end_time', '')

        query = OperationLog.query

        # 权限过滤
        if current_user.is_admin == 1:
            # 公司内部人员：可以指定工厂ID查看
            factory_id = filters.get('factory_id')
            if factory_id:
                query = query.filter_by(factory_id=factory_id)
        else:
            # 普通用户：只能查看自己关联工厂的日志
            factory_ids = LogService.get_user_factory_ids(current_user.id)
            if factory_ids:
                query = query.filter(OperationLog.factory_id.in_(factory_ids))
            else:
                query = query.filter(OperationLog.user_id == current_user.id)

        # 条件过滤
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
    def get_operation_log_by_id(log_id):
        """根据ID获取操作日志"""
        return OperationLog.query.get(log_id)

    @staticmethod
    def check_operation_log_permission(current_user, log):
        """检查操作日志查看权限"""
        if current_user.is_admin == 1:
            return True, None

        factory_ids = LogService.get_user_factory_ids(current_user.id)
        if log.factory_id in factory_ids or log.user_id == current_user.id:
            return True, None

        return False, '无权限查看'

    @staticmethod
    def get_login_log_list(current_user, filters):
        """
        获取登录日志列表
        filters: page, page_size, username, login_type, status, start_time, end_time, factory_id
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        login_type = filters.get('login_type', '')
        status = filters.get('status')
        start_time = filters.get('start_time', '')
        end_time = filters.get('end_time', '')

        query = LoginLog.query

        # 权限过滤
        if current_user.is_admin == 1:
            factory_id = filters.get('factory_id')
            if factory_id:
                # 获取该工厂下的用户ID列表
                user_ids = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id, status=1, is_deleted=0
                ).all()
                user_ids = [u[0] for u in user_ids]
                if user_ids:
                    query = query.filter(LoginLog.user_id.in_(user_ids))
        else:
            query = query.filter_by(user_id=current_user.id)

        # 条件过滤
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
    def get_login_log_by_id(log_id):
        """根据ID获取登录日志"""
        return LoginLog.query.get(log_id)

    @staticmethod
    def check_login_log_permission(current_user, log):
        """检查登录日志查看权限"""
        if current_user.is_admin == 1:
            return True, None

        if log.user_id == current_user.id:
            return True, None

        return False, '无权限查看'

    @staticmethod
    def get_log_stats(current_user):
        """获取日志统计"""
        query_op = OperationLog.query
        query_login = LoginLog.query

        if current_user.is_admin == 1:
            pass
        else:
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
