"""用户管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import get_jwt_identity
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserSchema, UserCreateSchema, UserUpdateSchema, UserResetPasswordSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import UserService

user_ns = Namespace('用户管理-users', description='用户管理')

shared = get_shared_models(user_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

# ========== 请求解析器 ==========
user_query_parser = user_ns.parser()
user_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
user_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
user_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
user_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
user_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID')

# ========== 请求模型 ==========
user_create_model = user_ns.model('UserCreate', {
    'username': fields.String(required=True, description='用户名', example='testuser'),
    'password': fields.String(required=True, description='密码', example='123456'),
    'nickname': fields.String(description='昵称', example='测试用户'),
    'phone': fields.String(description='手机号', example='13800138000'),
    'is_admin': fields.Integer(description='是否内部人员', example=0, choices=[0, 1]),
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

# ========== 响应模型 ==========
user_item_model = user_ns.model('UserItem', {
    'id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'phone': fields.String(),
    'avatar': fields.String(),
    'is_admin': fields.Integer(),
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

# ========== Schema 初始化 ==========
user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_reset_password_schema = UserResetPasswordSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    identity = get_jwt_identity()
    current_user_id = UserService.get_current_user_id_from_identity(identity)
    return UserService.get_user_by_id(current_user_id)


def check_user_permission(current_user, target_user):
    """
    检查当前用户是否有权限操作目标用户
    返回: (has_permission, error_message)
    """
    # 平台管理员：所有权限
    if current_user.is_admin == 1:
        return True, None

    # 获取当前用户的工厂（owner 类型）
    from app.models.system.user_factory import UserFactory
    user_factory = UserFactory.query.filter_by(
        user_id=current_user.id,
        relation_type='owner',
        status=1,
        is_deleted=0
    ).first()

    if not user_factory:
        return False, '无权限操作'

    factory_id = user_factory.factory_id

    # 检查目标用户是否属于同一工厂
    target_factory = UserFactory.query.filter_by(
        user_id=target_user.id,
        factory_id=factory_id,
        status=1,
        is_deleted=0
    ).first()

    # 允许操作自己的用户，或者同一工厂的用户
    if not target_factory and target_user.id != current_user.id:
        return False, '只能操作自己工厂的用户'

    return True, None


# ========== 接口 ==========
@user_ns.route('')
class UserList(Resource):
    @login_required
    @user_ns.expect(user_query_parser)
    @user_ns.response(200, '成功', user_list_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """获取用户列表"""
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
        """创建用户（平台管理员或工厂管理员）"""
        from app.models.auth.user import User
        from app.models.system.factory import Factory
        from app.models.system.user_factory import UserFactory
        from app.extensions import bcrypt
        import hashlib
        from datetime import datetime

        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = user_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        # 权限判断和工厂ID处理
        factory_id = data.get('factory_id')
        is_admin = data.get('is_admin', 0)

        if current_user.is_admin == 1:
            # 平台管理员：可以创建任何用户
            # 平台用户（is_admin=1）不关联工厂
            # 普通用户（is_admin=0）也不关联工厂（除非有特殊需求）
            pass
        else:
            # 工厂管理员：只能创建普通用户，且必须关联自己工厂
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id,
                relation_type='owner',
                status=1,
                is_deleted=0
            ).first()

            if not user_factory:
                return ApiResponse.error('无权限创建用户', 403)

            factory_id = user_factory.factory_id
            is_admin = 0  # 工厂管理员不能创建平台用户

        # 检查用户名
        existing_user = UserService.get_user_by_username(data['username'])
        if existing_user:
            return ApiResponse.error('用户名已存在', 409)

        # 验证工厂存在（如果有工厂ID）
        if factory_id:
            factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
            if not factory:
                return ApiResponse.error('工厂不存在', 400)

        # ========== 生成邀请码（所有用户都生成） ==========
        invite_code = hashlib.md5(f"{data['username']}{datetime.now()}".encode()).hexdigest()[:8].upper()
        while User.query.filter_by(invite_code=invite_code).first():
            invite_code = hashlib.md5(f"{data['username']}{datetime.now()}".encode()).hexdigest()[:8].upper()

        # 创建用户
        user = User(
            username=data['username'],
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            nickname=data.get('nickname', ''),
            phone=data.get('phone', ''),
            is_admin=is_admin,
            status=1,
            invite_code=invite_code,
            invited_by=None,
            invited_count=0,
            created_by=current_user.id
        )
        user.save()

        # ========== 工厂关联（仅在工厂管理员创建时，或有指定工厂时） ==========
        # 只有工厂管理员创建的用户才自动关联工厂
        if current_user.is_admin != 1 and factory_id:
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
        """获取用户详情"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

        # 统一权限验证
        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(user_schema.dump(target_user))

    @login_required
    @user_ns.expect(user_update_model)
    @user_ns.response(200, '更新成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def patch(self, user_id):
        """更新用户信息"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

        # 统一权限验证
        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = user_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        target_user = UserService.update_user(target_user, data)

        return ApiResponse.success(user_schema.dump(target_user), '更新成功')

    @login_required
    @user_ns.response(200, '删除成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    @user_ns.response(403, '不能删除自己', forbidden_response)
    def delete(self, user_id):
        """删除用户"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

        # 统一权限验证
        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        # 不能删除自己
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
        """重置密码"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在')

        # 统一权限验证
        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = user_reset_password_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        UserService.reset_password(target_user, data['password'])

        return ApiResponse.success(message='密码重置成功')


@user_ns.route('/<int:user_id>/roles')
class UserRoles(Resource):
    @login_required
    @user_ns.response(200, '成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        """获取用户角色"""
        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在')

        identity = get_jwt_identity()
        factory_id = identity.get('factory_id') if isinstance(identity, dict) else None

        if not factory_id:
            return ApiResponse.error('请指定工厂', 400)

        roles = UserService.get_user_roles(user_id, factory_id)

        from app.schemas.system.role import RoleSchema
        role_schema = RoleSchema()

        return ApiResponse.success(role_schema.dump(roles, many=True))

    @login_required
    @user_ns.expect(user_assign_roles_model)
    @user_ns.response(200, '分配成功', base_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def post(self, user_id):
        """分配角色"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return ApiResponse.error('用户不存在', 404)

        # 统一权限验证
        has_permission, error = check_user_permission(current_user, target_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        data = request.get_json()
        role_ids = data.get('role_ids', [])
        factory_id = data.get('factory_id')

        # 如果是工厂管理员，从验证中获取 factory_id
        if not factory_id and current_user.is_admin != 1:
            from app.models.system.user_factory import UserFactory
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id,
                relation_type='owner',
                status=1,
                is_deleted=0
            ).first()
            if user_factory:
                factory_id = user_factory.factory_id

        if not factory_id and target_user.is_admin != 1:
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
        """获取当前用户的权限列表"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        permissions = UserService.get_user_permissions(current_user.id)

        return ApiResponse.success(permissions)


@user_ns.route('/test')
class Test(Resource):
    def get(self):
        return {'message': 'test ok'}
