"""身份、关系与数据范围常量。"""

PLATFORM_IDENTITY_ADMIN = 'platform_admin'
PLATFORM_IDENTITY_STAFF = 'platform_staff'
PLATFORM_IDENTITY_EXTERNAL = 'external_user'

USER_TYPE_INTERNAL = 'internal'
USER_TYPE_SUBJECT = 'subject_user'
USER_TYPE_CUSTOMER = 'customer'

USER_TYPES = {
    USER_TYPE_INTERNAL,
    USER_TYPE_SUBJECT,
    USER_TYPE_CUSTOMER,
}

INTERNAL_PLATFORM_IDENTITIES = {
    PLATFORM_IDENTITY_ADMIN,
    PLATFORM_IDENTITY_STAFF,
}

SUBJECT_TYPE_FACTORY = 'factory_subject'
SUBJECT_TYPE_PARTNER = 'partner_subject'
SUBJECT_TYPE_INDIVIDUAL = 'individual_subject'

SUBJECT_CATEGORY_FACTORY = 'factory'
SUBJECT_CATEGORY_BUTTON = 'button_shop'
SUBJECT_CATEGORY_SHRINK = 'shrink_factory'
SUBJECT_CATEGORY_PRINT = 'print_factory'
SUBJECT_CATEGORY_OTHER = 'other'

SUBJECT_CATEGORIES = {
    SUBJECT_CATEGORY_FACTORY,
    SUBJECT_CATEGORY_BUTTON,
    SUBJECT_CATEGORY_SHRINK,
    SUBJECT_CATEGORY_PRINT,
    SUBJECT_CATEGORY_OTHER,
}

RELATION_TYPE_OWNER = 'owner'
RELATION_TYPE_EMPLOYEE = 'employee'
RELATION_TYPE_CUSTOMER = 'customer'
RELATION_TYPE_COLLABORATOR = 'collaborator'

RELATION_TYPES = {
    RELATION_TYPE_OWNER,
    RELATION_TYPE_EMPLOYEE,
    RELATION_TYPE_CUSTOMER,
    RELATION_TYPE_COLLABORATOR,
}

COLLABORATOR_TYPE_BUTTON = 'button_partner'
COLLABORATOR_TYPE_SHRINK = 'shrink_partner'
COLLABORATOR_TYPE_PRINT = 'print_partner'
COLLABORATOR_TYPE_OTHER = 'other_partner'

COLLABORATOR_TYPES = {
    COLLABORATOR_TYPE_BUTTON,
    COLLABORATOR_TYPE_SHRINK,
    COLLABORATOR_TYPE_PRINT,
    COLLABORATOR_TYPE_OTHER,
}

ROLE_DATA_SCOPE_ALL = 'all_factory'
ROLE_DATA_SCOPE_ASSIGNED = 'assigned'
ROLE_DATA_SCOPE_OWN_RELATED = 'own_related'
ROLE_DATA_SCOPE_SELF_ONLY = 'self_only'

ROLE_SCOPE_PLATFORM = 'platform'
ROLE_SCOPE_FACTORY = 'factory'
ROLE_SCOPE_PARTNER = 'partner_subject'
ROLE_SCOPE_SUBJECT = 'subject'

ROLE_DATA_SCOPES = {
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_DATA_SCOPE_SELF_ONLY,
}

ROLE_SCOPES = {
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_FACTORY,
    ROLE_SCOPE_PARTNER,
    ROLE_SCOPE_SUBJECT,
}

CUSTOMER_RELATION_STATUS_ACTIVE = 'active'
CUSTOMER_RELATION_STATUS_INACTIVE = 'inactive'

CUSTOMER_INVITE_EXPIRE_WEEK = 'week'
CUSTOMER_INVITE_EXPIRE_MONTH = 'month'
CUSTOMER_INVITE_EXPIRE_YEAR = 'year'
CUSTOMER_INVITE_STATUS_ACTIVE = 'active'
CUSTOMER_INVITE_STATUS_EXPIRED = 'expired'

CUSTOMER_TIER_FREE = 'free'
CUSTOMER_TIER_PRO = 'pro'
CUSTOMER_TIER_ENTERPRISE = 'enterprise'

COLLABORATION_STATUS_PENDING = 'pending'
COLLABORATION_STATUS_ACCEPTED = 'accepted'
COLLABORATION_STATUS_IN_PROGRESS = 'in_progress'
COLLABORATION_STATUS_COMPLETED = 'completed'

FREE_FEATURES = {
    'customer_order_list',
    'customer_order_detail',
    'customer_subject_relation',
}

WRITE_PERMISSION_SUFFIXES = (
    '.create',
    '.update',
    '.delete',
    '.assign',
    '.distribute',
    '.reset',
    '.bind',
    '.cancel',
    '.issue',
    '.return',
    '.transfer',
    '.complete',
    '.print',
    '.manage-roles',
)


def is_internal_platform_identity(platform_identity):
    """判断平台身份是否属于平台内部人员。"""
    return platform_identity in INTERNAL_PLATFORM_IDENTITIES


def infer_subject_type(platform_identity, relation_types=None):
    """根据平台身份和工厂关系推断主体类型。"""
    relation_types = set(relation_types or [])
    if RELATION_TYPE_OWNER in relation_types:
        return SUBJECT_TYPE_FACTORY
    if RELATION_TYPE_COLLABORATOR in relation_types:
        return SUBJECT_TYPE_PARTNER
    if platform_identity in INTERNAL_PLATFORM_IDENTITIES:
        return SUBJECT_TYPE_INDIVIDUAL
    return SUBJECT_TYPE_INDIVIDUAL


def is_write_permission(permission_code):
    """根据权限编码后缀判断是否属于写操作权限。"""
    return permission_code.endswith(WRITE_PERMISSION_SUFFIXES)
