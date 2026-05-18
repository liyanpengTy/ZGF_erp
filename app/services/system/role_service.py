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


FACTORY_ROLE_FORBIDDEN_PERMISSION_PREFIXES = (
    'system.',
)


class RoleService(BaseService):
    """角色管理服务。"""

    @staticmethod
    def has_factory_admin_permission(user, factory_id):
        """判断用户是否拥有指定工厂的管理员能力。"""
        if not user or user.is_internal_user or not factory_id:
            return False

        owner_relation = UserFactory.query.filter_by(
            user_id=user.id,
            factory_id=factory_id,
            relation_type=RELATION_TYPE_OWNER,
            status=1,
            is_deleted=0
        ).first()
        if owner_relation:
            return True

        admin_role = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
            UserFactoryRole.user_id == user.id,
            UserFactoryRole.factory_id == factory_id,
            UserFactoryRole.is_deleted == 0,
            Role.scope_type == ROLE_SCOPE_FACTORY,
            Role.scope_id == factory_id,
            Role.is_factory_admin == 1,
            Role.status == 1,
            Role.is_deleted == 0
        ).first()
        return admin_role is not None

    @staticmethod
    def can_manage_role(current_user, role, current_factory_id=None):
        """校验当前用户是否可以维护目标角色。"""
        if not current_user or not role:
            return False
        if current_user.is_platform_admin:
            return True
        if not role.is_factory_role:
            return False
        if current_factory_id and role.scope_id != current_factory_id:
            return False
        return RoleService.has_factory_admin_permission(current_user, role.scope_id)

    @staticmethod
    def normalize_scope(scope_type, scope_id):
        """归一化角色归属范围，避免平台角色误带工厂主键。"""
        if scope_type == ROLE_SCOPE_PLATFORM:
            return ROLE_SCOPE_PLATFORM, 0
        if scope_type == ROLE_SCOPE_FACTORY:
            if not scope_id:
                return None, None
            return ROLE_SCOPE_FACTORY, scope_id
        return scope_type, scope_id or 0

    @staticmethod
    def get_role_by_id(role_id):
        """按主键查询角色。"""
        return Role.query.filter_by(id=role_id, is_deleted=0).first()

    @staticmethod
    def get_role_by_code(scope_type, scope_id, code):
        """按角色归属范围和编码查询角色。"""
        scope_type, scope_id = RoleService.normalize_scope(scope_type, scope_id)
        return Role.query.filter_by(scope_type=scope_type, scope_id=scope_id, code=code, is_deleted=0).first()

    @staticmethod
    def get_role_by_name(scope_type, scope_id, name):
        """按角色归属范围和名称查询角色。"""
        scope_type, scope_id = RoleService.normalize_scope(scope_type, scope_id)
        return Role.query.filter_by(scope_type=scope_type, scope_id=scope_id, name=name, is_deleted=0).first()

    @staticmethod
    def get_role_list(current_user, filters, current_factory_id=None):
        """按当前用户权限范围分页查询角色列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')
        scope_type = filters.get('scope_type')
        scope_id = filters.get('scope_id')

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
        else:
            if not current_factory_id:
                return None, '请先选择工厂上下文'
            if not RoleService.has_factory_admin_permission(current_user, current_factory_id):
                return None, '无权限查看角色'
            query = Role.query.filter_by(
                scope_type=ROLE_SCOPE_FACTORY,
                scope_id=current_factory_id,
                is_deleted=0,
            )

        if name:
            query = query.filter(Role.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Role.sort_order).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }, None

    @staticmethod
    def create_role(data):
        """按归属范围创建角色，并保存数据范围元信息。"""
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
            status=1
        )
        role.save()
        return role, None

    @staticmethod
    def update_role(role, data):
        """更新角色名称、排序、数据范围等核心配置。"""
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
        return role, None

    @staticmethod
    def delete_role(role):
        """删除角色前先确保没有用户仍在使用该角色。"""
        user_role_count = UserFactoryRole.query.filter_by(role_id=role.id, is_deleted=0).count()
        if user_role_count > 0:
            return False, f'有 {user_role_count} 个用户关联此角色，无法删除'

        role.is_deleted = 1
        role.save()
        return True, None

    @staticmethod
    def get_role_menu_ids(role_id):
        """查询角色已绑定的菜单 ID。"""
        menu_ids = db.session.query(role_menu.c.menu_id).filter_by(role_id=role_id).all()
        return [menu_id for menu_id, in menu_ids]

    @staticmethod
    def assign_role_menus(role_id, menu_ids, current_user=None, role=None):
        """重建角色菜单权限映射；工厂管理员不能给工厂角色绑定平台级权限。"""
        role = role or RoleService.get_role_by_id(role_id)
        if not role:
            return False, '角色不存在'

        for menu_id in menu_ids:
            menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
            if not menu:
                return False, f'菜单ID {menu_id} 不存在'
            if (
                current_user
                and not current_user.is_platform_admin
                and role.is_factory_role
                and menu.permission
                and menu.permission.startswith(FACTORY_ROLE_FORBIDDEN_PERMISSION_PREFIXES)
            ):
                return False, f'工厂角色不允许绑定平台级权限 {menu.permission}'

        db.session.execute(role_menu.delete().where(role_menu.c.role_id == role_id))

        for menu_id in menu_ids:
            db.session.execute(role_menu.insert().values(role_id=role_id, menu_id=menu_id))

        db.session.commit()
        return True, None

    @staticmethod
    def get_role_users(role_id):
        """查询拥有该角色的用户 ID 列表。"""
        user_ids = db.session.query(UserFactoryRole.user_id).filter_by(role_id=role_id, is_deleted=0).all()
        return [user_id for user_id, in user_ids]

    @staticmethod
    def verify_role_permission(current_user, role):
        """校验当前用户是否可以访问该角色。"""
        if current_user.is_internal_user:
            return True
        if not role.is_factory_role:
            return False

        user_factory = UserFactory.query.filter_by(
            user_id=current_user.id,
            factory_id=role.scope_id,
            status=1,
            is_deleted=0
        ).first()
        return user_factory is not None
