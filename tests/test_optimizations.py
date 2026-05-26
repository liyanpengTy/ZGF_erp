"""本轮基础优化的回归测试。"""

import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import MagicMock

from app.models.base import apply_audit_fields
from app.api.v1.system.roles import get_role_or_error
from app.api.v1.system.users import get_target_user_or_error
from app.api.common.resource_helpers import ensure_permission_or_error, get_resource_or_error
from app.constants.identity import (
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_DATA_SCOPE_SELF_ONLY,
)
from app.services.business.data_scope_service import BusinessDataScopeService
from app.services.business.style_elastic_service import StyleElasticService
from app.services.business.style_price_service import StylePriceService
from app.services.business.style_process_service import StyleProcessService
from app.services.business.style_service import StyleService
from app.services.system.employee_wage_service import EmployeeWageService
from app.services.system.factory_service import FactoryService
from app.services.system.role_service import FACTORY_ADMIN_PERMISSION_CACHE, RoleService
from app.services.system.user_service import PERMISSION_CACHE, UserService
from app.utils.cache import SimpleTTLCache
from app.utils.logger import sanitize_payload


class DummyAuditTarget:
    """用于验证审计字段填充的简易对象。"""

    def __init__(self):
        self.create_by = None
        self.update_by = None
        self.created_by = None


class OptimizationTests(unittest.TestCase):
    """覆盖缓存、日志脱敏与审计字段填充。"""

    def setUp(self):
        """在每个用例前清理本地权限缓存，避免测试之间互相污染。"""
        PERMISSION_CACHE.clear()
        FACTORY_ADMIN_PERMISSION_CACHE.clear()

    def test_ttl_cache_get_set_and_expire(self):
        cache = SimpleTTLCache(default_ttl=0.01)
        cache.set('demo', 'value')
        self.assertEqual(cache.get('demo'), 'value')
        time.sleep(0.02)
        self.assertIsNone(cache.get('demo'))

    def test_ttl_cache_clear(self):
        cache = SimpleTTLCache(default_ttl=10)
        cache.set('demo', 'value')
        cache.clear()
        self.assertIsNone(cache.get('demo'))

    def test_employee_wage_calculate_uses_factory_dimension(self):
        """工资试算应按工厂维度读取当前生效配置。"""
        wage_config = SimpleNamespace(wage_type='piece', piece_rate=1.5)

        with patch.object(EmployeeWageService, 'get_current_wage', return_value=wage_config) as mock_get_current_wage:
            wage_amount = EmployeeWageService.calculate_wage(
                factory_id=9,
                user_id=2,
                process_id=3,
                quantity=100,
                work_hours=0,
                work_days=1,
                total_work_days=22,
                work_date='2026-05-01',
            )

        self.assertEqual(wage_amount, 150.0)
        mock_get_current_wage.assert_called_once_with(9, 2, 3, '2026-05-01')

    def test_sanitize_payload_masks_sensitive_fields(self):
        payload = {
            'username': 'tester',
            'password': '123456',
            'nested': {
                'refresh_token': 'abc',
                'profile': {'nickname': 'nick'},
            },
            'items': [
                {'new_password': '654321'},
                {'remark': 'ok'},
            ],
        }
        sanitized = sanitize_payload(payload)
        self.assertEqual(sanitized['username'], 'tester')
        self.assertEqual(sanitized['password'], '***')
        self.assertEqual(sanitized['nested']['refresh_token'], '***')
        self.assertEqual(sanitized['nested']['profile']['nickname'], 'nick')
        self.assertEqual(sanitized['items'][0]['new_password'], '***')
        self.assertEqual(sanitized['items'][1]['remark'], 'ok')

    def test_apply_audit_fields_sets_create_and_update(self):
        target = DummyAuditTarget()
        with patch('app.models.base.get_request_user_id', return_value=9):
            apply_audit_fields(target, is_insert=True)
        self.assertEqual(target.create_by, 9)
        self.assertEqual(target.update_by, 9)
        self.assertEqual(target.created_by, 9)

    def test_role_service_clear_permission_cache_cascades_to_user_service(self):
        """角色权限缓存清理应同时联动清空用户权限缓存。"""
        with patch.object(FACTORY_ADMIN_PERMISSION_CACHE, 'clear') as factory_cache_clear, patch.object(
            UserService,
            'clear_permission_cache',
        ) as user_cache_clear:
            RoleService.clear_permission_cache()

        factory_cache_clear.assert_called_once()
        user_cache_clear.assert_called_once()

    def test_user_service_assign_roles_clears_permission_cache(self):
        """用户角色重分配完成后应立即清空权限缓存。"""
        target_user = SimpleNamespace(is_internal_user=True)
        current_user = SimpleNamespace(is_platform_admin=True)

        with patch.object(UserService, 'get_user_by_id', return_value=target_user), patch(
            'app.services.system.user_service.db',
        ) as mock_db, patch.object(RoleService, 'clear_permission_cache') as clear_cache:
            success, error = UserService.assign_roles(user_id=9, role_ids=[], factory_id=0, current_user=current_user)

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_db.session.execute.assert_called_once()
        mock_db.session.commit.assert_called_once()
        clear_cache.assert_called_once()

    def test_role_service_assign_role_menus_clears_permission_cache(self):
        """角色菜单更新完成后应立即清空权限缓存。"""
        role = SimpleNamespace(id=5, is_factory_role=False)

        with patch('app.services.system.role_service.db') as mock_db, patch.object(
            RoleService,
            'clear_permission_cache',
        ) as clear_cache:
            success, error = RoleService.assign_role_menus(role_id=5, menu_ids=[], role=role)

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_db.session.execute.assert_called_once()
        mock_db.session.commit.assert_called_once()
        clear_cache.assert_called_once()

    def test_factory_service_add_user_to_factory_clears_permission_cache(self):
        """新增工厂关系后应立即清空权限缓存。"""
        user = SimpleNamespace(id=2, platform_identity='external')
        relation = MagicMock()

        with patch('app.services.system.factory_service.User') as mock_user_model, patch(
            'app.services.system.factory_service.UserFactory',
        ) as mock_user_factory_model, patch.object(
            FactoryService,
            '_sync_user_identity',
        ) as sync_identity, patch.object(RoleService, 'clear_permission_cache') as clear_cache:
            mock_user_model.query.filter_by.return_value.first.return_value = user
            mock_user_factory_model.query.filter_by.return_value.first.return_value = None
            mock_user_factory_model.return_value = relation

            result, error = FactoryService.add_user_to_factory(1, 2, 'employee')

        self.assertIs(result, relation)
        self.assertIsNone(error)
        relation.save.assert_called_once()
        sync_identity.assert_called_once_with(user)
        clear_cache.assert_called_once()

    def test_factory_service_update_factory_owner_clears_permission_cache(self):
        """切换工厂管理员后应立即清空权限缓存。"""
        user = SimpleNamespace(id=3, nickname='旧昵称', save=MagicMock())
        factory = SimpleNamespace(id=1, name='新工厂')
        old_owner_relation = SimpleNamespace(user_id=2, is_deleted=0, save=MagicMock())
        new_owner_relation = MagicMock()

        with patch('app.services.system.factory_service.User') as mock_user_model, patch(
            'app.services.system.factory_service.UserFactory',
        ) as mock_user_factory_model, patch.object(
            FactoryService,
            'get_factory_by_id',
            return_value=factory,
        ), patch.object(FactoryService, '_sync_user_identity') as sync_identity, patch.object(
            RoleService,
            'clear_permission_cache',
        ) as clear_cache:
            mock_user_model.query.filter_by.return_value.first.return_value = user
            mock_user_factory_model.query.filter_by.return_value.first.side_effect = [old_owner_relation, None]
            mock_user_factory_model.return_value = new_owner_relation

            result, error = FactoryService.update_factory_owner(1, 3)

        self.assertIs(result, new_owner_relation)
        self.assertIsNone(error)
        self.assertEqual(old_owner_relation.is_deleted, 1)
        old_owner_relation.save.assert_called_once()
        new_owner_relation.save.assert_called_once()
        sync_identity.assert_called_once_with(user)
        clear_cache.assert_called_once()

    def test_factory_service_remove_user_from_factory_clears_permission_cache(self):
        """移除工厂关系后应立即清空权限缓存。"""
        relation = SimpleNamespace(
            relation_type='employee',
            is_deleted=0,
            leave_date=None,
            save=MagicMock(),
        )
        user = SimpleNamespace(id=8)

        with patch('app.services.system.factory_service.UserFactory') as mock_user_factory_model, patch(
            'app.services.system.factory_service.User',
        ) as mock_user_model, patch.object(FactoryService, '_sync_user_identity') as sync_identity, patch.object(
            RoleService,
            'clear_permission_cache',
        ) as clear_cache:
            mock_user_factory_model.query.filter_by.return_value.first.return_value = relation
            mock_user_model.query.filter_by.return_value.first.return_value = user

            success, error = FactoryService.remove_user_from_factory(1, 8)

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(relation.is_deleted, 1)
        relation.save.assert_called_once()
        sync_identity.assert_called_once_with(user)
        clear_cache.assert_called_once()

    def test_factory_service_delete_factory_clears_permission_cache(self):
        """删除工厂后应立即清空权限缓存，避免 owner/admin 命中旧缓存。"""
        factory = SimpleNamespace(is_deleted=0, save=MagicMock(), id=1)
        owner_relation = SimpleNamespace(is_deleted=0, save=MagicMock())
        non_owner_query = MagicMock()
        owner_query = MagicMock()
        non_owner_query.filter.return_value.count.return_value = 0
        owner_query.first.return_value = owner_relation

        with patch('app.services.system.factory_service.UserFactory') as mock_user_factory_model, patch.object(
            RoleService,
            'clear_permission_cache',
        ) as clear_cache:
            mock_user_factory_model.query.filter_by.side_effect = [non_owner_query, owner_query]

            success, error = FactoryService.delete_factory(factory)

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(owner_relation.is_deleted, 1)
        owner_relation.save.assert_called_once()
        factory.save.assert_called_once()
        clear_cache.assert_called_once()

    def test_get_permission_summary_for_platform_admin_uses_cached_all_permissions(self):
        """平台管理员权限汇总应缓存全量权限并在后续调用复用。"""
        user = SimpleNamespace(id=1, is_platform_admin=True)
        menu_query = MagicMock()
        menu_query.all.return_value = [
            SimpleNamespace(permission='business.orders.query'),
            SimpleNamespace(permission='business.orders.create'),
            SimpleNamespace(permission='business.orders.query'),
        ]

        with patch.object(UserService, 'get_user_by_id', return_value=user), patch.object(
            UserService,
            'get_user_role_bindings',
            return_value=[],
        ), patch('app.services.system.user_service.get_jwt', return_value={}), patch(
            'app.services.system.user_service.Menu',
        ) as mock_menu:
            mock_menu.query.filter.return_value = menu_query

            first_summary = UserService.get_permission_summary(1)
            second_summary = UserService.get_permission_summary(1)

        self.assertEqual(
            first_summary['all_permissions'],
            ['business.orders.create', 'business.orders.query'],
        )
        self.assertEqual(first_summary['current_permissions'], first_summary['all_permissions'])
        self.assertEqual(second_summary['all_permissions'], first_summary['all_permissions'])
        mock_menu.query.filter.assert_called_once()
        menu_query.all.assert_called_once()

    def test_get_permission_summary_for_external_user_returns_current_and_all_permissions(self):
        """外部用户权限汇总应区分当前上下文权限和全部角色权限。"""
        user = SimpleNamespace(id=8, is_platform_admin=False, is_internal_user=False)
        role_bindings = [{'role_id': 2}, {'role_id': 3}]

        with patch.object(UserService, 'get_user_by_id', return_value=user), patch.object(
            UserService,
            'get_user_role_bindings',
            return_value=role_bindings,
        ), patch('app.services.system.user_service.get_jwt', return_value={'factory_id': 12}), patch.object(
            UserService,
            'get_current_data_scope',
            return_value=ROLE_DATA_SCOPE_OWN_RELATED,
        ), patch.object(
            UserService,
            '_get_current_context_role_ids',
            return_value=[2],
        ), patch.object(
            UserService,
            '_get_permission_codes_by_role_ids',
            side_effect=[['business.orders.query'], ['business.orders.query', 'business.orders.create']],
        ) as permission_loader:
            summary = UserService.get_permission_summary(8)

        self.assertEqual(summary['current_factory_id'], 12)
        self.assertEqual(summary['current_permissions'], ['business.orders.query'])
        self.assertEqual(
            summary['all_permissions'],
            ['business.orders.query', 'business.orders.create'],
        )
        self.assertEqual(summary['role_bindings'], role_bindings)
        self.assertEqual(permission_loader.call_args_list[0].args[0], [2])
        self.assertEqual(permission_loader.call_args_list[1].args[0], [2, 3])

    def test_target_user_helper_returns_404(self):
        """用户详情辅助方法在资源缺失时应返回 404。"""
        with patch.object(UserService, 'get_user_by_id', return_value=None):
            user, error_response = get_target_user_or_error(1)

        self.assertIsNone(user)
        self.assertEqual(error_response[0]['code'], 404)

    def test_role_helper_returns_404(self):
        """角色详情辅助方法在资源缺失时应返回 404。"""
        with patch.object(RoleService, 'get_role_by_id', return_value=None):
            role, error_response = get_role_or_error(1)

        self.assertIsNone(role)
        self.assertEqual(error_response[0]['code'], 404)

    def test_common_resource_helper_returns_404(self):
        """公共资源 helper 应统一返回 404。"""
        resource, error_response = get_resource_or_error(lambda: None, '资源不存在')

        self.assertIsNone(resource)
        self.assertEqual(error_response[0]['code'], 404)

    def test_common_permission_helper_returns_403(self):
        """公共权限 helper 应统一返回 403。"""
        error_response = ensure_permission_or_error(False, '无权限访问')

        self.assertEqual(error_response[0]['code'], 403)


    def test_business_data_scope_service_uses_assigned_filter(self):
        """assigned 数据范围应优先命中 assigned 过滤条件。"""
        current_user = SimpleNamespace(id=9, is_platform_admin=False)
        query = MagicMock()
        filtered_query = MagicMock()
        query.filter.return_value = filtered_query

        with patch(
            'app.services.business.data_scope_service.UserService.get_current_data_scope',
            return_value=ROLE_DATA_SCOPE_ASSIGNED,
        ):
            result = BusinessDataScopeService.apply_scope(
                query,
                current_user,
                current_factory_id=1,
                assigned_filter='assigned-filter',
                own_related_filter='own-filter',
                self_only_filter='self-filter',
            )

        self.assertIs(result, filtered_query)
        query.filter.assert_called_once_with('assigned-filter')

    def test_business_data_scope_service_uses_own_related_filter(self):
        """own_related 数据范围应使用本人关联过滤条件。"""
        current_user = SimpleNamespace(id=9, is_platform_admin=False)
        query = MagicMock()
        filtered_query = MagicMock()
        query.filter.return_value = filtered_query

        with patch(
            'app.services.business.data_scope_service.UserService.get_current_data_scope',
            return_value=ROLE_DATA_SCOPE_OWN_RELATED,
        ):
            result = BusinessDataScopeService.apply_scope(
                query,
                current_user,
                current_factory_id=1,
                assigned_filter='assigned-filter',
                own_related_filter='own-filter',
                self_only_filter='self-filter',
            )

        self.assertIs(result, filtered_query)
        query.filter.assert_called_once_with('own-filter')

    def test_business_data_scope_service_uses_self_filter_for_self_only(self):
        """self_only 数据范围应使用个人数据过滤条件。"""
        current_user = SimpleNamespace(id=9, is_platform_admin=False)
        query = MagicMock()
        filtered_query = MagicMock()
        query.filter.return_value = filtered_query

        with patch(
            'app.services.business.data_scope_service.UserService.get_current_data_scope',
            return_value=ROLE_DATA_SCOPE_SELF_ONLY,
        ):
            result = BusinessDataScopeService.apply_scope(
                query,
                current_user,
                current_factory_id=1,
                assigned_filter='assigned-filter',
                own_related_filter='own-filter',
                self_only_filter='self-filter',
            )

        self.assertIs(result, filtered_query)
        query.filter.assert_called_once_with('self-filter')

    def test_business_data_scope_service_returns_original_query_for_all_scope(self):
        """all 数据范围下不应追加任何过滤。"""
        current_user = SimpleNamespace(id=9, is_platform_admin=False)
        query = MagicMock()

        with patch(
            'app.services.business.data_scope_service.UserService.get_current_data_scope',
            return_value=ROLE_DATA_SCOPE_ALL,
        ):
            result = BusinessDataScopeService.apply_scope(query, current_user, current_factory_id=1)

        self.assertIs(result, query)
        query.filter.assert_not_called()

    def test_business_data_scope_service_creator_customer_scope(self):
        """创建人/客户归属校验应复用统一业务 helper。"""
        current_user = SimpleNamespace(id=9, is_platform_admin=False)

        with patch(
            'app.services.business.data_scope_service.UserService.get_current_data_scope',
            return_value=ROLE_DATA_SCOPE_OWN_RELATED,
        ):
            allowed = BusinessDataScopeService.check_creator_customer_scope(
                current_user,
                current_factory_id=1,
                creator_user_id=8,
                customer_user_id=9,
            )
            denied = BusinessDataScopeService.check_creator_customer_scope(
                current_user,
                current_factory_id=1,
                creator_user_id=8,
                customer_user_id=7,
            )

        self.assertTrue(allowed)
        self.assertFalse(denied)

    def test_style_price_service_delegates_style_permission_to_style_service(self):
        """款号价格服务应统一复用款号访问解析。"""
        current_user = SimpleNamespace(id=9)
        expected_style = SimpleNamespace(id=3)

        with patch.object(StyleService, 'get_accessible_style', return_value=(expected_style, None)) as mock_get_style:
            style, error = StylePriceService.check_style_permission(current_user, 1, 3)

        self.assertIs(style, expected_style)
        self.assertIsNone(error)
        mock_get_style.assert_called_once_with(current_user, 1, 3)

    def test_style_process_and_elastic_permission_use_style_service(self):
        """款号工艺与橡筋服务应统一委托给款号访问解析。"""
        current_user = SimpleNamespace(id=9)
        process = SimpleNamespace(style_id=7)
        elastic = SimpleNamespace(style_id=7)

        with patch.object(StyleService, 'get_accessible_style', return_value=(SimpleNamespace(id=7), None)) as mock_get_style:
            process_allowed, process_error = StyleProcessService.check_process_permission(current_user, 1, process)
            elastic_allowed, elastic_error = StyleElasticService.check_elastic_permission(current_user, 1, elastic)

        self.assertTrue(process_allowed)
        self.assertIsNone(process_error)
        self.assertTrue(elastic_allowed)
        self.assertIsNone(elastic_error)
        self.assertEqual(mock_get_style.call_count, 2)

if __name__ == '__main__':
    unittest.main()
