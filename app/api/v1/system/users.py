"""用户管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import get_jwt_identity
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserSchema, UserCreateSchema, UserUpdateSchema, UserResetPasswordSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required, permission_required
from app.services import UserService

user_ns = Namespace('users', description='用户管理')

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
    @user_ns.response(409, '用户名已存在', error_response)
    def post(self):
        """创建用户"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以创建用户
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限创建用户', 403)

        try:
            data = user_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        user, error = UserService.create_user(data, current_user.id)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(user_schema.dump(user), '创建成功', 201)


@user_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @login_required
    @user_ns.response(200, '成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        """获取用户详情"""
        current_user = get_current_user()

        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在')

        # 权限验证
        if current_user.is_admin != 1 and current_user.id != user.id:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(user_schema.dump(user))

    @login_required
    @user_ns.expect(user_update_model)
    @user_ns.response(200, '更新成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def put(self, user_id):
        """更新用户信息"""
        current_user = get_current_user()

        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在')

        # 权限验证
        if current_user.is_admin != 1 and current_user.id != user.id:
            return ApiResponse.error('无权限修改', 403)

        try:
            data = user_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        user = UserService.update_user(user, data)

        return ApiResponse.success(user_schema.dump(user), '更新成功')

    @login_required
    @user_ns.response(200, '删除成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    @user_ns.response(403, '不能删除自己', forbidden_response)
    def delete(self, user_id):
        """删除用户"""
        current_user = get_current_user()

        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以删除用户
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限删除', 403)

        if user.id == current_user.id:
            return ApiResponse.error('不能删除当前登录用户', 403)

        UserService.delete_user(user)
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

        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以重置密码
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限重置密码', 403)

        try:
            data = user_reset_password_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        UserService.reset_password(user, data['password'])

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
    def put(self, user_id):
        """分配角色"""
        current_user = get_current_user()

        # 只有公司内部人员可以分配角色
        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以分配角色', 403)

        user = UserService.get_user_by_id(user_id)
        if not user:
            return ApiResponse.error('用户不存在', 404)

        data = request.get_json()
        role_ids = data.get('role_ids', [])
        factory_id = data.get('factory_id')

        if not factory_id and user.is_admin != 1:
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

        # 获取用户权限（需要在 UserService 中实现 get_user_permissions 方法）
        permissions = UserService.get_user_permissions(current_user.id)

        return ApiResponse.success(permissions)


@user_ns.route('/test')
class Test(Resource):
    def get(self):
        return {'message': 'test ok'}
