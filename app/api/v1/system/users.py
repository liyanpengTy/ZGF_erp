"""用户管理接口。"""

import hashlib
from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_claims, get_current_factory_id, require_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.extensions import bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.schemas.auth.user import UserCreateSchema, UserResetPasswordSchema, UserUpdateSchema
from app.schemas.system.role import RoleSchema
from app.services import RoleService, UserService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

user_ns = Namespace('用户管理-users', description='用户管理')

common = get_common_models(user_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']

user_query_parser = page_parser.copy()
user_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
user_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
user_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID')
user_query_parser.add_argument(
    'relation_type',
    type=str,
    location='args',
    help='工厂关系类型',
    choices=['owner', 'employee', 'customer', 'collaborator'],
)
user_query_parser.add_argument(
    'platform_identity',
    type=str,
    location='args',
    help='平台身份',
    choices=['platform_admin', 'platform_staff', 'external_user'],
)

user_option_query_parser = new_query_parser()
user_option_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
user_option_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
user_option_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID')
user_option_query_parser.add_argument(
    'relation_type',
    type=str,
    location='args',
    help='工厂关系类型',
    choices=['owner', 'employee', 'customer', 'collaborator'],
)
user_option_query_parser.add_argument(
    'platform_identity',
    type=str,
    location='args',
    help='平台身份',
    choices=['platform_admin', 'platform_staff', 'external_user'],
)

user_create_model = user_ns.model('UserCreate', {
    'username': fields.String(required=True, description='用户名', example='testuser'),
    'password': fields.String(required=True, description='密码', example='123456'),
    'nickname': fields.String(description='昵称', example='测试用户'),
    'phone': fields.String(description='手机号', example='13800138000'),
    'platform_identity': fields.String(
        description='平台身份，可选 platform_admin(平台管理员)、platform_staff(平台员工)、external_user(外部人员)。非平台管理员调用时后端会强制写为 external_user。',
        example='external_user',
        choices=['platform_admin', 'platform_staff', 'external_user'],
    ),
    'factory_id': fields.Integer(description='工厂ID；创建外部用户时可同时挂靠到指定工厂', example=1),
})

user_update_model = user_ns.model('UserUpdate', {
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'status': fields.Integer(description='状态', example=1, choices=[0, 1]),
})

user_reset_password_model = user_ns.model('ResetPassword', {
    'password': fields.String(required=True, description='新密码', example='123456'),
})

user_assign_roles_model = user_ns.model('AssignRoles', {
    'role_ids': fields.List(fields.Integer, required=True, description='角色ID列表', example=[1, 2]),
    'factory_id': fields.Integer(description='角色分配上下文：平台角色传 0 或不传，工厂角色传工厂ID'),
})

user_factory_relation_model = user_ns.model('UserFactoryRelation', {
    'factory_id': fields.Integer(description='工厂ID', example=1),
    'factory_name': fields.String(description='工厂名称', example='测试工厂'),
    'factory_code': fields.String(description='工厂编码', example='TEST001'),
    'relation_type': fields.String(description='关联关系类型', example='employee'),
    'relation_type_label': fields.String(description='关联关系名称', example='工厂员工'),
    'collaborator_type': fields.String(description='协作细分类型', example=None),
    'collaborator_type_label': fields.String(description='协作细分类型名称', example=None),
    'entry_date': fields.String(description='入厂日期', example='2026-05-01'),
    'leave_date': fields.String(description='离厂日期', example=None),
})

user_role_binding_model = user_ns.model('UserRoleBinding', {
    'role_id': fields.Integer(description='角色ID', example=1),
    'role_name': fields.String(description='角色名称', example='工厂管理员'),
    'role_code': fields.String(description='角色编码', example='factory_admin'),
    'scope_type': fields.String(description='角色归属范围', example='factory'),
    'scope_type_label': fields.String(description='角色归属范围名称', example='工厂角色'),
    'scope_id': fields.Integer(description='角色归属主键', example=1),
    'factory_id': fields.Integer(description='角色分配上下文工厂ID；平台角色固定为 0', example=1),
    'is_factory_admin': fields.Integer(description='是否工厂管理员角色', example=1),
})

user_item_model = user_ns.model('UserItem', {
    'id': fields.Integer(description='用户ID', example=2),
    'username': fields.String(description='用户名', example='factory_admin'),
    'nickname': fields.String(description='昵称', example='工厂管理员'),
    'phone': fields.String(description='手机号', example='18370601281'),
    'avatar': fields.String(description='头像地址', example=None),
    'platform_identity': fields.String(description='平台身份', example='external_user'),
    'platform_identity_label': fields.String(description='平台身份名称', example='外部人员'),
    'subject_type': fields.String(description='主体类型', example='factory_subject'),
    'subject_type_label': fields.String(description='主体类型名称', example='工厂主体'),
    'status': fields.Integer(description='状态', example=1),
    'invite_code': fields.String(description='邀请码', example='ABC12346'),
    'invited_count': fields.Integer(description='邀请人数', example=0),
    'is_paid': fields.Integer(description='是否已付费', example=1),
    'created_by': fields.Integer(description='创建人ID', example=1),
    'create_time': fields.String(description='创建时间', example='2026-04-21 01:17:24'),
    'last_login_time': fields.String(description='最后登录时间', example='2026-05-15 12:35:13'),
    'factory_id': fields.Integer(description='主工厂ID；多工厂时取第一条有效挂靠关系', example=1),
    'factory_name': fields.String(description='主工厂名称；多工厂时取第一条有效挂靠关系', example='测试工厂'),
    'factory_ids': fields.List(fields.Integer, description='用户当前绑定的全部工厂ID列表', example=[1, 2]),
    'factory_relations': fields.List(fields.Nested(user_factory_relation_model), description='用户工厂挂靠关系列表'),
    'role_ids': fields.List(fields.Integer, description='用户当前绑定的全部角色ID列表', example=[1, 2]),
    'role_bindings': fields.List(fields.Nested(user_role_binding_model), description='用户角色绑定列表'),
})

user_option_model = user_ns.model('UserOptionItem', {
    'id': fields.Integer(description='用户ID', example=2),
    'username': fields.String(description='用户名', example='factory_employee'),
    'nickname': fields.String(description='昵称', example='工厂员工'),
    'phone': fields.String(description='手机号', example='18370601281'),
    'platform_identity': fields.String(description='平台身份', example='external_user'),
    'platform_identity_label': fields.String(description='平台身份名称', example='外部人员'),
})

user_list_data = user_ns.model('SystemUserListData', {
    'items': fields.List(fields.Nested(user_item_model), description='用户列表'),
    'total': fields.Integer(description='总条数'),
    'page': fields.Integer(description='当前页码'),
    'page_size': fields.Integer(description='每页条数'),
    'pages': fields.Integer(description='总页数'),
})

user_list_response = user_ns.clone('SystemUserListResponse', base_response, {
    'data': fields.Nested(user_list_data, description='用户分页数据'),
})

user_item_response = user_ns.clone('SystemUserItemResponse', base_response, {
    'data': fields.Nested(user_item_model, description='用户详情数据'),
})

user_options_response = user_ns.clone('SystemUserOptionsResponse', base_response, {
    'data': fields.List(fields.Nested(user_option_model), description='用户下拉选项列表'),
})

permission_summary_model = user_ns.model('UserPermissionSummary', {
    'current_factory_id': fields.Integer(description='当前 JWT 上下文中的工厂ID；平台账号通常为空', example=1),
    'current_permissions': fields.List(fields.String, description='当前上下文下生效的权限并集', example=['business.orders.browse']),
    'all_permissions': fields.List(fields.String, description='当前账号绑定的全部角色权限并集', example=['business.orders.browse', 'business.orders.create']),
    'role_bindings': fields.List(fields.Nested(user_role_binding_model), description='当前账号绑定的角色列表'),
})

permission_summary_response = user_ns.clone('UserPermissionSummaryResponse', base_response, {
    'data': fields.Nested(permission_summary_model, description='权限汇总数据'),
})

user_test_response = user_ns.model('UserTestResponse', {
    'message': fields.String(description='测试结果'),
})

user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_reset_password_schema = UserResetPasswordSchema()
role_schema = RoleSchema(many=True)


def get_required_current_user():
    """获取当前登录用户，不存在时返回统一错误响应。"""
    return require_current_user()


def get_target_user_or_error(user_id):
    """根据用户 ID 查询目标用户，不存在时返回统一错误响应。"""
    target_user = UserService.get_user_by_id(user_id)
    if not target_user:
        return None, ApiResponse.error('用户不存在')
    return target_user, None


def get_active_factory_ids(user):
    """查询用户当前有效挂靠的工厂 ID 列表。"""
    if not user:
        return []
    factory_records = UserFactory.query.filter_by(user_id=user.id, status=1, is_deleted=0).all()
    return [record.factory_id for record in factory_records]


def is_target_user_in_factory(target_user, factory_id):
    """判断目标用户是否属于指定工厂。"""
    if not target_user or not factory_id:
        return False
    return UserFactory.query.filter_by(
        user_id=target_user.id,
        factory_id=factory_id,
        status=1,
        is_deleted=0,
    ).first() is not None


def resolve_manage_factory_id(current_user, requested_factory_id=None):
    """解析当前用户可管理的工厂ID。"""
    if not current_user:
        return None, '用户不存在'
    if current_user.is_platform_admin:
        return requested_factory_id, None
    if current_user.is_internal_user:
        return None, '平台员工仅支持查看用户数据'

    candidate_factory_id = requested_factory_id or get_current_factory_id()
    if candidate_factory_id and RoleService.has_factory_admin_permission(current_user, candidate_factory_id):
        return candidate_factory_id, None

    for factory_id in get_active_factory_ids(current_user):
        if RoleService.has_factory_admin_permission(current_user, factory_id):
            return factory_id, None

    return None, '只有工厂管理员可以维护本工厂用户'


def check_user_permission(current_user, target_user):
    """校验当前用户是否可以读取目标用户数据。"""
    if current_user.is_internal_user:
        return True, None
    if target_user.id == current_user.id:
        return True, None

    for factory_id in get_active_factory_ids(current_user):
        if RoleService.has_factory_admin_permission(current_user, factory_id) and is_target_user_in_factory(target_user, factory_id):
            return True, None
    return False, '无权限操作'


def check_user_write_permission(current_user, target_user):
    """校验当前用户是否可以写入目标用户数据。"""
    if current_user.is_platform_admin:
        return True, None
    if current_user.is_internal_user:
        return False, '平台员工仅支持查看用户数据'
    if target_user.id == current_user.id:
        return True, None
    return check_user_permission(current_user, target_user)


@user_ns.route('')
class UserList(Resource):
    @login_required
    @user_ns.expect(user_query_parser)
    @user_ns.response(200, '成功', user_list_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    @user_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """按权限范围分页查询用户列表，返回工厂挂靠关系和角色绑定信息。"""
        args = user_query_parser.parse_args()
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        if not current_user.is_internal_user and not args.get('factory_id'):
            args['factory_id'] = get_current_factory_id()

        result = UserService.get_user_list(current_user, args)
        return ApiResponse.success_page_result(result, result['items'])

    @login_required
    @user_ns.expect(user_create_model)
    @user_ns.response(201, '创建成功', user_item_response)
    @user_ns.response(400, '参数错误', error_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(409, '用户名已存在', error_response)
    def post(self):
        """创建用户账号；必要时同时挂靠到工厂，并返回完整用户视图。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        try:
            data = user_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        factory_id = data.get('factory_id')
        platform_identity = data.get('platform_identity') or 'external_user'

        if not current_user.is_platform_admin:
            factory_id, error = resolve_manage_factory_id(current_user, factory_id)
            if error:
                return ApiResponse.error(error, 403)
            platform_identity = 'external_user'

        existing_user = UserService.get_user_by_username(data['username'])
        if existing_user:
            return ApiResponse.error('用户名已存在', 409)

        if factory_id:
            factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
            if not factory:
                return ApiResponse.error('工厂不存在', 400)

        invite_code = hashlib.md5(f"{data['username']}{datetime.now()}".encode()).hexdigest()[:8].upper()
        while User.query.filter_by(invite_code=invite_code).first():
            invite_code = hashlib.md5(f"{data['username']}{datetime.now()}".encode()).hexdigest()[:8].upper()

        user = User(
            username=data['username'],
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            nickname=data.get('nickname', ''),
            phone=data.get('phone', ''),
            platform_identity=platform_identity,
            status=1,
            invite_code=invite_code,
            invited_by=None,
            invited_count=0,
            created_by=current_user.id,
        )
        user.save()

        if factory_id and not user.is_internal_user:
            user_factory = UserFactory(
                user_id=user.id,
                factory_id=factory_id,
                relation_type='employee',
                status=1,
                entry_date=datetime.now().date(),
                remark=f'由 {current_user.username} 创建',
            )
            user_factory.save()

        return ApiResponse.success(UserService.build_user_view(user), '创建成功', 201)


@user_ns.route('/options')
class UserOptions(Resource):
    @login_required
    @user_ns.expect(user_option_query_parser)
    @user_ns.response(200, '成功', user_options_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    @user_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询轻量用户选项列表，供客户、员工、协作用户等选择器直接使用。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        args = user_option_query_parser.parse_args()
        if not current_user.is_internal_user and not args.get('factory_id'):
            args['factory_id'] = get_current_factory_id()

        return ApiResponse.success_list(UserService.get_user_options(current_user, args))


@user_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @login_required
    @user_ns.response(200, '成功', user_item_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        """查看单个用户详情，返回工厂挂靠关系和角色绑定信息。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        target_user, error_response_data = get_target_user_or_error(user_id)
        if error_response_data:
            return error_response_data

        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(UserService.build_user_view(target_user))

    @login_required
    @user_ns.expect(user_update_model)
    @user_ns.response(200, '更新成功', user_item_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def patch(self, user_id):
        """更新用户昵称、手机号和状态，并返回完整用户视图。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        target_user, error_response_data = get_target_user_or_error(user_id)
        if error_response_data:
            return error_response_data

        has_permission, error = check_user_write_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = user_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        target_user = UserService.update_user(target_user, data)
        return ApiResponse.success(UserService.build_user_view(target_user), '更新成功')

    @login_required
    @user_ns.response(200, '删除成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    @user_ns.response(403, '不能删除自己', forbidden_response)
    def delete(self, user_id):
        """删除用户；当前登录用户不允许删除自己。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        target_user, error_response_data = get_target_user_or_error(user_id)
        if error_response_data:
            return error_response_data

        has_permission, error = check_user_write_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        if target_user.id == current_user.id:
            return ApiResponse.error('不能删除当前登录用户', 403)

        UserService.delete_user(target_user)
        return ApiResponse.success(message='删除成功')


@user_ns.route('/<int:user_id>/reset-password')
class UserResetPassword(Resource):
    @login_required
    @user_ns.expect(user_reset_password_model)
    @user_ns.response(200, '重置成功', base_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def post(self, user_id):
        """重置指定用户密码接口。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        target_user, error_response_data = get_target_user_or_error(user_id)
        if error_response_data:
            return error_response_data

        has_permission, error = check_user_write_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = user_reset_password_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        UserService.reset_password(target_user, data['password'])
        return ApiResponse.success(message='密码重置成功')


@user_ns.route('/<int:user_id>/roles')
class UserRoles(Resource):
    @login_required
    @user_ns.response(200, '成功', base_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        """查询用户角色集合接口，返回当前工厂上下文下的角色列表。"""
        user, error_response_data = get_target_user_or_error(user_id)
        if error_response_data:
            return error_response_data

        claims = get_current_claims()
        factory_id = claims.get('factory_id')
        if user.is_internal_user and factory_id is None:
            factory_id = 0
        if factory_id is None:
            return ApiResponse.error('请指定工厂', 400)

        roles = UserService.get_user_roles(user_id, factory_id)
        return ApiResponse.success_list(role_schema.dump(roles))

    @login_required
    @user_ns.expect(user_assign_roles_model)
    @user_ns.response(200, '分配成功', base_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def post(self, user_id):
        """给用户重新分配角色，会替换当前上下文下的旧角色。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        target_user, error_response_data = get_target_user_or_error(user_id)
        if error_response_data:
            return error_response_data

        data = request.get_json() or {}
        role_ids = data.get('role_ids', [])
        factory_id = data.get('factory_id')

        if factory_id is None and not current_user.is_internal_user:
            factory_id, error = resolve_manage_factory_id(current_user)
            if error:
                return ApiResponse.error(error, 403)

        if factory_id is None and not target_user.is_internal_user:
            return ApiResponse.error('请指定工厂ID', 400)

        if not current_user.is_platform_admin:
            if not RoleService.has_factory_admin_permission(current_user, factory_id):
                return ApiResponse.error('只有平台管理员或本工厂管理员可以分配角色', 403)
            if not is_target_user_in_factory(target_user, factory_id):
                return ApiResponse.error('只能给本工厂用户分配角色', 403)

        success, error = UserService.assign_roles(user_id, role_ids, factory_id, current_user)
        if not success:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(message='角色分配成功')


@user_ns.route('/permissions')
class UserPermissions(Resource):
    @login_required
    @user_ns.response(200, '成功', permission_summary_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    @user_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """返回当前账号绑定角色的权限并集，以及当前上下文权限。"""
        current_user, error_response_data = get_required_current_user()
        if error_response_data:
            return error_response_data

        return ApiResponse.success(UserService.get_permission_summary(current_user.id))


@user_ns.route('/test')
class Test(Resource):
    @user_ns.response(200, '成功', user_test_response)
    def get(self):
        """联调使用的最小测试接口。"""
        return {'message': 'test ok'}
