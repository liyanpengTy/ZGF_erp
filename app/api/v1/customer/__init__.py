"""V1 客户接口导出。"""

from app.api.common.namespace_registry import build_namespace_routes
from app.api.v1.customer.customers import customer_ns

NAMESPACE_ROUTES = build_namespace_routes(
    (customer_ns, '/customer'),
)

__all__ = [
    'customer_ns',
    'NAMESPACE_ROUTES',
]
