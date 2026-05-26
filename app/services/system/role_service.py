"""角色管理服务。"""

from app.constants.identity import (
    RELATION_TYPE_OWNER,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_SCOPE_FACTORY,
    ROLE_SCOPE_PLATFORM,
)
from app.extensions import db
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService
from app.utils.cache import SimpleTTLCache


FACTORY_ROLE_FORBIDDEN_PERMISSION_PREFIXES = ('system.',)
FACTORY_ADMIN_PERMISSION_CACHE = SimpleTTLCache(default_ttl=300)


class RoleService(BaseService):
    """提供角色查询、维护和菜单绑定能力。"""

    @staticmethod
    def clear_permission_cache():
        """清空角色与用户权限相关缓存。"""
        from app.services.system.user_service import UserService

        FACTORY_ADMIN_PERMISSION_CACHE.clear()
        UserService.clear_permission_cache()

    @staticmethod
    def has_factory_admin_permission(user, factory_id):
        """判断用户是否拥有指定工厂的管理能力。"""
        if not user or user.is_internal_user or not factory_id:
            return False

        cache_key = (user.id, factory_id)
        cached = FACTORY_ADMIN_PERMISSION_CACHE.get(cache_key)
        if cached is not None:
            return cached

        owner_relation = UserFactory.query.filter_by(
            user_id=user.id,
            factory_id=factory_id,
            relation_type=RELATION_TYPE_OWNER,
            status=1,
            is_deleted=0,
        ).first()
        if owner_relation:
            FACTORY_ADMIN_PERMISSION_CACHE.set(cache_key, True)
            return True

        admin_role = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
            UserFactoryRole.user_id == user.id,
            UserFactoryRole.factory_id == factory_id,
            UserFactoryRole.is_deleted == 0,
            Role.scope_type == ROLE_SCOPE_FACTORY,
            Role.scope_id == factory_id,
            Role.is_factory_admin == 1,
            Role.status == 1,
            Role.is_deleted == 0,
        ).first()
        result = admin_role is not None
        FACTORY_ADMIN_PERMISSION_CACHE.set(cache_key, result)
        return result

    @staticmethod
    def normalize_scope(scope_type, scope_id):
        """归一化角色归属范围，避免平台角色携带工厂主键。"""
        if scope_type == ROLE_SCOPE_PLATFORM:
            return ROLE_SCOPE_PLATFORM, 0
        if scope_type == ROLE_SCOPE_FACTORY:
            if not scope_id:
                return None, None
            return ROLE_SCOPE_FACTORY, scope_id
        return scope_type, scope_id or 0

    @staticmethod
    def get_role_by_id(role_id):
        """按主键查询未删除角色。"""
        return Role.query.filter_by(id=role_id, is_deleted=0).first()

    @staticmethod
    def get_role_by_code(scope_type, scope_id, code):
        """按范围和编码查询角色。"""
        scope_type, scope_id = RoleService.normalize_scope(scope_type, scope_id)
        return Role.query.filter_by(
            scope_type=scope_type,
            scope_id=scope_id,
            code=code,
            is_deleted=0,
        ).first()

    @staticmethod
    def get_role_by_name(scope_type, scope_id, name):
        """按范围和名称查询角色。"""
        scope_type, scope_id = RoleService.normalize_scope(scope_type, scope_id)
        return Role.query.filter_by(
            scope_type=scope_type,
            scope_id=scope_id,
            name=name,
            is_deleted=0,
        ).first()

    @staticmethod
    def _build_role_query(current_user, current_factory_id=None, scope_type=None, scope_id=None):
        """按当前用户上下文构造角色查询。"""
        if current_user.is_internal_user:
            query = Role.query.filter(Role.is_deleted == 0)
            if scope_type:
                normalized_scope_type, normalized_scope_id = RoleService.normalize_scope(scope_type, scope_id)
                if scope_type == ROLE_SCOPE_FACTORY and not normalized_scope_id:
                    return None, '工厂角色请指定 scope_id'
                query = query.filter(
                    Role.scope_type == normalized_scope_type,
                    Role.scope_id == normalized_scope_id,
                )
            return query, None

        if not current_factory_id:
            return None, '请先选择工厂上下文'
        if not RoleService.has_factory_admin_permission(current_user, current_factory_id):
            return None, '无权限查看角色'

        query = Role.query.filter_by(
            scope_type=ROLE_SCOPE_FACTORY,
            scope_id=current_factory_id,
            is_deleted=0,
        )
        return query, None

    @staticmethod
    def get_role_list(current_user, filters, current_factory_id=None):
        """分页查询角色列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')
        scope_type = filters.get('scope_type')
        scope_id = filters.get('scope_id')

        query, error = RoleService._build_role_query(current_user, current_factory_id, scope_type, scope_id)
        if error:
            return None, error

        if name:
            query = query.filter(Role.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Role.sort_order.asc(), Role.id.asc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False,
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }, None

    @staticmethod
    def get_role_options(current_user, filters, current_factory_id=None):
        """查询角色下拉选项列表。"""
        name = filters.get('name', '')
        status = filters.get('status')
        scope_type = filters.get('scope_type')
        scope_id = filters.get('scope_id')

        query, error = RoleService._build_role_query(current_user, current_factory_id, scope_type, scope_id)
        if error:
            return None, error

        if name:
            query = query.filter(Role.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        return query.order_by(Role.sort_order.asc(), Role.id.asc()).all(), None

    @staticmethod
    def create_role(data):
        """创建角色并初始化数据范围。"""
        scope_type, scope_id = RoleService.normalize_scope(data['scope_type'], data.get('scope_id'))
        if scope_type == ROLE_SCOPE_FACTORY and not scope_id:
            return None, '工厂角色必须指定 scope_id'

        existing_code = RoleService.get_role_by_code(scope_type, scope_id, data['code'])
        if existing_code:
            return None, '角色编码已存在'

        existing_name = RoleService.get_role_by_name(scope_type, scope_id, data['name'])
        if existing_name:
            return None, '角色名称已存在'

        role = Role(
            scope_type=scope_type,
            scope_id=scope_id,
            name=data['name'],
            code=data['code'],
            description=data.get('description', ''),
            sort_order=data.get('sort_order', 0),
            data_scope=data.get('data_scope', ROLE_DATA_SCOPE_OWN_RELATED),
            is_factory_admin=data.get('is_factory_admin', 0),
            status=1,
        )
        role.save()
        RoleService.clear_permission_cache()
        return role, None

    @staticmethod
    def update_role(role, data):
        """更新角色名称、排序、状态与数据范围。"""
        if 'name' in data:
            existing = RoleService.get_role_by_name(role.scope_type, role.scope_id, data['name'])
            if existing and existing.id != role.id:
                return None, '角色名称已存在'
            role.name = data['name']

        if 'description' in data:
            role.description = data['description']
        if 'status' in data:
            role.status = data['status']
        if 'sort_order' in data:
            role.sort_order = data['sort_order']
        if 'data_scope' in data:
            role.data_scope = data['data_scope']
        if 'is_factory_admin' in data:
            role.is_factory_admin = data['is_factory_admin']

        role.save()
        RoleService.clear_permission_cache()
        return role, None

    @staticmethod
    def delete_role(role):
        """逻辑删除角色，删除前校验是否仍被使用。"""
        user_role_count = UserFactoryRole.query.filter_by(role_id=role.id, is_deleted=0).count()
        if user_role_count > 0:
            return False, f'已有 {user_role_count} 个用户关联此角色，无法删除'

        role.is_deleted = 1
        role.save()
        RoleService.clear_permission_cache()
        return True, None

    @staticmethod
    def get_role_menu_ids(role_id):
        """查询角色已绑定的菜单 ID 列表。"""
        menu_ids = db.session.query(role_menu.c.menu_id).filter_by(role_id=role_id).all()
        return [menu_id for menu_id, in menu_ids]

    @staticmethod
    def assign_role_menus(role_id, menu_ids, current_user=None, role=None):
        """重建角色菜单权限映射。"""
        role = role or RoleService.get_role_by_id(role_id)
        if not role:
            return False, '角色不存在'

        for menu_id in menu_ids:
            menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
            if not menu:
                return False, f'菜单ID {menu_id} 不存在'
            if (
                role.is_factory_role
                and menu.permission
                and menu.permission.startswith(FACTORY_ROLE_FORBIDDEN_PERMISSION_PREFIXES)
            ):
                return False, f'工厂角色不允许绑定平台级权限 {menu.permission}'

        db.session.execute(role_menu.delete().where(role_menu.c.role_id == role_id))
        for menu_id in menu_ids:
            db.session.execute(role_menu.insert().values(role_id=role_id, menu_id=menu_id))
        db.session.commit()
        RoleService.clear_permission_cache()
        return True, None

    @staticmethod
    def get_role_users(role_id):
        """查询拥有该角色的用户 ID 列表。"""
        user_ids = db.session.query(UserFactoryRole.user_id).filter_by(role_id=role_id, is_deleted=0).all()
        return [user_id for user_id, in user_ids]
