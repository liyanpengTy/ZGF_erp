"""用户管理服务。"""

from collections import defaultdict

from flask_jwt_extended import get_jwt
from sqlalchemy import case, or_

from app.constants.identity import (
    ROLE_DATA_SCOPE_ALL,
    ROLE_DATA_SCOPE_ASSIGNED,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_DATA_SCOPE_SELF_ONLY,
    ROLE_SCOPE_FACTORY,
    ROLE_SCOPE_PLATFORM,
)
from app.constants.permissions import (
    PERM_FACTORY_MANAGEMENT_ROLE_EDIT,
    PERM_SYSTEM_FACTORY_MANAGE_ROLES,
    PERM_SYSTEM_ROLE_EDIT,
)
from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService
from app.services.system.role_service import RoleService
from app.utils.cache import SimpleTTLCache
from app.utils.permissions import has_any_permission


PERMISSION_CACHE = SimpleTTLCache(default_ttl=300)
DATA_SCOPE_PRIORITY = {
    ROLE_DATA_SCOPE_SELF_ONLY: 1,
    ROLE_DATA_SCOPE_OWN_RELATED: 2,
    ROLE_DATA_SCOPE_ASSIGNED: 3,
    ROLE_DATA_SCOPE_ALL: 4,
}
DATA_SCOPE_LABELS = {
    ROLE_DATA_SCOPE_ALL: '全工厂数据',
    ROLE_DATA_SCOPE_ASSIGNED: '分配数据',
    ROLE_DATA_SCOPE_OWN_RELATED: '本人关联数据',
    ROLE_DATA_SCOPE_SELF_ONLY: '仅个人数据',
}


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
    def get_user_factory_relations(user_id):
        """查询单个用户当前有效的工厂挂靠关系。"""
        return UserService.get_user_factory_relations_map([user_id]).get(user_id, [])

    @staticmethod
    def get_user_factory_relations_map(user_ids):
        """批量查询用户工厂挂靠关系，避免列表接口出现 N+1。"""
        if not user_ids:
            return {}

        relation_priority = case(
            (UserFactory.relation_type == 'owner', 0),
            (UserFactory.relation_type == 'employee', 1),
            (UserFactory.relation_type == 'customer', 2),
            (UserFactory.relation_type == 'collaborator', 3),
            else_=99,
        )
        relations = (
            UserFactory.query.join(Factory, Factory.id == UserFactory.factory_id)
            .filter(
                UserFactory.user_id.in_(user_ids),
                UserFactory.status == 1,
                UserFactory.is_deleted == 0,
                Factory.is_deleted == 0,
            )
            .order_by(UserFactory.user_id.asc(), relation_priority.asc(), UserFactory.id.asc())
            .all()
        )

        relation_map = defaultdict(list)
        for relation in relations:
            relation_map[relation.user_id].append({
                'factory_id': relation.factory_id,
                'factory_name': relation.factory.name if relation.factory else None,
                'factory_code': relation.factory.code if relation.factory else None,
                'relation_type': relation.relation_type,
                'relation_type_label': relation.relation_type_label,
                'collaborator_type': relation.collaborator_type,
                'collaborator_type_label': relation.collaborator_type_label,
                'entry_date': relation.entry_date.isoformat() if relation.entry_date else None,
                'leave_date': relation.leave_date.isoformat() if relation.leave_date else None,
            })
        return relation_map

    @staticmethod
    def get_user_role_bindings(user_id):
        """查询单个用户当前绑定的全部角色。"""
        return UserService.get_user_role_bindings_map([user_id]).get(user_id, [])

    @staticmethod
    def get_user_role_bindings_map(user_ids):
        """批量查询用户角色绑定，避免列表接口出现 N+1。"""
        if not user_ids:
            return {}

        records = (
            UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id)
            .filter(
                UserFactoryRole.user_id.in_(user_ids),
                UserFactoryRole.is_deleted == 0,
                Role.status == 1,
                Role.is_deleted == 0,
            )
            .order_by(UserFactoryRole.user_id.asc(), UserFactoryRole.factory_id.desc(), Role.sort_order.asc(), Role.id.asc())
            .all()
        )

        role_map = defaultdict(list)
        for record in records:
            role_map[record.user_id].append({
                'role_id': record.role.id,
                'role_name': record.role.name,
                'role_code': record.role.code,
                'scope_type': record.role.scope_type,
                'scope_type_label': record.role.scope_type_label,
                'scope_id': record.role.scope_id,
                'factory_id': record.factory_id,
                'is_factory_admin': record.role.is_factory_admin,
            })
        return role_map

    @staticmethod
    def build_user_view(user, factory_relations=None, role_bindings=None, viewer_user=None, viewer_factory_id=None):
        """组装用户展示数据，支持按查看人上下文收敛工厂关系与角色绑定。"""
        factory_relations = factory_relations if factory_relations is not None else UserService.get_user_factory_relations(user.id)
        role_bindings = role_bindings if role_bindings is not None else UserService.get_user_role_bindings(user.id)

        if viewer_user and not viewer_user.is_internal_user and viewer_user.id != user.id:
            visible_factory_ids = {viewer_factory_id} if viewer_factory_id else set()
            factory_relations = [item for item in factory_relations if item['factory_id'] in visible_factory_ids]
            role_bindings = [item for item in role_bindings if item['factory_id'] in visible_factory_ids]

        relation_types = [item['relation_type'] for item in factory_relations]
        primary_relation = factory_relations[0] if factory_relations else None

        return {
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'phone': user.phone,
            'avatar': user.avatar,
            'platform_identity': user.platform_identity,
            'platform_identity_label': user.platform_identity_label,
            'subject_type': user.get_subject_type(relation_types),
            'subject_type_label': user.get_subject_type_label(relation_types),
            'status': user.status,
            'invite_code': user.invite_code,
            'invited_count': user.invited_count,
            'is_paid': user.is_paid,
            'created_by': user.created_by,
            'create_time': user.create_time.strftime('%Y-%m-%d %H:%M:%S') if user.create_time else None,
            'last_login_time': user.last_login_time.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_time else None,
            'factory_id': primary_relation['factory_id'] if primary_relation else None,
            'factory_name': primary_relation['factory_name'] if primary_relation else None,
            'factory_ids': [item['factory_id'] for item in factory_relations],
            'factory_relations': factory_relations,
            'role_ids': [item['role_id'] for item in role_bindings],
            'role_bindings': role_bindings,
        }

    @staticmethod
    def _get_permission_codes_by_role_ids(role_ids):
        """把角色 ID 集合映射成去重后的权限编码列表。"""
        if not role_ids:
            return []

        cache_key = ('permission_codes', tuple(sorted(set(role_ids))))
        cached = PERMISSION_CACHE.get(cache_key)
        if cached is not None:
            return cached

        menu_records = db.session.query(role_menu).filter(role_menu.c.role_id.in_(role_ids)).all()
        menu_ids = sorted({record.menu_id for record in menu_records})
        if not menu_ids:
            PERMISSION_CACHE.set(cache_key, [])
            return []

        menus = Menu.query.filter(
            Menu.id.in_(menu_ids),
            Menu.permission.isnot(None),
            Menu.permission != '',
            Menu.status == 1,
            Menu.is_deleted == 0,
        ).all()
        permissions = sorted({menu.permission for menu in menus})
        PERMISSION_CACHE.set(cache_key, permissions)
        return permissions

    @staticmethod
    def _get_current_context_role_ids(user):
        """按当前 JWT 上下文解析当前有效角色集合。"""
        if user.is_platform_admin:
            return []

        claims = get_jwt()
        if user.is_internal_user:
            records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
                UserFactoryRole.user_id == user.id,
                UserFactoryRole.factory_id == 0,
                UserFactoryRole.is_deleted == 0,
                Role.scope_type == ROLE_SCOPE_PLATFORM,
                Role.scope_id == 0,
                Role.status == 1,
                Role.is_deleted == 0,
            ).all()
            return [record.role_id for record in records]

        factory_id = claims.get('factory_id')
        if not factory_id:
            return []

        records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
            UserFactoryRole.user_id == user.id,
            UserFactoryRole.factory_id == factory_id,
            UserFactoryRole.is_deleted == 0,
            Role.scope_type == ROLE_SCOPE_FACTORY,
            Role.scope_id == factory_id,
            Role.status == 1,
            Role.is_deleted == 0,
        ).all()
        return [record.role_id for record in records]

    @staticmethod
    def _get_current_context_roles(user, current_factory_id=None):
        """按当前上下文返回生效角色对象列表，用于解析数据范围。"""
        if user.is_platform_admin:
            return []

        claims = get_jwt()
        if user.is_internal_user:
            records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
                UserFactoryRole.user_id == user.id,
                UserFactoryRole.factory_id == 0,
                UserFactoryRole.is_deleted == 0,
                Role.scope_type == ROLE_SCOPE_PLATFORM,
                Role.scope_id == 0,
                Role.status == 1,
                Role.is_deleted == 0,
            ).all()
            return [record.role for record in records]

        target_factory_id = current_factory_id or claims.get('factory_id')
        if not target_factory_id:
            return []

        records = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
            UserFactoryRole.user_id == user.id,
            UserFactoryRole.factory_id == target_factory_id,
            UserFactoryRole.is_deleted == 0,
            Role.scope_type == ROLE_SCOPE_FACTORY,
            Role.scope_id == target_factory_id,
            Role.status == 1,
            Role.is_deleted == 0,
        ).all()
        return [record.role for record in records]

    @staticmethod
    def get_current_data_scope(user, current_factory_id=None):
        """返回当前用户在当前上下文中的最宽数据范围。"""
        if not user:
            return ROLE_DATA_SCOPE_SELF_ONLY
        if user.is_platform_admin:
            return ROLE_DATA_SCOPE_ALL

        roles = UserService._get_current_context_roles(user, current_factory_id=current_factory_id)
        if not roles:
            return ROLE_DATA_SCOPE_SELF_ONLY

        return max(
            (role.data_scope or ROLE_DATA_SCOPE_OWN_RELATED for role in roles),
            key=lambda scope: DATA_SCOPE_PRIORITY.get(scope, 0),
        )

    @staticmethod
    def get_data_scope_label(data_scope):
        """返回数据范围中文名称。"""
        return DATA_SCOPE_LABELS.get(data_scope, data_scope)

    @staticmethod
    def apply_user_data_scope(query, current_user, current_factory_id=None):
        """按当前用户数据范围收敛用户查询。"""
        data_scope = UserService.get_current_data_scope(current_user, current_factory_id=current_factory_id)
        if current_user.is_platform_admin or data_scope == ROLE_DATA_SCOPE_ALL:
            return query
        if data_scope == ROLE_DATA_SCOPE_ASSIGNED:
            return query.filter(or_(User.id == current_user.id, User.created_by == current_user.id))
        if data_scope == ROLE_DATA_SCOPE_OWN_RELATED:
            return query.filter(
                or_(
                    User.id == current_user.id,
                    User.created_by == current_user.id,
                    User.invited_by == current_user.id,
                )
            )
        return query.filter(User.id == current_user.id)

    @staticmethod
    def check_user_data_scope(current_user, target_user, current_factory_id=None):
        """校验目标用户是否落在当前用户的数据范围内。"""
        if not current_user or not target_user:
            return False
        if current_user.is_platform_admin:
            return True

        data_scope = UserService.get_current_data_scope(current_user, current_factory_id=current_factory_id)
        if data_scope == ROLE_DATA_SCOPE_ALL:
            return True
        if data_scope == ROLE_DATA_SCOPE_ASSIGNED:
            return target_user.id == current_user.id or target_user.created_by == current_user.id
        if data_scope == ROLE_DATA_SCOPE_OWN_RELATED:
            return (
                target_user.id == current_user.id
                or target_user.created_by == current_user.id
                or target_user.invited_by == current_user.id
            )
        return target_user.id == current_user.id

    @staticmethod
    def check_creator_customer_data_scope(current_user, creator_user_id=None, customer_user_id=None, current_factory_id=None):
        """校验带有创建人和客户归属的业务数据是否落在当前用户数据范围内。"""
        if not current_user:
            return False
        if current_user.is_platform_admin:
            return True

        data_scope = UserService.get_current_data_scope(current_user, current_factory_id=current_factory_id)
        if data_scope == ROLE_DATA_SCOPE_ALL:
            return True

        related_user_ids = {user_id for user_id in (creator_user_id, customer_user_id) if user_id}
        return current_user.id in related_user_ids

    @staticmethod
    def clear_permission_cache():
        """清空用户权限相关缓存。"""
        PERMISSION_CACHE.clear()

    @staticmethod
    def get_permission_summary(user_id):
        """返回当前用户的角色绑定、当前上下文权限并集和全量权限并集。"""
        user = UserService.get_user_by_id(user_id)
        if not user:
            return {
                'current_factory_id': None,
                'current_data_scope': ROLE_DATA_SCOPE_SELF_ONLY,
                'current_data_scope_label': UserService.get_data_scope_label(ROLE_DATA_SCOPE_SELF_ONLY),
                'current_permissions': [],
                'all_permissions': [],
                'role_bindings': [],
            }

        role_bindings = UserService.get_user_role_bindings(user.id)
        claims = get_jwt()
        current_factory_id = claims.get('factory_id')

        if user.is_platform_admin:
            cache_key = ('all_permissions', 'platform_admin')
            all_permissions = PERMISSION_CACHE.get(cache_key)
            if all_permissions is None:
                all_permissions = sorted(
                    {
                        menu.permission
                        for menu in Menu.query.filter(
                            Menu.permission.isnot(None),
                            Menu.permission != '',
                            Menu.status == 1,
                            Menu.is_deleted == 0,
                        ).all()
                    }
                )
                PERMISSION_CACHE.set(cache_key, all_permissions)
            return {
                'current_factory_id': current_factory_id,
                'current_data_scope': ROLE_DATA_SCOPE_ALL,
                'current_data_scope_label': UserService.get_data_scope_label(ROLE_DATA_SCOPE_ALL),
                'current_permissions': all_permissions,
                'all_permissions': all_permissions,
                'role_bindings': role_bindings,
            }

        all_role_ids = [item['role_id'] for item in role_bindings]
        current_role_ids = UserService._get_current_context_role_ids(user)
        current_data_scope = UserService.get_current_data_scope(user, current_factory_id=current_factory_id)
        return {
            'current_factory_id': current_factory_id,
            'current_data_scope': current_data_scope,
            'current_data_scope_label': UserService.get_data_scope_label(current_data_scope),
            'current_permissions': UserService._get_permission_codes_by_role_ids(current_role_ids),
            'all_permissions': UserService._get_permission_codes_by_role_ids(all_role_ids),
            'role_bindings': role_bindings,
        }

    @staticmethod
    def _build_user_query(current_user, factory_id=None, relation_type=None):
        """按当前登录人权限范围构造用户查询。"""
        query = User.query.filter_by(is_deleted=0)

        if current_user.is_internal_user:
            if factory_id:
                user_ids_query = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id,
                    status=1,
                    is_deleted=0,
                )
                if relation_type:
                    user_ids_query = user_ids_query.filter_by(relation_type=relation_type)
                user_ids = [user_id for user_id, in user_ids_query.all()]
                query = query.filter(User.id.in_(user_ids))
            return UserService.apply_user_data_scope(query, current_user, current_factory_id=factory_id)

        if factory_id and RoleService.has_factory_admin_permission(current_user, factory_id):
            user_ids_query = db.session.query(UserFactory.user_id).filter_by(
                factory_id=factory_id,
                status=1,
                is_deleted=0,
            )
            if relation_type:
                user_ids_query = user_ids_query.filter_by(relation_type=relation_type)
            user_ids = [user_id for user_id, in user_ids_query.all()]
            query = query.filter(User.id.in_(user_ids))
            return UserService.apply_user_data_scope(query, current_user, current_factory_id=factory_id)

        return UserService.apply_user_data_scope(query.filter(User.id == current_user.id), current_user, current_factory_id=factory_id)

    @staticmethod
    def _apply_user_basic_filters(query, username='', status=None, platform_identity=None):
        """统一叠加用户名、状态和平台身份筛选。"""
        if username:
            query = query.filter(User.username.like(f'%{username}%'))
        if status is not None:
            query = query.filter_by(status=status)
        if platform_identity:
            query = query.filter_by(platform_identity=platform_identity)
        return query

    @staticmethod
    def get_user_list(current_user, filters, viewer_factory_id=None):
        """按当前登录人权限范围分页查询用户列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        factory_id = filters.get('factory_id')

        query = UserService._build_user_query(
            current_user=current_user,
            factory_id=factory_id,
            relation_type=filters.get('relation_type'),
        )
        query = UserService._apply_user_basic_filters(
            query=query,
            username=filters.get('username', ''),
            status=filters.get('status'),
            platform_identity=filters.get('platform_identity'),
        )

        pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        user_ids = [user.id for user in pagination.items]
        relation_map = UserService.get_user_factory_relations_map(user_ids)
        role_map = UserService.get_user_role_bindings_map(user_ids)

        return {
            'items': [
                UserService.build_user_view(
                    user,
                    factory_relations=relation_map.get(user.id, []),
                    role_bindings=role_map.get(user.id, []),
                    viewer_user=current_user,
                    viewer_factory_id=viewer_factory_id,
                )
                for user in pagination.items
            ],
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def get_user_options(current_user, filters):
        """查询轻量用户选项列表，供客户、员工、协作用户选择器使用。"""
        query = UserService._build_user_query(
            current_user=current_user,
            factory_id=filters.get('factory_id'),
            relation_type=filters.get('relation_type'),
        )
        query = UserService._apply_user_basic_filters(
            query=query,
            username=filters.get('username', ''),
            status=filters.get('status'),
            platform_identity=filters.get('platform_identity'),
        )
        users = query.order_by(User.id.desc()).all()

        return [
            {
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'phone': user.phone,
                'platform_identity': user.platform_identity,
                'platform_identity_label': user.platform_identity_label,
            }
            for user in users
        ]

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
            status=1,
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
        """查询用户在指定工厂上下文中的角色集合。"""
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
                    is_deleted=0,
                ).first()
                if not target_factory:
                    return False, '目标用户不属于该工厂，不能分配工厂角色'
            if role.is_platform_role and not target_user.is_internal_user:
                return False, f'角色 {role.name} 只能分配给平台内部用户'

        if len(role_scope_types) > 1:
            return False, '不能在同一次分配中混合平台角色和工厂角色'

        if ROLE_SCOPE_PLATFORM in role_scope_types or (
            not role_scope_types and target_user.is_internal_user and factory_id in (None, 0)
        ):
            assignment_factory_id = 0
        else:
            assignment_factory_id = factory_id

        if not current_user.is_platform_admin:
            if assignment_factory_id == 0 or ROLE_SCOPE_PLATFORM in role_scope_types:
                if not current_user.is_internal_user:
                    return False, '只有平台内部用户可以分配平台角色'
                has_permission, _ = has_any_permission(current_user, [PERM_SYSTEM_ROLE_EDIT])
                if not has_permission:
                    return False, '无权限分配平台角色'
            elif current_user.is_internal_user:
                has_permission, _ = has_any_permission(
                    current_user,
                    [PERM_SYSTEM_ROLE_EDIT, PERM_FACTORY_MANAGEMENT_ROLE_EDIT, PERM_SYSTEM_FACTORY_MANAGE_ROLES],
                    factory_id=assignment_factory_id,
                )
                if not has_permission:
                    return False, '无权限分配工厂角色'
            elif not RoleService.has_factory_admin_permission(current_user, assignment_factory_id):
                return False, '只有平台管理员或本工厂管理员可以分配工厂角色'

        if assignment_factory_id is not None:
            db.session.execute(
                UserFactoryRole.__table__.delete().where(
                    UserFactoryRole.user_id == user_id,
                    UserFactoryRole.factory_id == assignment_factory_id,
                )
            )
        else:
            db.session.execute(UserFactoryRole.__table__.delete().where(UserFactoryRole.user_id == user_id))

        for role_id in role_ids:
            role = db.session.get(Role, role_id)
            user_factory_role = UserFactoryRole(
                user_id=user_id,
                factory_id=0 if role.is_platform_role else factory_id,
                role_id=role_id,
            )
            db.session.add(user_factory_role)

        db.session.commit()
        RoleService.clear_permission_cache()
        return True, None
