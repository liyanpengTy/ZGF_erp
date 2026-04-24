from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.extensions import db, bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserLoginSchema
from app.utils.logger import log_login
from app.api.v1.shared_models import get_shared_models
from datetime import datetime

auth_ns = Namespace('auth', description='认证管理')

shared = get_shared_models(auth_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

login_request_model = auth_ns.model('LoginRequest', {
    'username': fields.String(required=True, description='用户名', example='admin'),
    'password': fields.String(required=True, description='密码', example='123456')
})

switch_factory_model = auth_ns.model('SwitchFactoryRequest', {
    'factory_id': fields.Integer(required=True, description='工厂ID')
})

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
    'current_factory': fields.Nested(factory_info_model, description='当前工厂')
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


def get_user_factories(user_id):
    """获取用户关联的工厂列表"""
    results = db.session.query(
        Factory.id, Factory.name, Factory.code, UserFactory.relation_type
    ).join(
        UserFactory, UserFactory.factory_id == Factory.id
    ).filter(
        UserFactory.user_id == user_id,
        UserFactory.status == 1,
        Factory.is_deleted == 0,
        UserFactory.is_deleted == 0
    ).all()
    return [{'id': r[0], 'name': r[1], 'code': r[2], 'relation_type': r[3]} for r in results]


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

        user = User.query.filter_by(username=username, status=1, is_deleted=0).first()

        if not user:
            log_login(username, 'pc', 0, '用户名或密码错误')
            return ApiResponse.error('用户名或密码错误')

        if not bcrypt.check_password_hash(user.password, password):
            log_login(username, 'pc', 0, '用户名或密码错误', user.id)
            return ApiResponse.error('用户名或密码错误')

        if user.status != 1:
            log_login(username, 'pc', 0, '账号已被禁用', user.id)
            return ApiResponse.error('账号已被禁用')

        user.last_login_time = datetime.now()
        user.save()

        log_login(username, 'pc', 1, user_id=user.id)

        factories = get_user_factories(user.id)

        # 公司内部人员
        if user.is_admin == 1:
            # ✅ 修改：identity 使用字符串（用户ID）
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={
                    'user_id': user.id,
                    'is_admin': True,
                    'user_type': 'admin'
                }
            )
            refresh_token = create_refresh_token(
                identity=str(user.id),
                additional_claims={
                    'user_id': user.id,
                    'is_admin': True,
                    'user_type': 'admin'
                }
            )

            user_schema = UserLoginSchema()
            user_info = user_schema.dump(user)

            return ApiResponse.success({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_info': user_info,
                'factories': [],
                'current_factory': None
            })

        if not factories:
            # 没有工厂的员工也能登录，但不设置默认工厂
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={
                    'user_id': user.id,
                    'is_admin': False,
                    'has_factory': False,
                    'user_type': 'employee'
                }
            )
            refresh_token = create_refresh_token(
                identity=str(user.id),
                additional_claims={
                    'user_id': user.id,
                    'is_admin': False,
                    'has_factory': False,
                    'user_type': 'employee'
                }
            )

            user_schema = UserLoginSchema()
            user_info = user_schema.dump(user)

            return ApiResponse.success({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_info': user_info,
                'factories': [],
                'current_factory': None
            })

        current_factory = factories[0]

        # ✅ 修改：identity 使用字符串（用户ID）
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'user_id': user.id,
                'factory_id': current_factory['id'],
                'relation_type': current_factory['relation_type'],
                'user_type': 'employee'
            }
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),
            additional_claims={
                'user_id': user.id,
                'factory_id': current_factory['id'],
                'relation_type': current_factory['relation_type'],
                'user_type': 'employee'
            }
        )

        user_schema = UserLoginSchema()
        user_info = user_schema.dump(user)

        return ApiResponse.success({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_info': user_info,
            'factories': factories,
            'current_factory': current_factory
        })


@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @jwt_required(refresh=True)
    @auth_ns.response(200, '刷新成功', refresh_response)
    @auth_ns.response(401, 'refresh_token无效或已过期', unauthorized_response)
    def post(self):
        from flask_jwt_extended import get_jwt
        old_claims = get_jwt()

        user_id = old_claims.get('user_id')
        if not user_id:
            # 兼容旧 token（identity 直接是用户ID）
            identity = get_jwt_identity()
            if isinstance(identity, dict):
                user_id = identity.get('user_id')
            else:
                user_id = int(identity)

        additional_claims = {'user_id': user_id}

        # 复制其他字段
        if old_claims.get('factory_id'):
            additional_claims['factory_id'] = old_claims['factory_id']
        if old_claims.get('relation_type'):
            additional_claims['relation_type'] = old_claims['relation_type']
        if old_claims.get('is_admin'):
            additional_claims['is_admin'] = old_claims['is_admin']

        access_token = create_access_token(
            identity=str(user_id),
            additional_claims=additional_claims
        )
        return ApiResponse.success({'access_token': access_token})


@auth_ns.route('/userinfo')
class UserInfo(Resource):
    @jwt_required()
    @auth_ns.response(200, '获取成功', user_info_response)
    @auth_ns.response(401, '未登录或token无效', unauthorized_response)
    def get(self):
        # identity = get_jwt_identity()
        # user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        user_id = claims.get('user_id')

        user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not user:
            return ApiResponse.error('用户不存在')

        user_schema = UserLoginSchema()
        return ApiResponse.success(user_schema.dump(user))


@auth_ns.route('/switch-factory')
class SwitchFactory(Resource):
    """用户关联了多个工厂时，切换到当前工厂"""
    @jwt_required()
    @auth_ns.expect(switch_factory_model)
    @auth_ns.response(200, '切换成功', login_response)
    @auth_ns.response(400, '参数错误', error_response)
    @auth_ns.response(403, '无权限', forbidden_response)
    def post(self):
        # identity = get_jwt_identity()
        # user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        user_id = claims.get('user_id')

        # 增加 JSON 解析错误处理
        try:
            data = request.get_json()
        except Exception as e:
            return ApiResponse.error('请正确输入参数', 400)

        # data = request.get_json()
        factory_id = data.get('factory_id')

        if not factory_id:
            return ApiResponse.error('请指定工厂ID', 400)

        user_factory = UserFactory.query.filter_by(
            user_id=user_id,
            factory_id=factory_id,
            status=1,
            is_deleted=0
        ).first()

        if not user_factory:
            return ApiResponse.error('无权限访问该工厂', 403)

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        factories = get_user_factories(user.id)

        access_token = create_access_token(identity={
            'user_id': user.id,
            'factory_id': factory_id,
            'relation_type': user_factory.relation_type
        })
        refresh_token = create_refresh_token(identity={
            'user_id': user.id,
            'factory_id': factory_id,
            'relation_type': user_factory.relation_type
        })

        user_schema = UserLoginSchema()
        user_info = user_schema.dump(user)

        return ApiResponse.success({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_info': user_info,
            'factories': factories,
            'current_factory': {
                'id': factory.id,
                'name': factory.name,
                'code': factory.code,
                'relation_type': user_factory.relation_type
            }
        })


@auth_ns.route('/my-factories')
class MyFactories(Resource):
    @jwt_required()
    @auth_ns.response(200, '获取成功', base_response)
    @auth_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)

        factories = get_user_factories(user_id)

        return ApiResponse.success(factories)


@auth_ns.route('/logout')
class Logout(Resource):
    @jwt_required()
    @auth_ns.response(200, '登出成功', base_response)
    def post(self):
        return ApiResponse.success(message='登出成功')
