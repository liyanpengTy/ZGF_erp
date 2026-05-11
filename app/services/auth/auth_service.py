"""认证服务 - 业务逻辑层"""
from datetime import datetime

from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity

from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService
from app.utils.logger import log_login


class AuthService(BaseService):
    """认证服务"""

    @staticmethod
    def authenticate(username, password, client_type='pc'):
        """用户认证"""
        user = User.query.filter_by(username=username, status=1, is_deleted=0).first()

        if not user:
            log_login(username, client_type, 0, '用户名或密码错误')
            return None, '用户名或密码错误'

        if not bcrypt.check_password_hash(user.password, password):
            log_login(username, client_type, 0, '用户名或密码错误', user.id)
            return None, '用户名或密码错误'

        if user.status != 1:
            log_login(username, client_type, 0, '账号已被禁用', user.id)
            return None, '账号已被禁用'

        user.last_login_time = datetime.now()
        user.save()
        log_login(username, client_type, 1, user_id=user.id)

        return user, None

    @staticmethod
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

    @staticmethod
    def build_claims(user, factory_id=None, relation_type=None):
        """构建 JWT claims"""
        if user.is_admin == 1:
            return {
                'user_id': user.id,
                'is_admin': True,
                'user_type': 'admin',
                'has_factory': False,
            }

        if factory_id:
            return {
                'user_id': user.id,
                'is_admin': False,
                'user_type': 'employee',
                'has_factory': True,
                'factory_id': factory_id,
                'relation_type': relation_type,
            }

        return {
            'user_id': user.id,
            'is_admin': False,
            'user_type': 'employee',
            'has_factory': False,
        }

    @staticmethod
    def create_tokens(user, factory_id=None, relation_type=None):
        """创建 access_token 和 refresh_token"""
        claims = AuthService.build_claims(user, factory_id, relation_type)

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims=claims,
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),
            additional_claims=claims,
        )

        return access_token, refresh_token

    @staticmethod
    def get_current_user():
        """获取当前登录用户"""
        try:
            claims = get_jwt()
            user_id = claims.get('user_id')

            if not user_id:
                identity = get_jwt_identity()
                user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)

            return User.query.filter_by(id=user_id, is_deleted=0).first()
        except Exception:
            return None

    @staticmethod
    def get_current_factory_id():
        """获取当前 JWT 中的工厂 ID"""
        try:
            claims = get_jwt()
            return claims.get('factory_id')
        except Exception:
            return None

    @staticmethod
    def verify_factory_permission(user_id, factory_id):
        """验证用户是否有权限访问该工厂"""
        return UserFactory.query.filter_by(
            user_id=user_id,
            factory_id=factory_id,
            status=1,
            is_deleted=0,
        ).first()
