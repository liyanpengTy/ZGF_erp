"""底层架构回归测试。"""

import unittest
from types import SimpleNamespace

from app import create_app
from app.api.common.namespace_registry import (
    build_namespace_routes,
    merge_namespace_routes,
    validate_namespace_routes,
)
from app.api.common.serializers import build_mapping_serializer, safe_isoformat, serialize_schema
from app.core.exceptions import BusinessException, ValidationException
from app.extensions import NotFoundException


class ArchitectureTests(unittest.TestCase):
    """覆盖应用启动层与命名空间注册层。"""

    def test_create_app_loads_v1_routes(self):
        """应用工厂应能完成启动并注册 V1 路由。"""
        app = create_app()

        self.assertGreater(len(app.url_map._rules), 0)
        self.assertTrue(any(rule.rule.startswith('/api/v1/') for rule in app.url_map.iter_rules()))

    def test_build_namespace_routes_returns_list(self):
        """单模块命名空间构建器应返回稳定列表结构。"""
        namespace = SimpleNamespace(name='test-ns')

        routes = build_namespace_routes((namespace, '/test'))

        self.assertEqual(routes, [(namespace, '/test')])

    def test_merge_namespace_routes_rejects_duplicate_paths(self):
        """合并命名空间时应阻止不同名称共用同一路径。"""
        namespace_a = SimpleNamespace(name='ns-a')
        namespace_b = SimpleNamespace(name='ns-b')

        with self.assertRaises(ValueError):
            merge_namespace_routes(
                [(namespace_a, '/same-path')],
                [(namespace_b, '/same-path')],
            )

    def test_validate_namespace_routes_rejects_name_collision_with_different_path(self):
        """同名命名空间不允许挂到不同路径。"""
        namespace_a = SimpleNamespace(name='same-name')
        namespace_b = SimpleNamespace(name='same-name')

        with self.assertRaises(ValueError):
            validate_namespace_routes(
                [
                    (namespace_a, '/path-a'),
                    (namespace_b, '/path-b'),
                ]
            )

    def test_core_exceptions_and_extensions_reexport_stay_consistent(self):
        """核心异常与兼容导出应保持可用。"""
        self.assertTrue(issubclass(NotFoundException, BusinessException))
        self.assertTrue(issubclass(ValidationException, BusinessException))

    def test_serializer_helpers_keep_mapping_and_enricher_behavior(self):
        """通用序列化 helper 应支持映射字段、日期格式化和后置补充。"""

        class DummySchema:
            def dump(self, obj):
                return {'id': obj.id}

        dummy = SimpleNamespace(id=7, code='A-01', created_at=None)
        serializer = build_mapping_serializer(
            {
                'id': 'id',
                'code': 'code',
                'created_at': ('created_at', safe_isoformat),
            }
        )

        self.assertEqual(
            serialize_schema(
                DummySchema(),
                dummy,
                enricher=lambda payload, _: {**payload, 'code': 'patched'},
            ),
            {'id': 7, 'code': 'patched'},
        )
        self.assertEqual(
            serializer(dummy),
            {'id': 7, 'code': 'A-01', 'created_at': None},
        )


if __name__ == '__main__':
    unittest.main()
