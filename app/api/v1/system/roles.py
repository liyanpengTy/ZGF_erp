"""角色管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.api.common.auth import require_current_user
from app.api.common.context_helpers import get_factory_request_context
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.api.common.resource_helpers import ensure_permission_or_error, get_resource_or_error
from app.api.common.response_helpers import load_json_or_error, success_mapped_page
from app.constants.identity import ROLE_SCOPE_FACTORY, ROLE_SCOPE_PLATFORM, ROLE_SCOPE_SUBJECT
from app.constants.permissions import (
    PERM_FACTORY_MANAGEMENT_ROLE_ADD,
    PERM_FACTORY_MANAGEMENT_ROLE_DELETE,
    PERM_FACTORY_MANAGEMENT_ROLE_EDIT,
    PERM_FACTORY_MANAGEMENT_ROLE_QUERY,
    PERM_SYSTEM_ROLE_ADD,
    PERM_SYSTEM_ROLE_DELETE,
    PERM_SYSTEM_ROLE_EDIT,
    PERM_SYSTEM_ROLE_QUERY,
)
from app.schemas.system.role import RoleAssignMenuSchema, RoleCreateSchema, RoleUpdateSchema
from app.services import RoleService
from app.utils.permissions import has_any_permission, login_required, permission_required_any
from app.utils.response import ApiResponse

role_ns = Namespace('角色管理-roles', description='角色管理')

common = get_common_models(role_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_item_response_model = common['build_item_response_model']
build_list_response_model = common['build_list_response_model']

ROLE_SCOPE_CHOICES = [ROLE_SCOPE_PLATFORM, ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT]
ROLE_DATA_SCOPE_CHOICES = ['all_factory', 'assigned', 'own_related', 'self_only', 'subject']
ROLE_QUERY_PERMISSION_CODES = [PERM_SYSTEM_ROLE_QUERY, PERM_FACTORY_MANAGEMENT_ROLE_QUERY]
ROLE_CREATE_PERMISSION_CODES = [PERM_SYSTEM_ROLE_ADD, PERM_FACTORY_MANAGEMENT_ROLE_ADD]
ROLE_EDIT_PERMISSION_CODES = [PERM_SYSTEM_ROLE_EDIT, PERM_FACTORY_MANAGEMENT_ROLE_EDIT]
ROLE_DELETE_PERMISSION_CODES = [PERM_SYSTEM_ROLE_DELETE, PERM_FACTORY_MANAGEMENT_ROLE_DELETE]
ROLE_SYSTEM_PERMISSION_MAP = {
    'query': PERM_SYSTEM_ROLE_QUERY,
    'create': PERM_SYSTEM_ROLE_ADD,
    'edit': PERM_SYSTEM_ROLE_EDIT,
    'delete': PERM_SYSTEM_ROLE_DELETE,
}
ROLE_FACTORY_PERMISSION_MAP = {
    'query': PERM_FACTORY_MANAGEMENT_ROLE_QUERY,
    'create': PERM_FACTORY_MANAGEMENT_ROLE_ADD,
    'edit': PERM_FACTORY_MANAGEMENT_ROLE_EDIT,
    'delete': PERM_FACTORY_MANAGEMENT_ROLE_DELETE,
}

role_query_parser = page_parser.copy()
role_query_parser.add_argument('name', type=str, location='args', help='角色名称，支持模糊查询')
role_query_parser.add_argument('status', type=int, location='args', help='角色状态', choices=[0, 1])
role_query_parser.add_argument(
    'scope_type',
    type=str,
    location='args',
    help='角色归属范围，可选 platform、factory、subject',
    choices=ROLE_SCOPE_CHOICES,
)
role_query_parser.add_argument('scope_id', type=int, location='args', help='角色归属主键，工厂或主体角色传对应 ID')

role_option_query_parser = new_query_parser()
role_option_query_parser.add_argument('name', type=str, location='args', help='角色名称，支持模糊查询')
role_option_query_parser.add_argument('status', type=int, location='args', help='角色状态', choices=[0, 1])
role_option_query_parser.add_argument(
    'scope_type',
    type=str,
    location='args',
    help='角色归属范围，可选 platform、factory、subject',
    choices=ROLE_SCOPE_CHOICES,
)
role_option_query_parser.add_argument('scope_id', type=int, location='args', help='角色归属主键，工厂或主体角色传对应 ID')

role_detail_query_parser = new_query_parser()
role_detail_query_parser.add_argument(
    'scope_type',
    type=str,
    location='args',
    help='角色归属范围，可选 platform、factory、subject',
    choices=ROLE_SCOPE_CHOICES,
)
role_detail_query_parser.add_argument('scope_id', type=int, location='args', help='角色归属主键，主体角色建议同时传入')

role_create_model = role_ns.model(
    'RoleCreate',
    {
        'scope_type': fields.String(
            description='角色归属范围。平台用户可传 platform、factory、subject；外部用户默认固定为 subject',
            choices=ROLE_SCOPE_CHOICES,
            example='subject',
        ),
        'scope_id': fields.Integer(
            description='角色归属主键。platform 可不传；factory 或 subject 必须传对应工厂 ID',
            example=1,
        ),
        'name': fields.String(required=True, description='角色名称', example='工厂管理员'),
        'code': fields.String(required=True, description='角色编码', example='factory_admin'),
        'description': fields.String(description='角色说明', example='工厂内完整管理权限'),
        'sort_order': fields.Integer(description='排序值', default=0, example=1),
        'data_scope': fields.String(
            description='数据范围。主体角色推荐使用 subject',
            choices=ROLE_DATA_SCOPE_CHOICES,
            example='subject',
        ),
        'is_factory_admin': fields.Integer(description='是否管理员角色', choices=[0, 1], example=1),
    },
)

role_update_model = role_ns.model(
    'RoleUpdate',
    {
        'name': fields.String(description='角色名称', example='工厂管理员'),
        'description': fields.String(description='角色说明', example='工厂内完整管理权限'),
        'status': fields.Integer(description='角色状态', example=1, choices=[0, 1]),
        'sort_order': fields.Integer(description='排序值', example=1),
        'data_scope': fields.String(
            description='数据范围。主体角色推荐使用 subject',
            choices=ROLE_DATA_SCOPE_CHOICES,
        ),
        'is_factory_admin': fields.Integer(description='是否管理员角色', choices=[0, 1]),
    },
)

role_assign_menu_model = role_ns.model(
    'RoleAssignMenu',
    {
        'menu_ids': fields.List(fields.Integer, required=True, description='菜单 ID 列表', example=[1, 2, 3]),
    },
)

role_item_model = role_ns.model(
    'RoleItem',
    {
        'id': fields.Integer(description='角色 ID'),
        'scope_type': fields.String(description='角色归属范围编码'),
        'scope_type_label': fields.String(description='角色归属范围名称'),
        'scope_id': fields.Integer(description='角色归属主键'),
        'name': fields.String(description='角色名称'),
        'code': fields.String(description='角色编码'),
        'description': fields.String(description='角色说明'),
        'status': fields.Integer(description='角色状态'),
        'sort_order': fields.Integer(description='排序值'),
        'data_scope': fields.String(description='数据范围编码'),
        'data_scope_label': fields.String(description='数据范围名称'),
        'is_factory_admin': fields.Integer(description='是否管理员角色'),
        'create_time': fields.String(description='创建时间'),
        'update_time': fields.String(description='更新时间'),
    },
)

role_option_model = role_ns.model(
    'RoleOptionItem',
    {
        'id': fields.Integer(description='角色 ID', example=1),
        'name': fields.String(description='角色名称', example='工厂管理员'),
        'code': fields.String(description='角色编码', example='factory_admin'),
        'scope_type': fields.String(description='角色归属范围编码', example='subject'),
        'scope_type_label': fields.String(description='角色归属范围名称', example='主体角色'),
        'scope_id': fields.Integer(description='角色归属主键', example=1),
        'is_factory_admin': fields.Integer(description='是否管理员角色', example=1),
    },
)

role_list_data = role_ns.model(
    'RoleListData',
    {
        'items': fields.List(fields.Nested(role_item_model), description='角色列表'),
        'total': fields.Integer(description='总条数'),
        'page': fields.Integer(description='当前页码'),
        'page_size': fields.Integer(description='每页条数'),
        'pages': fields.Integer(description='总页数'),
    },
)

role_list_response = role_ns.clone('RoleListResponse', base_response, {'data': fields.Nested(role_list_data, description='角色分页数据')})
role_item_response = build_item_response_model(role_ns, 'RoleItemResponse', base_response, role_item_model, '角色详情数据')
role_options_response = build_list_response_model(role_ns, 'RoleOptionsResponse', base_response, role_option_model, '角色下拉选项列表')
menu_ids_response = role_ns.clone('MenuIdsResponse', base_response, {'data': fields.List(fields.Integer, description='菜单 ID 列表')})

role_user_item_model = role_ns.model(
    'RoleUserItem',
    {
        'id': fields.Integer(description='用户 ID'),
        'username': fields.String(description='用户名'),
        'nickname': fields.String(description='昵称'),
        'phone': fields.String(description='手机号'),
        'status': fields.Integer(description='用户状态'),
    },
)

role_users_response = build_list_response_model(role_ns, 'RoleUsersResponse', base_response, role_user_item_model, '角色下的用户列表')

role_create_schema = RoleCreateSchema()
role_update_schema = RoleUpdateSchema()
role_assign_menu_schema = RoleAssignMenuSchema()


def get_required_role_user():
    """获取当前登录用户，不存在时返回统一错误响应。"""
    return require_current_user()


def get_role_or_error(role_id):
    """按角色 ID 查询基础角色资源，不存在时返回统一 404。"""
    return get_resource_or_error(lambda: RoleService.get_role_by_id(role_id), '角色不存在')


def get_role_request_context(query_factory_id=None, allow_internal_without_factory=False):
    """解析角色接口所需的工厂上下文。"""
    return get_factory_request_context(
        query_factory_id=query_factory_id,
        allow_internal_without_factory=allow_internal_without_factory,
    )


def serialize_role_option(role):
    """序列化角色下拉选项。"""
    data = RoleService.serialize_role(role)
    return {
        'id': data['id'],
        'name': data['name'],
        'code': data['code'],
        'scope_type': data['scope_type'],
        'scope_type_label': data['scope_type_label'],
        'scope_id': data['scope_id'],
        'is_factory_admin': data['is_factory_admin'],
    }


def serialize_role_user(user):
    """序列化角色关联用户。"""
    return {
        'id': user.id,
        'username': user.username,
        'nickname': user.nickname,
        'phone': user.phone,
        'status': user.status,
    }


def normalize_role_filters(current_user, current_factory_id, filters):
    """按当前用户按钮权限收敛可查询的角色范围。"""
    normalized = dict(filters)
    if not current_user or not current_user.is_internal_user:
        if not normalized.get('scope_type'):
            normalized['scope_type'] = ROLE_SCOPE_SUBJECT
        if normalized.get('scope_type') == ROLE_SCOPE_SUBJECT and not normalized.get('scope_id'):
            normalized['scope_id'] = current_factory_id
        return normalized, None

    has_system_permission, _ = has_any_permission(current_user, [ROLE_SYSTEM_PERMISSION_MAP['query']])
    if has_system_permission:
        return normalized, None

    if normalized.get('scope_type') == ROLE_SCOPE_PLATFORM:
        return None, '无权限查看平台角色'

    if not normalized.get('scope_type'):
        normalized['scope_type'] = ROLE_SCOPE_SUBJECT
    if normalized.get('scope_type') in {ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT} and not normalized.get('scope_id'):
        if current_factory_id:
            normalized['scope_id'] = current_factory_id
        else:
            return None, '请指定 scope_id 或先切换工厂上下文'
    return normalized, None


def resolve_role_resource(role_id, current_user, current_factory_id, scope_type=None, scope_id=None):
    """根据范围参数定位统一角色资源。"""
    effective_scope_type = scope_type
    effective_scope_id = scope_id

    if not effective_scope_type and not current_user.is_internal_user:
        effective_scope_type = ROLE_SCOPE_SUBJECT
        effective_scope_id = effective_scope_id or current_factory_id

    role = RoleService.get_role_resource(role_id, scope_type=effective_scope_type, scope_id=effective_scope_id)
    if role:
        return role, effective_scope_type, effective_scope_id, None

    if not effective_scope_type and current_user.is_internal_user:
        role = RoleService.get_role_resource(role_id, scope_type=ROLE_SCOPE_SUBJECT, scope_id=effective_scope_id)
        if role:
            return role, ROLE_SCOPE_SUBJECT, effective_scope_id, None

    return None, effective_scope_type, effective_scope_id, ApiResponse.error('角色不存在', 404)


def check_role_scope_permission(current_user, role, action, current_factory_id=None):
    """按角色归属范围校验当前用户是否可以操作该角色。"""
    if not current_user or not role:
        return False, '角色不存在'

    role_scope_type = RoleService.get_role_scope_type(role)
    role_scope_id = RoleService.get_role_scope_id(role)

    if role_scope_type == ROLE_SCOPE_PLATFORM:
        if not current_user.is_internal_user:
            return False, '只有平台内部用户可以访问平台角色'
        return has_any_permission(current_user, [ROLE_SYSTEM_PERMISSION_MAP[action]])

    if role_scope_type == ROLE_SCOPE_FACTORY:
        if current_user.is_internal_user:
            return has_any_permission(
                current_user,
                [ROLE_SYSTEM_PERMISSION_MAP[action], ROLE_FACTORY_PERMISSION_MAP[action]],
                factory_id=role_scope_id,
            )
        if current_factory_id and role_scope_id != current_factory_id:
            return False, '无权限跨工厂操作角色'
        if not RoleService.has_factory_admin_permission(current_user, role_scope_id):
            return False, '只有本工厂管理员可以操作角色'
        return has_any_permission(current_user, [ROLE_FACTORY_PERMISSION_MAP[action]], factory_id=role_scope_id)

    if role_scope_type == ROLE_SCOPE_SUBJECT:
        if current_user.is_internal_user:
            return has_any_permission(
                current_user,
                [ROLE_SYSTEM_PERMISSION_MAP[action], ROLE_FACTORY_PERMISSION_MAP[action]],
                factory_id=role_scope_id,
            )
        if current_factory_id and role_scope_id != current_factory_id:
            return False, '无权限跨主体操作角色'
        if not RoleService.has_factory_admin_permission(current_user, role_scope_id):
            return False, '只有本工厂管理员可以操作主体角色'
        return has_any_permission(current_user, [ROLE_FACTORY_PERMISSION_MAP[action]], factory_id=role_scope_id)

    return False, '当前接口暂不支持该角色范围'


def check_role_create_permission(current_user, scope_type, scope_id=None, current_factory_id=None):
    """按待创建角色的归属范围校验创建权限。"""
    if not current_user:
        return False, '用户不存在'

    if scope_type == ROLE_SCOPE_PLATFORM:
        if not current_user.is_internal_user:
            return False, '只有平台内部用户可以创建平台角色'
        return has_any_permission(current_user, [ROLE_SYSTEM_PERMISSION_MAP['create']])

    if scope_type in {ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT}:
        target_factory_id = scope_id or current_factory_id
        if not target_factory_id:
            return False, '工厂或主体角色必须指定 scope_id'
        if current_user.is_internal_user:
            return has_any_permission(
                current_user,
                [ROLE_SYSTEM_PERMISSION_MAP['create'], ROLE_FACTORY_PERMISSION_MAP['create']],
                factory_id=target_factory_id,
            )
        if current_factory_id and target_factory_id != current_factory_id:
            return False, '无权限跨工厂创建角色'
        if not RoleService.has_factory_admin_permission(current_user, target_factory_id):
            return False, '只有本工厂管理员可以创建角色'
        return has_any_permission(current_user, [ROLE_FACTORY_PERMISSION_MAP['create']], factory_id=target_factory_id)

    return False, '当前接口暂不支持该角色范围'


@role_ns.route('')
class RoleList(Resource):
    @login_required
    @permission_required_any(ROLE_QUERY_PERMISSION_CODES)
    @role_ns.expect(role_query_parser)
    @role_ns.response(200, '查询成功', role_list_response)
    @role_ns.response(401, '未登录', unauthorized_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """角色分页列表接口，支持按范围、状态和名称筛选。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args, error = normalize_role_filters(current_user, current_factory_id, role_query_parser.parse_args())
        if error:
            return ApiResponse.error(error, 403)

        current_user, current_factory_id, error_response_data = get_role_request_context(
            query_factory_id=args.get('scope_id') if args.get('scope_type') in {ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT} else None,
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        result, error = RoleService.get_role_list(current_user, args, current_factory_id)
        if error:
            return ApiResponse.error(error, 403 if error == '无权限查看角色' else 400)

        items = [RoleService.serialize_role(role) for role in result['items']]
        return success_mapped_page(result, items)

    @login_required
    @permission_required_any(ROLE_CREATE_PERMISSION_CODES)
    @role_ns.expect(role_create_model)
    @role_ns.response(201, '创建成功', role_item_response)
    @role_ns.response(400, '参数错误', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(409, '角色编码或名称已存在', error_response)
    def post(self):
        """创建角色接口，支持平台角色、工厂角色和主体角色。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(role_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        if not current_user.is_internal_user:
            data['scope_type'] = ROLE_SCOPE_SUBJECT
            data['scope_id'] = current_factory_id

        has_permission, error = check_role_create_permission(
            current_user,
            data.get('scope_type'),
            data.get('scope_id'),
            current_factory_id=current_factory_id,
        )
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        role, error = RoleService.create_role(data)
        if error:
            return ApiResponse.error(error, 400 if 'scope_id' in error else 409)
        return ApiResponse.success(RoleService.serialize_role(role), '创建成功', 201)


@role_ns.route('/options')
class RoleOptions(Resource):
    @login_required
    @permission_required_any(ROLE_QUERY_PERMISSION_CODES)
    @role_ns.expect(role_option_query_parser)
    @role_ns.response(200, '查询成功', role_options_response)
    @role_ns.response(401, '未登录', unauthorized_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """角色下拉选项接口，供角色选择器直接使用。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args, error = normalize_role_filters(current_user, current_factory_id, role_option_query_parser.parse_args())
        if error:
            return ApiResponse.error(error, 403)

        current_user, current_factory_id, error_response_data = get_role_request_context(
            query_factory_id=args.get('scope_id') if args.get('scope_type') in {ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT} else None,
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        roles, error = RoleService.get_role_options(current_user, args, current_factory_id)
        if error:
            return ApiResponse.error(error, 403 if error == '无权限查看角色' else 400)

        return ApiResponse.success_list([serialize_role_option(role) for role in roles])


@role_ns.route('/<int:role_id>')
class RoleDetail(Resource):
    @login_required
    @permission_required_any(ROLE_QUERY_PERMISSION_CODES)
    @role_ns.expect(role_detail_query_parser)
    @role_ns.response(200, '查询成功', role_item_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """角色详情接口，返回范围、数据权限和基础配置信息。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args = role_detail_query_parser.parse_args()
        role, _, _, error_response_data = resolve_role_resource(
            role_id,
            current_user,
            current_factory_id,
            scope_type=args.get('scope_type'),
            scope_id=args.get('scope_id'),
        )
        if error_response_data:
            return error_response_data

        has_permission, error = check_role_scope_permission(current_user, role, 'query', current_factory_id=current_factory_id)
        permission_error = ensure_permission_or_error(has_permission, error or '无权限查看此角色', 403)
        if permission_error:
            return permission_error

        return ApiResponse.success(RoleService.serialize_role(role))

    @login_required
    @permission_required_any(ROLE_EDIT_PERMISSION_CODES)
    @role_ns.expect(role_detail_query_parser, role_update_model)
    @role_ns.response(200, '更新成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def patch(self, role_id):
        """更新角色接口，可修改名称、状态、排序和数据范围。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args = role_detail_query_parser.parse_args()
        role, _, _, error_response_data = resolve_role_resource(
            role_id,
            current_user,
            current_factory_id,
            scope_type=args.get('scope_type'),
            scope_id=args.get('scope_id'),
        )
        if error_response_data:
            return error_response_data

        has_permission, error = check_role_scope_permission(current_user, role, 'edit', current_factory_id=current_factory_id)
        permission_error = ensure_permission_or_error(has_permission, error or '无权限更新角色', 403)
        if permission_error:
            return permission_error

        data, validation_error = load_json_or_error(role_update_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        role, error = RoleService.update_role(role, data)
        if error:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(RoleService.serialize_role(role), '更新成功')

    @login_required
    @permission_required_any(ROLE_DELETE_PERMISSION_CODES)
    @role_ns.expect(role_detail_query_parser)
    @role_ns.response(200, '删除成功', base_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(409, '角色已被使用', error_response)
    def delete(self, role_id):
        """删除角色接口，删除前会校验是否仍被用户使用。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args = role_detail_query_parser.parse_args()
        role, _, _, error_response_data = resolve_role_resource(
            role_id,
            current_user,
            current_factory_id,
            scope_type=args.get('scope_type'),
            scope_id=args.get('scope_id'),
        )
        if error_response_data:
            return error_response_data

        has_permission, error = check_role_scope_permission(current_user, role, 'delete', current_factory_id=current_factory_id)
        permission_error = ensure_permission_or_error(has_permission, error or '无权限删除角色', 403)
        if permission_error:
            return permission_error

        success, error = RoleService.delete_role(role)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')


@role_ns.route('/<int:role_id>/menus')
class RoleMenus(Resource):
    @login_required
    @permission_required_any(ROLE_QUERY_PERMISSION_CODES)
    @role_ns.expect(role_detail_query_parser)
    @role_ns.response(200, '查询成功', menu_ids_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """角色菜单权限查询接口，返回当前角色已绑定的菜单 ID 集合。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args = role_detail_query_parser.parse_args()
        role, _, _, error_response_data = resolve_role_resource(
            role_id,
            current_user,
            current_factory_id,
            scope_type=args.get('scope_type'),
            scope_id=args.get('scope_id'),
        )
        if error_response_data:
            return error_response_data

        has_permission, error = check_role_scope_permission(current_user, role, 'query', current_factory_id=current_factory_id)
        permission_error = ensure_permission_or_error(has_permission, error or '无权限查看角色菜单', 403)
        if permission_error:
            return permission_error

        return ApiResponse.success_list(RoleService.get_role_menu_ids(role))

    @login_required
    @permission_required_any(ROLE_EDIT_PERMISSION_CODES)
    @role_ns.expect(role_detail_query_parser, role_assign_menu_model)
    @role_ns.response(200, '分配成功', base_response)
    @role_ns.response(404, '角色或菜单不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def post(self, role_id):
        """角色菜单权限分配接口，会重建当前角色的菜单绑定关系。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args = role_detail_query_parser.parse_args()
        role, _, _, error_response_data = resolve_role_resource(
            role_id,
            current_user,
            current_factory_id,
            scope_type=args.get('scope_type'),
            scope_id=args.get('scope_id'),
        )
        if error_response_data:
            return error_response_data

        has_permission, error = check_role_scope_permission(current_user, role, 'edit', current_factory_id=current_factory_id)
        permission_error = ensure_permission_or_error(has_permission, error or '无权限分配角色菜单', 403)
        if permission_error:
            return permission_error

        data, validation_error = load_json_or_error(role_assign_menu_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        success, error = RoleService.assign_role_menus(role.id, data['menu_ids'], current_user=current_user, role=role)
        if not success:
            return ApiResponse.error(error, 403 if '不允许' in error else 404)
        return ApiResponse.success(message='权限分配成功')


@role_ns.route('/<int:role_id>/users')
class RoleUsers(Resource):
    @login_required
    @permission_required_any(ROLE_QUERY_PERMISSION_CODES)
    @role_ns.expect(role_detail_query_parser)
    @role_ns.response(200, '查询成功', role_users_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """角色关联用户查询接口，返回当前角色下的用户列表。"""
        current_user, current_factory_id, error_response_data = get_role_request_context(
            allow_internal_without_factory=True,
        )
        if error_response_data:
            return error_response_data

        args = role_detail_query_parser.parse_args()
        role, _, _, error_response_data = resolve_role_resource(
            role_id,
            current_user,
            current_factory_id,
            scope_type=args.get('scope_type'),
            scope_id=args.get('scope_id'),
        )
        if error_response_data:
            return error_response_data

        has_permission, error = check_role_scope_permission(current_user, role, 'query', current_factory_id=current_factory_id)
        permission_error = ensure_permission_or_error(has_permission, error or '无权限查看角色关联用户', 403)
        if permission_error:
            return permission_error

        from app.models.auth.user import User

        user_ids = RoleService.get_role_users(role)
        users = User.query.filter(User.id.in_(user_ids), User.is_deleted == 0).all() if user_ids else []
        return ApiResponse.success_list([serialize_role_user(user) for user in users])
