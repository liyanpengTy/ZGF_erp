"""V1 基础资料接口导出。"""

from app.api.v1.base_data.categories import category_ns
from app.api.v1.base_data.colors import color_ns
from app.api.v1.base_data.sizes import size_ns

NAMESPACE_ROUTES = [
    (size_ns, '/base/sizes'),
    (category_ns, '/base/categories'),
    (color_ns, '/base/colors'),
]

__all__ = ['category_ns', 'color_ns', 'size_ns', 'NAMESPACE_ROUTES']
