"""用户管理接口。"""

import hashlib
from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_claims, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.extensions import bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.schemas.auth.user import UserCreateSchema, UserResetPasswordSchema, UserSchema, UserUpdateSchema
from app.schemas.system.role import RoleSchema
from app.services import UserService
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

user_create_model = user_ns.model('UserCreate', {
    'username': fields.String(required=True, description='用户名', example='testuser'),
    'password': fields.String(required=True, description='密码', example='123456'),
    'nickname': fields.String(description='昵称', example='测试用户'),
    'phone': fields.String(description='手机号', example='13800138000'),
    'platform_identity': fields.String(
        description='平台身份',
        example='external_user',
        choices=['platform_admin', 'platform_staff', 'external_user']
    ),
    'factory_id': fields.Integer(description='工厂ID')
})

user_update_model = user_ns.model('UserUpdate', {
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'status': fields.Integer(description='状态', example=1, choices=[0, 1])
})

user_reset_password_model = user_ns.model('ResetPassword', {
    'password': fields.String(required=True, description='新密码', example='123456')
})

user_assign_roles_model = user_ns.model('AssignRoles', {
    'role_ids': fields.List(fields.Integer, required=True, description='角色ID列表', example=[1, 2]),
    'factory_id': fields.Integer(description='工厂ID')
})

user_item_model = user_ns.model('UserItem', {
    'id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'phone': fields.String(),
    'avatar': fields.String(),
    'platform_identity': fields.String(),
    'platform_identity_label': fields.String(),
    'subject_type': fields.String(),
    'subject_type_label': fields.String(),
    'status': fields.Integer(),
    'invite_code': fields.String(),
    'invited_count': fields.Integer(),
    'is_paid': fields.Integer(),
    'create_time': fields.String(),
    'last_login_time': fields.String()
})

user_list_data = user_ns.model('UserListData', {
    'items': fields.List(fields.Nested(user_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

user_list_response = user_ns.clone('UserListResponse', base_response, {
    'data': fields.Nested(user_list_data)
})

user_item_response = user_ns.clone('UserItemResponse', base_response, {
    'data': fields.Nested(user_item_model)
})

user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_reset_password_schema = UserResetPasswordSchema()
role_schema = RoleSchema(many=True)


def get_owner_relation(current_user):
    """获取当前用户作为工厂 owner 的有效绑定关系。"""
    return UserFactory.query.filter_by(
        user_id=current_user.id,
        relation_type='owner',
        status=1,
        is_deleted=0
    ).first()


def check_user_permission(current_user, target_user):
    """校验当前用户是否可以读取目标用户数据。"""
    if current_user.is_internal_user:
        return True, None

    owner_relation = get_owner_relation(current_user)
    if not owner_relation:
        if target_user.id == current_user.id:
            return True, None
        return False, '无权限操作'

    target_factory = UserFactory.query.filter_by(
        user_id=target_user.id,
        factory_id=owner_relation.factory_id,
        status=1,
        is_deleted=0
    ).first()
    if not target_factory and target_user.id != current_user.id:
        return False, '只能操作自己工厂的用户'
    return True, None


def check_user_write_permission(current_user, target_user):
    """校验当前用户是否可以写入目标用户数据。"""
    if current_user.is_platform_admin:
        return True, None
    if current_user.is_internal_user:
        return False, '平台员工仅支持查看用户数据'
    return check_user_permission(current_user, target_user)


@user_ns.route('')
class UserList(Resource):
    @login_required
    @user_ns.expect(user_query_parser)
    @user_ns.response(200, '成功', user_list_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """按权限范围分页查询用户列表。"""
        args = user_query_parser.parse_args()
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        result = UserService.get_user_list(current_user, args)
        return ApiResponse.success({
            'items': users_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @user_ns.expect(user_create_model)
    @user_ns.response(201, '创建成功', user_item_response)
    @user_ns.response(400, '参数错误', error_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(409, '用户名已存在', error_response)
    def post(self):
        """创建用户账号；工厂 owner 创建时会自动挂到自己的工厂。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = user_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        factory_id = data.get('factory_id')
        platform_identity = data.get('platform_identity') or 'external_user'

        if current_user.is_platform_admin:
            pass
        else:
            owner_relation = get_owner_relation(current_user)
            if not owner_relation:
                return ApiResponse.error('无权限创建用户', 403)
            factory_id = owner_relation.factory_id
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
            created_by=current_user.id
        )
        user.save()

        if factory_id and not user.is_internal_user:
            user_factory = UserFactory(
                user_id=user.id,
                factory_id=factory_id,
                relation_type='employee',
                status=1,
                entry_date=datetime.now().date(),
                remark=f'由 {current_user.username} 创建'
            )
            user_factory.save()

        return ApiResponse.success(user_schema.dump(user), '创建成功', 201)


@user_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @login_required
    @user_ns.response(200, '成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        """查看单个用户详情。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(user_schema.dump(target_user))

    @login_required
    @user_ns.expect(user_update_model)
    @user_ns.response(200, '更新成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def patch(self, user_id):
        """更新用户昵称、手机号和状态。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

        has_permission, error = check_user_write_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = user_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        target_user = UserService.update_user(target_user, data)
        return ApiResponse.success(user_schema.dump(target_user), '更新成功')

    @login_required
    @user_ns.response(200, '删除成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    @user_ns.response(403, '不能删除自己', forbidden_response)
    def delete(self, user_id):
        """删除用户，当前登录用户不允许删除自己。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

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
    @user_ns.response(404, '用户不存在', error_response)
    def post(self, user_id):
        """重置指定用户密码。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

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
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        """查询用户在当前工厂上下文下的角色集合。"""
        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在')

        claims = get_current_claims()
        factory_id = claims.get('factory_id')
        if user.is_internal_user and factory_id is None:
            factory_id = 0
        if factory_id is None:
            return ApiResponse.error('请指定工厂', 400)

        roles = UserService.get_user_roles(user_id, factory_id)
        return ApiResponse.success(role_schema.dump(roles))

    @login_required
    @user_ns.expect(user_assign_roles_model)
    @user_ns.response(200, '分配成功', base_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def post(self, user_id):
        """给用户重新分配角色，会替换当前上下文下的旧角色。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在', 404)

        has_permission, error = check_user_write_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        data = request.get_json() or {}
        role_ids = data.get('role_ids', [])
        factory_id = data.get('factory_id')

        if factory_id is None and not current_user.is_internal_user:
            owner_relation = get_owner_relation(current_user)
            if owner_relation:
                factory_id = owner_relation.factory_id

        if factory_id is None and not target_user.is_internal_user:
            return ApiResponse.error('请指定工厂ID', 400)

        success, error = UserService.assign_roles(user_id, role_ids, factory_id, current_user)
        if not success:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(message='角色分配成功')


@user_ns.route('/permissions')
class UserPermissions(Resource):
    @login_required
    @user_ns.response(200, '成功', base_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回当前登录用户最终拥有的权限编码列表。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        permissions = UserService.get_user_permissions(current_user.id)
        return ApiResponse.success(permissions)


@user_ns.route('/test')
class Test(Resource):
    def get(self):
        """联调使用的最小测试接口。"""
        return {'message': 'test ok'}
