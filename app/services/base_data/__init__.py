"""基础资料服务导出。"""

from app.services.base_data.category_service import CategoryService
from app.services.base_data.color_service import ColorService
from app.services.base_data.size_service import SizeService

BASE_DATA_SERVICE_EXPORTS = (
    'CategoryService',
    'ColorService',
    'SizeService',
)

__all__ = list(BASE_DATA_SERVICE_EXPORTS)
