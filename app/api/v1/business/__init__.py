"""V1 业务接口导出。"""

from app.api.v1.business.orders import order_ns
from app.api.v1.business.processes import process_ns
from app.api.v1.business.style_elastics import style_elastic_ns
from app.api.v1.business.style_prices import style_price_ns
from app.api.v1.business.style_processes import style_process_ns
from app.api.v1.business.styles import style_ns

NAMESPACE_ROUTES = [
    (style_ns, '/business/styles'),
    (style_price_ns, '/business/style-prices'),
    (style_process_ns, '/business/style-processes'),
    (style_elastic_ns, '/business/style-elastics'),
    (process_ns, '/business/processes'),
    (order_ns, '/business/orders'),
]

__all__ = [
    'style_ns',
    'style_process_ns',
    'style_price_ns',
    'style_elastic_ns',
    'process_ns',
    'order_ns',
    'NAMESPACE_ROUTES',
]
