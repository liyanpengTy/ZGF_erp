"""业务模块接口"""
from app.api.v1.business.styles import style_ns
from app.api.v1.business.style_processes import style_process_ns
from app.api.v1.business.style_prices import style_price_ns
from app.api.v1.business.style_elastics import style_elastic_ns
from app.api.v1.business.processes import process_ns
from app.api.v1.business.orders import order_ns

__all__ = [
    'style_ns',
    'style_process_ns',
    'style_price_ns',
    'style_elastic_ns',
    'process_ns',
    'order_ns'
]
