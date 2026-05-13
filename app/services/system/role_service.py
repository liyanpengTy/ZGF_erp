"""角色管理服务。"""

from app.constants.identity import ROLE_DATA_SCOPE_OWN_RELATED
from app.extensions import db
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService


class RoleService(BaseService):
    """角色管理服务。"""

    @staticmethod
    def get_role_by_id(role_id):
        """按主键查询角色。"""
        return Role.query.filter_by(id=role_id, is_deleted=0).first()

    @staticmethod
    def get_role_by_code(factory_id, code):
        """按工厂上下文和编码查询角色。"""
        return Role.query.filter_by(factory_id=factory_id, code=code, is_deleted=0).first()

    @staticmethod
    def get_role_by_name(factory_id, name):
        """按工厂上下文和名称查询角色。"""
        return Role.query.filter_by(factory_id=factory_id, name=name, is_deleted=0).first()

    @staticmethod
    def get_role_list(current_user, filters):
        """按当前用户权限范围分页查询角色列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        if current_user.is_internal_user:
            factory_id = filters.get('factory_id')
            if not factory_id:
                return None, '请指定工厂ID'
            query = Role.query.filter(
                (Role.factory_id == 0) | (Role.factory_id == factory_id),
                Role.is_deleted == 0
            )
        else:
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id,
                status=1,
                is_deleted=0
            ).first()
            if not user_factory:
                return None, '无权限查看角色'
            query = Role.query.filter_by(factory_id=user_factory.factory_id, is_deleted=0)

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
    def create_role(data, factory_id):
        """在指定工厂下创建角色，并保存数据范围元信息。"""
        existing_code = RoleService.get_role_by_code(factory_id, data['code'])
        if existing_code:
            return None, '角色编码已存在'

        existing_name = RoleService.get_role_by_name(factory_id, data['name'])
        if existing_name:
            return None, '角色名称已存在'

        role = Role(
            factory_id=factory_id,
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
            existing = RoleService.get_role_by_name(role.factory_id, data['name'])
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
    def assign_role_menus(role_id, menu_ids):
        """重建角色菜单权限映射。"""
        for menu_id in menu_ids:
            menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
            if not menu:
                return False, f'菜单ID {menu_id} 不存在'

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

        user_factory = UserFactory.query.filter_by(
            user_id=current_user.id,
            factory_id=role.factory_id,
            status=1,
            is_deleted=0
        ).first()
        return user_factory is not None
