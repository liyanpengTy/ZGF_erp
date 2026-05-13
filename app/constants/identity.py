"""身份、关系和权限范围常量。"""

PLATFORM_IDENTITY_ADMIN = 'platform_admin'
PLATFORM_IDENTITY_STAFF = 'platform_staff'
PLATFORM_IDENTITY_EXTERNAL = 'external_user'

INTERNAL_PLATFORM_IDENTITIES = {
    PLATFORM_IDENTITY_ADMIN,
    PLATFORM_IDENTITY_STAFF,
}

SUBJECT_TYPE_FACTORY = 'factory_subject'
SUBJECT_TYPE_PARTNER = 'partner_subject'
SUBJECT_TYPE_INDIVIDUAL = 'individual_subject'

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

ROLE_DATA_SCOPES = {
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_DATA_SCOPE_SELF_ONLY,
}

WRITE_PERMISSION_SUFFIXES = (
    ':add',
    ':edit',
    ':delete',
    ':assign',
    ':distribute',
    ':reset',
    ':bind',
)


def is_internal_platform_identity(platform_identity):
    """判断平台身份是否属于平台内部人员。"""
    return platform_identity in INTERNAL_PLATFORM_IDENTITIES


def infer_subject_type(platform_identity, relation_types=None):
    """根据平台身份和工厂关系推导主体类型。"""
    relation_types = set(relation_types or [])
    if RELATION_TYPE_OWNER in relation_types:
        return SUBJECT_TYPE_FACTORY
    if RELATION_TYPE_COLLABORATOR in relation_types:
        return SUBJECT_TYPE_PARTNER
    if platform_identity in INTERNAL_PLATFORM_IDENTITIES:
        return SUBJECT_TYPE_INDIVIDUAL
    return SUBJECT_TYPE_INDIVIDUAL


def is_write_permission(permission_code):
    """根据权限编码后缀判断当前权限是否属于写操作。"""
    return permission_code.endswith(WRITE_PERMISSION_SUFFIXES)
