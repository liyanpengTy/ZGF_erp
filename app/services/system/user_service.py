"""用户管理服务。"""

from flask_jwt_extended import get_jwt

from app.constants.identity import ROLE_SCOPE_FACTORY, ROLE_SCOPE_PLATFORM
from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService
from app.services.system.role_service import RoleService


class UserService(BaseService):
    """用户管理服务。"""

    @staticmethod
    def get_user_by_id(user_id):
        """按主键查询未删除用户。"""
        return User.query.filter_by(id=user_id, is_deleted=0).first()

    @staticmethod
    def get_user_by_username(username):
        """按用户名查询未删除用户。"""
        return User.query.filter_by(username=username, is_deleted=0).first()

    @staticmethod
    def get_current_user_id_from_identity(identity):
        """兼容 JWT identity 既可能是字符串也可能是字典的情况。"""
        if isinstance(identity, dict):
            return identity.get('user_id')
        return int(identity)

    @staticmethod
    def get_user_list(current_user, filters):
        """按当前登录人权限范围分页查询用户列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        status = filters.get('status')
        factory_id = filters.get('factory_id')

        query = User.query.filter_by(is_deleted=0)

        if current_user.is_internal_user:
            if factory_id:
                user_ids = db.session.query(UserFactory.user_id).filter_by(factory_id=factory_id, status=1, is_deleted=0).all()
                query = query.filter(User.id.in_([user_id for user_id, in user_ids]))
        else:
            if factory_id and RoleService.has_factory_admin_permission(current_user, factory_id):
                user_ids = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id,
                    status=1,
                    is_deleted=0
                ).all()
                query = query.filter(User.id.in_([user_id for user_id, in user_ids]))
            else:
                query = query.filter(User.id == current_user.id)

        if username:
            query = query.filter(User.username.like(f'%{username}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def create_user(data, current_user_id=None):
        """创建用户基础账号，不在这里处理工厂绑定关系。"""
        existing = UserService.get_user_by_username(data['username'])
        if existing:
            return None, '用户名已存在'

        user = User(
            username=data['username'],
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            nickname=data.get('nickname', ''),
            phone=data.get('phone', ''),
            platform_identity=data.get('platform_identity', 'external_user'),
            status=1
        )
        user.save()
        return user, None

    @staticmethod
    def update_user(user, data):
        """更新用户可编辑的基础资料字段。"""
        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'phone' in data:
            user.phone = data['phone']
        if 'status' in data:
            user.status = data['status']
        user.save()
        return user

    @staticmethod
    def reset_password(user, new_password):
        """重置指定用户密码。"""
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.save()
        return user

    @staticmethod
    def delete_user(user):
        """逻辑删除用户。"""
        user.is_deleted = 1
        user.save()
        return True

    @staticmethod
    def get_user_roles(user_id, factory_id):
        """查询用户在指定工厂上下文下的角色集合。"""
        role_query = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
            UserFactoryRole.user_id == user_id,
            UserFactoryRole.factory_id == factory_id,
            UserFactoryRole.is_deleted == 0,
            Role.status == 1,
            Role.is_deleted == 0,
        )
        if factory_id == 0:
            role_query = role_query.filter(
                Role.scope_type == ROLE_SCOPE_PLATFORM,
                Role.scope_id == 0,
            )
        else:
            role_query = role_query.filter(
                Role.scope_type == ROLE_SCOPE_FACTORY,
                Role.scope_id == factory_id,
            )
        return [record.role for record in role_query.all()]

    @staticmethod
    def assign_roles(user_id, role_ids, factory_id, current_user):
        """先清空旧角色，再按当前上下文重建新的角色绑定。"""
        target_user = UserService.get_user_by_id(user_id)
        if not target_user:
            return False, '用户不存在'

        role_scope_types = set()
        for role_id in role_ids:
            role = Role.query.filter_by(id=role_id, is_deleted=0).first()
            if not role:
                return False, f'角色ID {role_id} 不存在'
            role_scope_types.add(role.scope_type)
            if role.is_factory_role:
                if not factory_id:
                    return False, '工厂角色分配必须指定工厂ID'
                if role.scope_id != factory_id:
                    return False, f'角色 {role.name} 不属于该工厂'
                target_factory = UserFactory.query.filter_by(
                    user_id=user_id,
                    factory_id=factory_id,
                    status=1,
                    is_deleted=0
                ).first()
                if not target_factory:
                    return False, '目标用户不属于该工厂，不能分配工厂角色'
            if role.is_platform_role and not target_user.is_internal_user:
                return False, f'角色 {role.name} 只能分配给平台内部用户'

        if len(role_scope_types) > 1:
            return False, '不能在同一次分配中混合平台角色和工厂角色'

        if ROLE_SCOPE_PLATFORM in role_scope_types or (not role_scope_types and target_user.is_internal_user and factory_id in (None, 0)):
            assignment_factory_id = 0
        else:
            assignment_factory_id = factory_id

        if not current_user.is_platform_admin:
            if assignment_factory_id == 0 or ROLE_SCOPE_PLATFORM in role_scope_types:
                return False, '只有平台管理员可以分配平台角色'
            if not RoleService.has_factory_admin_permission(current_user, assignment_factory_id):
                return False, '只有平台管理员或本工厂管理员可以分配工厂角色'

        if assignment_factory_id is not None:
            db.session.execute(
                UserFactoryRole.__table__.delete().where(
                    UserFactoryRole.user_id == user_id,
                    UserFactoryRole.factory_id == assignment_factory_id
                )
            )
        else:
            db.session.execute(UserFactoryRole.__table__.delete().where(UserFactoryRole.user_id == user_id))

        for role_id in role_ids:
            role = Role.query.get(role_id)
            user_factory_role = UserFactoryRole(
                user_id=user_id,
                factory_id=0 if role.is_platform_role else factory_id,
                role_id=role_id
            )
            db.session.add(user_factory_role)

        db.session.commit()
        return True, None

    @staticmethod
    def get_user_permissions(user_id):
        """把用户角色映射成最终权限编码列表。"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return []

        if user.is_platform_admin:
            menus = Menu.query.filter(
                Menu.permission.isnot(None),
                Menu.permission != '',
                Menu.status == 1,
                Menu.is_deleted == 0
            ).all()
            return [menu.permission for menu in menus]

        claims = get_jwt()
        role_ids = []

        if user.is_internal_user:
            role_records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
                UserFactoryRole.user_id == user.id,
                UserFactoryRole.factory_id == 0,
                UserFactoryRole.is_deleted == 0,
                Role.scope_type == ROLE_SCOPE_PLATFORM,
                Role.scope_id == 0,
                Role.status == 1,
                Role.is_deleted == 0
            ).all()
            role_ids = [record.role_id for record in role_records]
        else:
            factory_id = claims.get('factory_id')
            if not factory_id:
                return []
            role_records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
                UserFactoryRole.user_id == user.id,
                UserFactoryRole.factory_id == factory_id,
                UserFactoryRole.is_deleted == 0,
                Role.scope_type == ROLE_SCOPE_FACTORY,
                Role.scope_id == factory_id,
                Role.status == 1,
                Role.is_deleted == 0
            ).all()
            role_ids = [record.role_id for record in role_records]

        if not role_ids:
            return []

        menu_records = db.session.query(role_menu).filter(role_menu.c.role_id.in_(role_ids)).all()
        menu_ids = list(set(record.menu_id for record in menu_records))
        if not menu_ids:
            return []

        menus = Menu.query.filter(
            Menu.id.in_(menu_ids),
            Menu.permission.isnot(None),
            Menu.permission != '',
            Menu.status == 1,
            Menu.is_deleted == 0
        ).all()
        return [menu.permission for menu in menus]
