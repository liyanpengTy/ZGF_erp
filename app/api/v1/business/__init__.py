"""V1 业务接口导出。"""

from app.api.v1.business.bundle_templates import bundle_template_ns
from app.api.v1.business.bundles import bundle_ns
from app.api.v1.business.cutting_reports import cutting_report_ns
from app.api.v1.business.orders import order_ns
from app.api.v1.business.processes import process_ns
from app.api.v1.business.shipments import shipment_ns
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
    (shipment_ns, '/business/shipments'),
    (bundle_template_ns, '/business/bundle-templates'),
    (cutting_report_ns, '/business/cutting-reports'),
    (bundle_ns, '/business/bundles'),
]

__all__ = [
    'bundle_template_ns',
    'cutting_report_ns',
    'bundle_ns',
    'style_ns',
    'style_process_ns',
    'style_price_ns',
    'style_elastic_ns',
    'process_ns',
    'order_ns',
    'shipment_ns',
    'NAMESPACE_ROUTES',
]
