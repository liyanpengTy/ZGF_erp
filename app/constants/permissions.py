"""接口权限码常量，必须和 sys_menu.permission 保持一致。"""

PERM_BASE_SIZE_QUERY = 'base.sizes.browse'
PERM_BASE_SIZE_ADD = 'base.sizes.create'
PERM_BASE_SIZE_EDIT = 'base.sizes.update'
PERM_BASE_SIZE_DELETE = 'base.sizes.delete'

PERM_BASE_CATEGORY_QUERY = 'base.categories.browse'
PERM_BASE_CATEGORY_ADD = 'base.categories.create'
PERM_BASE_CATEGORY_EDIT = 'base.categories.update'
PERM_BASE_CATEGORY_DELETE = 'base.categories.delete'

PERM_BASE_COLOR_QUERY = 'base.colors.browse'
PERM_BASE_COLOR_ADD = 'base.colors.create'
PERM_BASE_COLOR_EDIT = 'base.colors.update'
PERM_BASE_COLOR_DELETE = 'base.colors.delete'

PERM_BUSINESS_STYLE_QUERY = 'business.styles.browse'
PERM_BUSINESS_STYLE_ADD = 'business.styles.create'
PERM_BUSINESS_STYLE_EDIT = 'business.styles.update'
PERM_BUSINESS_STYLE_DELETE = 'business.styles.delete'

PERM_BUSINESS_STYLE_ELASTIC_QUERY = 'business.style-elastics.browse'
PERM_BUSINESS_STYLE_ELASTIC_ADD = 'business.style-elastics.create'
PERM_BUSINESS_STYLE_ELASTIC_EDIT = 'business.style-elastics.update'
PERM_BUSINESS_STYLE_ELASTIC_DELETE = 'business.style-elastics.delete'

PERM_BUSINESS_STYLE_PRICE_QUERY = 'business.style-prices.browse'
PERM_BUSINESS_STYLE_PRICE_ADD = 'business.style-prices.create'
PERM_BUSINESS_STYLE_PRICE_DELETE = 'business.style-prices.delete'

PERM_BUSINESS_STYLE_PROCESS_QUERY = 'business.style-processes.browse'
PERM_BUSINESS_STYLE_PROCESS_ADD = 'business.style-processes.create'
PERM_BUSINESS_STYLE_PROCESS_EDIT = 'business.style-processes.update'
PERM_BUSINESS_STYLE_PROCESS_DELETE = 'business.style-processes.delete'

PERM_BUSINESS_PROCESS_QUERY = 'business.processes.browse'
PERM_BUSINESS_PROCESS_ADD = 'business.processes.create'
PERM_BUSINESS_PROCESS_EDIT = 'business.processes.update'
PERM_BUSINESS_PROCESS_DELETE = 'business.processes.delete'

PERM_BUSINESS_ORDER_QUERY = 'business.orders.browse'
PERM_BUSINESS_ORDER_ADD = 'business.orders.create'
PERM_BUSINESS_ORDER_EDIT = 'business.orders.update'
PERM_BUSINESS_ORDER_DELETE = 'business.orders.delete'

PERM_BUSINESS_CUTTING_REPORT_QUERY = 'business.cutting-reports.browse'
PERM_BUSINESS_CUTTING_REPORT_ADD = 'business.cutting-reports.create'
PERM_BUSINESS_CUTTING_REPORT_DELETE = 'business.cutting-reports.delete'

PERM_BUSINESS_BUNDLE_QUERY = 'business.bundles.browse'
PERM_BUSINESS_BUNDLE_ISSUE = 'business.bundles.issue'
PERM_BUSINESS_BUNDLE_RETURN = 'business.bundles.return'
PERM_BUSINESS_BUNDLE_TRANSFER = 'business.bundles.transfer'
PERM_BUSINESS_BUNDLE_COMPLETE = 'business.bundles.complete'
PERM_BUSINESS_BUNDLE_PRINT = 'business.bundles.print'

PERM_BUSINESS_BUNDLE_TEMPLATE_QUERY = 'business.bundle-templates.browse'
PERM_BUSINESS_BUNDLE_TEMPLATE_ADD = 'business.bundle-templates.create'
PERM_BUSINESS_BUNDLE_TEMPLATE_EDIT = 'business.bundle-templates.update'
PERM_BUSINESS_BUNDLE_TEMPLATE_DELETE = 'business.bundle-templates.delete'
PERM_BUSINESS_BUNDLE_RULE_EDIT = PERM_BUSINESS_BUNDLE_TEMPLATE_EDIT

PERM_BUSINESS_SHIPMENT_QUERY = 'business.shipments.browse'
PERM_BUSINESS_SHIPMENT_ADD = 'business.shipments.create'
PERM_BUSINESS_SHIPMENT_CANCEL = 'business.shipments.cancel'

PERM_FACTORY_MANAGEMENT_USER_QUERY = 'factory-management.users.browse'
PERM_FACTORY_MANAGEMENT_USER_ADD = 'factory-management.users.create'
PERM_FACTORY_MANAGEMENT_USER_EDIT = 'factory-management.users.update'
PERM_FACTORY_MANAGEMENT_USER_DELETE = 'factory-management.users.delete'

PERM_FACTORY_MANAGEMENT_ROLE_QUERY = 'factory-management.roles.browse'
PERM_FACTORY_MANAGEMENT_ROLE_ADD = 'factory-management.roles.create'
PERM_FACTORY_MANAGEMENT_ROLE_EDIT = 'factory-management.roles.update'
PERM_FACTORY_MANAGEMENT_ROLE_DELETE = 'factory-management.roles.delete'

PERM_FACTORY_MANAGEMENT_EMPLOYEE_WAGE_QUERY = 'factory-management.employee-wages.browse'
PERM_FACTORY_MANAGEMENT_EMPLOYEE_WAGE_ADD = 'factory-management.employee-wages.create'
PERM_FACTORY_MANAGEMENT_EMPLOYEE_WAGE_EDIT = 'factory-management.employee-wages.update'
PERM_FACTORY_MANAGEMENT_EMPLOYEE_WAGE_DELETE = 'factory-management.employee-wages.delete'

PERM_SYSTEM_USER_QUERY = 'system.users.browse'
PERM_SYSTEM_USER_ADD = 'system.users.create'
PERM_SYSTEM_USER_EDIT = 'system.users.update'
PERM_SYSTEM_USER_DELETE = 'system.users.delete'

PERM_SYSTEM_ROLE_QUERY = 'system.roles.browse'
PERM_SYSTEM_ROLE_ADD = 'system.roles.create'
PERM_SYSTEM_ROLE_EDIT = 'system.roles.update'
PERM_SYSTEM_ROLE_DELETE = 'system.roles.delete'

PERM_SYSTEM_MENU_QUERY = 'system.menus.browse'
PERM_SYSTEM_MENU_ADD = 'system.menus.create'
PERM_SYSTEM_MENU_EDIT = 'system.menus.update'
PERM_SYSTEM_MENU_DELETE = 'system.menus.delete'

PERM_SYSTEM_FACTORY_QUERY = 'system.factories.browse'
PERM_SYSTEM_FACTORY_ADD = 'system.factories.create'
PERM_SYSTEM_FACTORY_EDIT = 'system.factories.update'
PERM_SYSTEM_FACTORY_DELETE = 'system.factories.delete'
PERM_SYSTEM_FACTORY_MANAGE_ROLES = 'system.factories.manage-roles'

PERM_SYSTEM_REWARD_QUERY = 'system.rewards.browse'
PERM_SYSTEM_REWARD_DISTRIBUTE = 'system.rewards.distribute'
