"""角色管理服务"""
from app.extensions import db
from app.models.system.role import Role, role_menu
from app.models.system.menu import Menu
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService


class RoleService(BaseService):
    """角色管理服务"""

    @staticmethod
    def get_role_by_id(role_id):
        """根据ID获取角色"""
        return Role.query.filter_by(id=role_id, is_deleted=0).first()

    @staticmethod
    def get_role_by_code(factory_id, code):
        """根据工厂ID和编码获取角色"""
        return Role.query.filter_by(factory_id=factory_id, code=code, is_deleted=0).first()

    @staticmethod
    def get_role_by_name(factory_id, name):
        """根据工厂ID和名称获取角色"""
        return Role.query.filter_by(factory_id=factory_id, name=name, is_deleted=0).first()

    @staticmethod
    def get_role_list(current_user, filters):
        """
        获取角色列表
        filters: page, page_size, name, status, factory_id
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        # 公司内部人员：可以查看平台角色 + 指定工厂的角色
        if current_user.is_admin == 1:
            factory_id = filters.get('factory_id')
            if not factory_id:
                return None, '请指定工厂ID'
            query = Role.query.filter(
                (Role.factory_id == 0) | (Role.factory_id == factory_id),
                Role.is_deleted == 0
            )
        else:
            # 普通用户：只能查看自己工厂的角色
            from app.models.system.user_factory import UserFactory
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id, status=1, is_deleted=0
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
        """创建角色"""
        # 检查编码是否已存在
        existing_code = RoleService.get_role_by_code(factory_id, data['code'])
        if existing_code:
            return None, '角色编码已存在'

        # 检查名称是否已存在
        existing_name = RoleService.get_role_by_name(factory_id, data['name'])
        if existing_name:
            return None, '角色名称已存在'

        role = Role(
            factory_id=factory_id,
            name=data['name'],
            code=data['code'],
            description=data.get('description', ''),
            sort_order=data.get('sort_order', 0),
            status=1
        )
        role.save()

        return role, None

    @staticmethod
    def update_role(role, data):
        """更新角色"""
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

        role.save()
        return role, None

    @staticmethod
    def delete_role(role):
        """删除角色（软删除）"""
        # 检查是否有用户关联此角色
        user_role_count = UserFactoryRole.query.filter_by(
            role_id=role.id, is_deleted=0
        ).count()
        if user_role_count > 0:
            return False, f'有 {user_role_count} 个用户关联此角色，无法删除'

        role.is_deleted = 1
        role.save()
        return True, None

    @staticmethod
    def get_role_menu_ids(role_id):
        """获取角色的菜单权限ID列表"""
        menu_ids = db.session.query(role_menu.c.menu_id).filter_by(role_id=role_id).all()
        return [m[0] for m in menu_ids]

    @staticmethod
    def assign_role_menus(role_id, menu_ids):
        """分配菜单权限给角色"""
        # 验证菜单是否存在
        for menu_id in menu_ids:
            menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
            if not menu:
                return False, f'菜单ID {menu_id} 不存在'

        # 删除原有权限
        db.session.execute(role_menu.delete().where(role_menu.c.role_id == role_id))

        # 添加新权限
        for menu_id in menu_ids:
            db.session.execute(role_menu.insert().values(role_id=role_id, menu_id=menu_id))

        db.session.commit()
        return True, None

    @staticmethod
    def get_role_users(role_id):
        """获取拥有该角色的用户列表"""
        user_ids = db.session.query(UserFactoryRole.user_id).filter_by(
            role_id=role_id, is_deleted=0
        ).all()
        return [u[0] for u in user_ids]

    @staticmethod
    def verify_role_permission(current_user, role):
        """验证用户是否有权限操作该角色"""
        if current_user.is_admin == 1:
            return True

        from app.models.system.user_factory import UserFactory
        user_factory = UserFactory.query.filter_by(
            user_id=current_user.id, factory_id=role.factory_id, status=1, is_deleted=0
        ).first()

        return user_factory is not None
