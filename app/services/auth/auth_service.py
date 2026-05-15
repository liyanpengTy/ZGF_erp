"""认证服务。"""

from datetime import datetime

from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity
from sqlalchemy import case

from app.extensions import bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService
from app.utils.logger import log_login


class AuthService(BaseService):
    """认证服务。"""

    @staticmethod
    def authenticate(username, password, client_type='pc'):
        """校验用户名密码，并在成功后刷新最后登录时间。"""
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
    def is_platform_admin(user):
        """对外统一判断用户是否为平台管理员。"""
        return bool(user and user.is_platform_admin)

    @staticmethod
    def is_internal_user(user):
        """对外统一判断用户是否属于平台内部人员。"""
        return bool(user and user.is_internal_user)

    @staticmethod
    def build_factory_context(user_factory):
        """把用户-工厂关系对象组装成登录态需要的工厂上下文。"""
        factory = user_factory.factory
        return {
            'id': factory.id,
            'name': factory.name,
            'code': factory.code,
            'relation_type': user_factory.relation_type,
            'relation_type_label': user_factory.relation_type_label,
            'collaborator_type': user_factory.collaborator_type,
            'collaborator_type_label': user_factory.collaborator_type_label,
            'service_expire_date': factory.service_expire_date.isoformat() if factory.service_expire_date else None,
            'service_status': factory.service_status
        }

    @staticmethod
    def get_user_factories(user_id):
        """查询用户有效绑定的工厂列表，并转换成统一返回结构。"""
        relation_priority = case(
            (UserFactory.relation_type == 'owner', 0),
            (UserFactory.relation_type == 'employee', 1),
            (UserFactory.relation_type == 'customer', 2),
            (UserFactory.relation_type == 'collaborator', 3),
            else_=99,
        )
        records = UserFactory.query.filter_by(
            user_id=user_id,
            status=1,
            is_deleted=0
        ).join(Factory, UserFactory.factory_id == Factory.id).filter(
            Factory.is_deleted == 0
        ).order_by(relation_priority.asc(), UserFactory.id.asc()).all()
        return [AuthService.build_factory_context(record) for record in records]

    @staticmethod
    def build_claims(user, factory_id=None, relation_type=None, collaborator_type=None):
        """构建 JWT claims，统一携带平台身份和当前工厂上下文。"""
        claims = {
            'user_id': user.id,
            'platform_identity': user.platform_identity,
            'subject_type': user.get_subject_type([relation_type] if relation_type else []),
            'has_factory': bool(factory_id),
        }

        if factory_id:
            claims.update({
                'factory_id': factory_id,
                'relation_type': relation_type,
                'collaborator_type': collaborator_type,
            })

        return claims

    @staticmethod
    def create_tokens(user, factory_id=None, relation_type=None, collaborator_type=None):
        """根据当前用户和工厂上下文生成 access/refresh token。"""
        claims = AuthService.build_claims(user, factory_id, relation_type, collaborator_type)
        access_token = create_access_token(identity=str(user.id), additional_claims=claims)
        refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
        return access_token, refresh_token

    @staticmethod
    def get_current_user():
        """从当前 JWT 中解析用户并返回数据库对象。"""
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
        """从当前 JWT 中直接取出工厂上下文 ID。"""
        try:
            return get_jwt().get('factory_id')
        except Exception:
            return None

    @staticmethod
    def verify_factory_permission(user_id, factory_id):
        """校验用户是否仍然拥有目标工厂的有效绑定关系。"""
        return UserFactory.query.filter_by(
            user_id=user_id,
            factory_id=factory_id,
            status=1,
            is_deleted=0,
        ).first()
