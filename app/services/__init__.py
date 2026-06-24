"""服务层模块。"""

from app.services.auth import AUTH_SERVICE_EXPORTS, AuthService, LoginResponseBuilder
from app.services.base import BaseService
from app.services.base_data import BASE_DATA_SERVICE_EXPORTS, CategoryService, ColorService, SizeService
from app.services.business import (
    BUSINESS_SERVICE_EXPORTS,
    BundleService,
    BundleTemplateService,
    CollaborationTaskService,
    CuttingReportService,
    OrderService,
    ProcessService,
    ShipmentService,
    StyleElasticService,
    StylePriceService,
    StyleProcessService,
    StyleService,
)
from app.services.customer import CUSTOMER_SERVICE_EXPORTS, CustomerService, can_use_feature
from app.services.profile import PROFILE_SERVICE_EXPORTS, ProfileService
from app.services.system import (
    SYSTEM_SERVICE_EXPORTS,
    EmployeeWageService,
    FactoryService,
    LogService,
    MenuService,
    MonitorService,
    RewardService,
    RoleService,
    UserService,
)

__all__ = [
    "BaseService",
    *AUTH_SERVICE_EXPORTS,
    *SYSTEM_SERVICE_EXPORTS,
    *PROFILE_SERVICE_EXPORTS,
    *BASE_DATA_SERVICE_EXPORTS,
    *BUSINESS_SERVICE_EXPORTS,
    *CUSTOMER_SERVICE_EXPORTS,
]
