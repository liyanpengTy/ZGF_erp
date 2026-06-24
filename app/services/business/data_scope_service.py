"""业务模块数据范围公共服务。"""

from sqlalchemy import false, or_

from app.constants.identity import (
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
)
from app.services.system.user_service import UserService


class BusinessDataScopeService:
    """统一处理业务模块的数据范围过滤规则。"""

    @staticmethod
    def build_or_filter(*conditions):
        """把多个可选条件合并为一个 OR 过滤表达式。"""
        valid_conditions = [condition for condition in conditions if condition is not None]
        if not valid_conditions:
            return None
        if len(valid_conditions) == 1:
            return valid_conditions[0]
        return or_(*valid_conditions)

    @staticmethod
    def apply_scope(
        query,
        current_user,
        current_factory_id=None,
        assigned_filter=None,
        own_related_filter=None,
        self_only_filter=None,
    ):
        """按当前用户在当前上下文中的数据范围收口业务查询。"""
        data_scope = UserService.get_current_data_scope(
            current_user,
            current_factory_id=current_factory_id,
        )
        if current_user.is_platform_admin or data_scope == ROLE_DATA_SCOPE_ALL:
            return query

        if data_scope == ROLE_DATA_SCOPE_ASSIGNED:
            scope_filter = assigned_filter or own_related_filter or self_only_filter
        elif data_scope == ROLE_DATA_SCOPE_OWN_RELATED:
            scope_filter = own_related_filter or assigned_filter or self_only_filter
        else:
            scope_filter = self_only_filter or own_related_filter or assigned_filter

        if scope_filter is None:
            return query.filter(false())
        return query.filter(scope_filter)

    @staticmethod
    def apply_subject_scope(query, current_user, model, current_subject_id=None, user_id_field=None):
        """按需求中的主体用户隔离规则过滤查询。"""
        if current_user and current_user.is_internal_user:
            return query

        if current_subject_id:
            return query.filter(model.subject_id == current_subject_id)

        if user_id_field is not None and current_user:
            return query.filter(user_id_field == current_user.id, model.subject_id.is_(None))

        return query.filter(false())

    @staticmethod
    def apply_customer_scope(query, customer, model):
        """按客户用户只能查看自己订单的规则过滤查询。"""
        if not customer:
            return query.filter(false())
        return query.filter(model.customer_user_id == customer.id)

    @staticmethod
    def check_related_users_scope(current_user, current_factory_id=None, *related_user_ids):
        """校验带有“创建人/客户/操作人”等关联用户的数据是否落在当前数据范围内。"""
        if not current_user:
            return False

        data_scope = UserService.get_current_data_scope(
            current_user,
            current_factory_id=current_factory_id,
        )
        if current_user.is_platform_admin or data_scope == ROLE_DATA_SCOPE_ALL:
            return True

        valid_related_user_ids = {
            user_id
            for user_id in related_user_ids
            if user_id not in (None, 0)
        }
        return current_user.id in valid_related_user_ids

    @staticmethod
    def check_creator_customer_scope(current_user, current_factory_id=None, creator_user_id=None, customer_user_id=None):
        """校验带创建人和客户归属的业务数据是否在当前用户可操作范围内。"""
        return BusinessDataScopeService.check_related_users_scope(
            current_user,
            current_factory_id,
            creator_user_id,
            customer_user_id,
        )
