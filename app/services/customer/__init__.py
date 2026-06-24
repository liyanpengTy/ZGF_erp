"""客户服务导出。"""

from app.services.customer.customer_service import CustomerService
from app.services.customer.feature_service import can_use_feature

CUSTOMER_SERVICE_EXPORTS = (
    'CustomerService',
    'can_use_feature',
)

__all__ = list(CUSTOMER_SERVICE_EXPORTS)
