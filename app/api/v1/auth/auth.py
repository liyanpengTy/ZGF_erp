"""认证接口。"""

import hashlib
from datetime import datetime

from flask import request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity
from flask_restx import Namespace, Resource, fields

from app.api.common.models import get_common_models
from app.extensions import bcrypt
from app.models.auth.user import User
from app.schemas.auth.user import UserLoginSchema
from app.services import AuthService, LoginResponseBuilder
from app.utils.permissions import login_required, refresh_required
from app.utils.response import ApiResponse

auth_ns = Namespace('认证管理-auth', description='认证管理')

common = get_common_models(auth_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']

login_request_model = auth_ns.model('LoginRequest', {
    'username': fields.String(required=True, description='用户名', example='admin'),
    'password': fields.String(required=True, description='密码', example='123456')
})

switch_factory_model = auth_ns.model('SwitchFactoryRequest', {
    'factory_id': fields.Integer(required=True, description='工厂ID')
})

register_request_model = auth_ns.model('RegisterRequest', {
    'username': fields.String(required=True, description='用户名', example='newuser'),
    'password': fields.String(required=True, description='密码', example='123456'),
    'nickname': fields.String(description='昵称', example='新用户'),
    'phone': fields.String(description='手机号', example='13800138000'),
    'invite_code': fields.String(description='邀请码', example='ABC12345')
})

register_response_data = auth_ns.model('RegisterResponseData', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'invite_code': fields.String(description='邀请码')
})

register_response = auth_ns.clone('RegisterResponse', base_response, {
    'data': fields.Nested(register_response_data)
})

user_info_model = auth_ns.model('UserInfo', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'avatar': fields.String(description='头像'),
    'platform_identity': fields.String(description='平台身份'),
    'platform_identity_label': fields.String(description='平台身份名称'),
    'subject_type': fields.String(description='主体类型'),
    'subject_type_label': fields.String(description='主体类型名称'),
    'status': fields.Integer(description='状态'),
    'invite_code': fields.String(description='邀请码'),
    'invited_count': fields.Integer(description='邀请人数'),
    'is_paid': fields.Integer(description='是否已付费'),
    'create_time': fields.String(description='创建时间'),
    'last_login_time': fields.String(description='最后登录时间')
})

factory_info_model = auth_ns.model('FactoryInfo', {
    'id': fields.Integer(description='工厂ID'),
    'name': fields.String(description='工厂名称'),
    'code': fields.String(description='工厂编码'),
    'relation_type': fields.String(description='关系类型'),
    'relation_type_label': fields.String(description='关系类型名称'),
    'collaborator_type': fields.String(description='协作类型'),
    'collaborator_type_label': fields.String(description='协作类型名称'),
    'service_expire_date': fields.String(description='服务到期日期'),
    'service_status': fields.String(description='服务状态')
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


@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_request_model)
    @auth_ns.response(200, '登录成功', login_response)
    @auth_ns.response(400, '用户名或密码错误', error_response)
    @auth_ns.response(401, '账号已被禁用', unauthorized_response)
    def post(self):
        """账号密码登录，并根据身份决定是否附带工厂上下文。"""
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        user, error = AuthService.authenticate(username, password)
        if error:
            return ApiResponse.error(error)

        factories = AuthService.get_user_factories(user.id)
        if AuthService.is_internal_user(user):
            access_token, refresh_token = AuthService.create_tokens(user)
            return LoginResponseBuilder.build_admin(user, access_token, refresh_token)

        if not factories:
            access_token, refresh_token = AuthService.create_tokens(user)
            return LoginResponseBuilder.build_employee(user, access_token, refresh_token, [], None)

        current_factory = factories[0]
        access_token, refresh_token = AuthService.create_tokens(
            user,
            factory_id=current_factory['id'],
            relation_type=current_factory['relation_type'],
            collaborator_type=current_factory.get('collaborator_type')
        )
        return LoginResponseBuilder.build_employee(
            user,
            access_token,
            refresh_token,
            factories,
            current_factory
        )


@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @refresh_required
    @auth_ns.response(200, '刷新成功', refresh_response)
    @auth_ns.response(401, 'refresh_token 无效或已过期', unauthorized_response)
    def post(self):
        """使用 refresh token 刷新 access token，并保留现有身份上下文。"""
        old_claims = get_jwt()
        user_id = old_claims.get('user_id')
        if not user_id:
            identity = get_jwt_identity()
            user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)

        additional_claims = {'user_id': user_id}
        for key in [
            'factory_id',
            'relation_type',
            'collaborator_type',
            'platform_identity',
            'subject_type',
            'has_factory'
        ]:
            if key in old_claims:
                additional_claims[key] = old_claims[key]

        access_token = create_access_token(identity=str(user_id), additional_claims=additional_claims)
        return ApiResponse.success({'access_token': access_token})


@auth_ns.route('/userinfo')
class UserInfo(Resource):
    @login_required
    @auth_ns.response(200, '获取成功', user_info_response)
    @auth_ns.response(401, '未登录或 token 无效', unauthorized_response)
    def get(self):
        """读取当前登录用户的基础资料。"""
        user = AuthService.get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        user_schema = UserLoginSchema()
        return ApiResponse.success(user_schema.dump(user))


@auth_ns.route('/switch-factory')
class SwitchFactory(Resource):
    @login_required
    @auth_ns.expect(switch_factory_model)
    @auth_ns.response(200, '切换成功', login_response)
    @auth_ns.response(400, '参数错误', error_response)
    @auth_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """切换当前工厂上下文，并重新签发带新 claims 的 token。"""
        user = AuthService.get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')

        if AuthService.is_internal_user(user):
            return ApiResponse.error('平台内部人员不使用工厂切换上下文', 400)

        data = request.get_json() or {}
        factory_id = data.get('factory_id')
        if not factory_id:
            return ApiResponse.error('请指定工厂ID', 400)

        user_factory = AuthService.verify_factory_permission(user.id, factory_id)
        if not user_factory:
            return ApiResponse.error('无权限访问该工厂', 403)

        factory = user_factory.factory
        if not factory or factory.is_deleted == 1:
            return ApiResponse.error('工厂不存在')

        access_token, refresh_token = AuthService.create_tokens(
            user,
            factory_id=factory_id,
            relation_type=user_factory.relation_type,
            collaborator_type=user_factory.collaborator_type
        )
        factories = AuthService.get_user_factories(user.id)
        current_factory = AuthService.build_factory_context(user_factory)
        return LoginResponseBuilder.build_employee(
            user,
            access_token,
            refresh_token,
            factories,
            current_factory
        )


@auth_ns.route('/my-factories')
class MyFactories(Resource):
    @login_required
    @auth_ns.response(200, '获取成功', base_response)
    @auth_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回当前用户已绑定的工厂列表。"""
        user = AuthService.get_current_user()
        if not user:
            return ApiResponse.error('用户不存在')
        return ApiResponse.success(AuthService.get_user_factories(user.id))


@auth_ns.route('/logout')
class Logout(Resource):
    @login_required
    @auth_ns.response(200, '退出成功', base_response)
    def post(self):
        """退出登录接口，当前实现由前端自行丢弃 token。"""
        return ApiResponse.success(message='退出成功')


@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_request_model)
    @auth_ns.response(201, '注册成功', register_response)
    @auth_ns.response(400, '参数错误', error_response)
    @auth_ns.response(409, '用户名已存在', error_response)
    def post(self):
        """注册外部普通用户账号，并生成邀请码。"""
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        nickname = data.get('nickname', '')
        phone = data.get('phone', '')
        invite_code = data.get('invite_code')

        existing = User.query.filter_by(username=username, is_deleted=0).first()
        if existing:
            return ApiResponse.error('用户名已存在', 409)

        inviter = None
        if invite_code:
            inviter = User.query.filter_by(invite_code=invite_code, is_deleted=0).first()

        user_invite_code = hashlib.md5(f'{username}{datetime.now()}'.encode()).hexdigest()[:8].upper()
        while User.query.filter_by(invite_code=user_invite_code).first():
            user_invite_code = hashlib.md5(f'{username}{datetime.now()}'.encode()).hexdigest()[:8].upper()

        user = User(
            username=username,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            nickname=nickname,
            phone=phone,
            platform_identity='external_user',
            status=1,
            invite_code=user_invite_code,
            invited_by=inviter.id if inviter else None,
            invited_count=0,
            is_paid=0
        )
        user.save()

        return ApiResponse.success({
            'id': user.id,
            'username': user.username,
            'invite_code': user.invite_code
        }, '注册成功', 201)
