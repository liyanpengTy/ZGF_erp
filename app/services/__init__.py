"""服务层模块"""
from app.services.base import BaseService
from app.services.auth import AuthService, LoginResponseBuilder
from app.services.system import (
    UserService,
    RoleService,
    MenuService,
    FactoryService,
    LogService,
    MonitorService
)
from app.services.profile import ProfileService
from app.services.base_data import CategoryService, ColorService, SizeService
from app.services.business import (
    StyleService,
    StyleProcessService,
    StylePriceService,
    StyleElasticService,
    ProcessService,
    OrderService
)

__all__ = [
    # 基础服务
    'BaseService',

    # 认证服务
    'AuthService',
    'LoginResponseBuilder',

    # 系统管理服务
    'UserService',
    'RoleService',
    'MenuService',
    'FactoryService',
    'LogService',
    'MonitorService',

    # 个人中心服务
    'ProfileService',

    # 基础数据服务
    'CategoryService',
    'ColorService',
    'SizeService',

    # 业务模块服务
    'StyleService',
    'StyleProcessService',
    'StylePriceService',
    'StyleElasticService',
    'ProcessService',
    'OrderService'
]
