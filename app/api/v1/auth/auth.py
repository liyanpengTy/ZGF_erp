"""认证接口 - 接口层（只负责路由和参数解析）"""
from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import get_jwt, create_access_token, get_jwt_identity
from app.services import AuthService, LoginResponseBuilder
from app.utils.permissions import login_required, refresh_required
from app.utils.response import ApiResponse
from app.api.v1.shared_models import get_shared_models

auth_ns = Namespace('auth', description='认证管理')

# ========== 共享模型 ==========
shared = get_shared_models(auth_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

# ========== 请求模型 ==========
login_request_model = auth_ns.model('LoginRequest', {
    'username': fields.String(required=True, description='用户名', example='admin'),
    'password': fields.String(required=True, description='密码', example='123456')
})

switch_factory_model = auth_ns.model('SwitchFactoryRequest', {
    'factory_id': fields.Integer(required=True, description='工厂ID')
})

# ========== 响应模型 ==========
user_info_model = auth_ns.model('UserInfo', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'avatar': fields.String(description='头像'),
    'is_admin': fields.Integer(description='是否管理员'),
    'status': fields.Integer(description='状态'),
    'create_time': fields.String(description='创建时间'),
    'last_login_time': fields.String(description='最后登录时间')
})

factory_info_model = auth_ns.model('FactoryInfo', {
    'id': fields.Integer(description='工厂ID'),
    'name': fields.String(description='工厂名称'),
    'code': fields.String(description='工厂编码'),
    'relation_type': fields.String(description='关系类型')
})

login_response_data = auth_ns.model('LoginResponseData', {
    'access_token': fields.String(description='访问令牌'),
    'refresh_token': fields.String(description='刷新令牌'),
    'user_info': fields.Nested(user_info_model, description='用户信息'),
    'factories': fields.List(fields.Nested(factory_info_model), description='关联工厂列表'),
    'current_factory': fields.Nested(factory_info_model, description='当前工厂', allow_null=True)
})

refresh_response_data = auth_ns.model('RefreshResponseData', {
    'access_token': fields.String(description='新的访问令牌')
})

login_response = auth_ns.clone('LoginResponse', base_response, {
    'data': fields.Nested(login_response_data)
})

refresh_response = auth_ns.clone('RefreshResponse', base_response, {
    'data': fields.Nested(refresh_response_data)
})

user_info_response = auth_ns.clone('UserInfoResponse', base_response, {
    'data': fields.Nested(user_info_model)
})


# ========== 接口 ==========
@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_request_model)
    @auth_ns.response(200, '登录成功', login_response)
    @auth_ns.response(400, '用户名或密码错误', error_response)
    @auth_ns.response(401, '账号已被禁用', unauthorized_response)
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # 用户认证
        user, error = AuthService.authenticate(username, password)
        if error:
            return ApiResponse.error(error)

        # 获取用户关联的工厂
        factories = AuthService.get_user_factories(user.id)

        # 公司内部人员
        if user.is_admin == 1:
            access_token, refresh_token = AuthService.create_tokens(user)
            return LoginResponseBuilder.build_admin(user, access_token, refresh_token)

        # 无工厂的员工
        if not factories:
            access_token, refresh_token = AuthService.create_tokens(user)
            return LoginResponseBuilder.build_employee(user, access_token, refresh_token, [], None)

        # 有工厂的员工（默认使用第一个工厂）
        current_factory = factories[0]
        access_token, refresh_token = AuthService.create_tokens(
            user,
            factory_id=current_factory['id'],
            relation_type=current_factory['relation_type']
        )

        return LoginResponseBuilder.build_employee(
            user, access_token, refresh_token, factories, current_factory
        )


@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @refresh_required  # 使用专门的装饰器
    @auth_ns.response(200, '刷新成功', refresh_response)
    @auth_ns.response(401, 'refresh_token无效或已过期', unauthorized_response)
    def post(self):
        old_claims = get_jwt()
        user_id = old_claims.get('user_id')

        if not user_id:
            identity = get_jwt_identity()
            if isinstance(identity, dict):
                user_id = identity.get('user_id')
            else:
                user_id = int(identity)

        # 构建新的 claims（保留原工厂信息）
        additional_claims = {'user_id': user_id}

        for key in ['factory_id', 'relation_type', 'is_admin']:
            if old_claims.get(key):
                additional_claims[key] = old_claims[key]

        access_token = create_access_token(
            identity=str(user_id),
            additional_claims=additional_claims
        )

        return ApiResponse.success({'access_token': access_token})


@auth_ns.route('/userinfo')
class UserInfo(Resource):
    @login_required
    @auth_ns.response(200, '获取成功', user_info_response)
    @auth_ns.response(401, '未登录或token无效', unauthorized_response)
    def get(self):
        user = AuthService.get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        from app.schemas.auth.user import UserLoginSchema
        user_schema = UserLoginSchema()
        return ApiResponse.success(user_schema.dump(user))


@auth_ns.route('/switch-factory')
class SwitchFactory(Resource):
    """用户关联了多个工厂时，切换到当前工厂"""

    @login_required
    @auth_ns.expect(switch_factory_model)
    @auth_ns.response(200, '切换成功', login_response)
    @auth_ns.response(400, '参数错误', error_response)
    @auth_ns.response(403, '无权限', forbidden_response)
    def post(self):
        user = AuthService.get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        try:
            data = request.get_json()
        except Exception:
            return ApiResponse.error('请正确输入参数', 400)

        factory_id = data.get('factory_id')
        if not factory_id:
            return ApiResponse.error('请指定工厂ID', 400)

        # 验证用户权限
        user_factory = AuthService.verify_factory_permission(user.id, factory_id)
        if not user_factory:
            return ApiResponse.error('无权限访问该工厂', 403)

        from app.models.system.factory import Factory
        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 生成新的 Token
        access_token, refresh_token = AuthService.create_tokens(
            user,
            factory_id=factory_id,
            relation_type=user_factory.relation_type
        )

        factories = AuthService.get_user_factories(user.id)
        current_factory = {
            'id': factory.id,
            'name': factory.name,
            'code': factory.code,
            'relation_type': user_factory.relation_type
        }

        return LoginResponseBuilder.build_employee(
            user, access_token, refresh_token, factories, current_factory
        )


@auth_ns.route('/my-factories')
class MyFactories(Resource):
    @login_required
    @auth_ns.response(200, '获取成功', base_response)
    @auth_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        user = AuthService.get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        factories = AuthService.get_user_factories(user.id)
        return ApiResponse.success(factories)


@auth_ns.route('/logout')
class Logout(Resource):
    @login_required
    @auth_ns.response(200, '登出成功', base_response)
    def post(self):
        return ApiResponse.success(message='登出成功')
