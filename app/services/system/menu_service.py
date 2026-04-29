"""菜单管理服务"""
from app.extensions import db
from app.models.system.menu import Menu
from app.models.system.role import role_menu
from app.services.base.base_service import BaseService


class MenuService(BaseService):
    """菜单管理服务"""

    @staticmethod
    def get_menu_by_id(menu_id):
        """根据ID获取菜单"""
        return Menu.query.filter_by(id=menu_id, is_deleted=0).first()

    @staticmethod
    def get_menu_list(filters):
        """
        获取菜单列表
        filters: type, status
        """
        query = Menu.query.filter_by(is_deleted=0)

        menu_type = filters.get('type')
        status = filters.get('status')

        if menu_type is not None:
            query = query.filter_by(type=menu_type)
        if status is not None:
            query = query.filter_by(status=status)

        return query.order_by(Menu.sort_order).all()

    @staticmethod
    def build_menu_tree(menus, parent_id=0, menu_schema=None):
        """构建菜单树"""
        tree = []
        for menu in menus:
            if menu.parent_id == parent_id:
                children = MenuService.build_menu_tree(menus, menu.id, menu_schema)
                if menu_schema:
                    menu_dict = menu_schema.dump(menu)
                else:
                    menu_dict = {
                        'id': menu.id,
                        'parent_id': menu.parent_id,
                        'name': menu.name,
                        'path': menu.path,
                        'component': menu.component,
                        'permission': menu.permission,
                        'type': menu.type,
                        'icon': menu.icon,
                        'sort_order': menu.sort_order,
                        'status': menu.status,
                        'create_time': menu.create_time.isoformat() if menu.create_time else None,
                        'update_time': menu.update_time.isoformat() if menu.update_time else None
                    }
                if children:
                    menu_dict['children'] = children
                tree.append(menu_dict)
        return tree

    @staticmethod
    def create_menu(data):
        """创建菜单"""
        # 验证父菜单
        if data.get('parent_id', 0) != 0:
            parent_menu = MenuService.get_menu_by_id(data['parent_id'])
            if not parent_menu:
                return None, '父菜单不存在'

        menu = Menu(
            parent_id=data.get('parent_id', 0),
            name=data['name'],
            path=data.get('path', ''),
            component=data.get('component', ''),
            permission=data.get('permission', ''),
            type=data['type'],
            icon=data.get('icon', ''),
            sort_order=data.get('sort_order', 0),
            status=1
        )
        menu.save()

        return menu, None

    @staticmethod
    def update_menu(menu, data):
        """更新菜单"""
        if 'parent_id' in data:
            if data['parent_id'] != 0:
                parent_menu = MenuService.get_menu_by_id(data['parent_id'])
                if not parent_menu:
                    return None, '父菜单不存在'
                if data['parent_id'] == menu.id:
                    return None, '不能将父菜单设为自己'
            menu.parent_id = data['parent_id']

        if 'name' in data:
            menu.name = data['name']
        if 'path' in data:
            menu.path = data['path']
        if 'component' in data:
            menu.component = data['component']
        if 'permission' in data:
            menu.permission = data['permission']
        if 'type' in data:
            menu.type = data['type']
        if 'icon' in data:
            menu.icon = data['icon']
        if 'sort_order' in data:
            menu.sort_order = data['sort_order']
        if 'status' in data:
            menu.status = data['status']

        menu.save()
        return menu, None

    @staticmethod
    def delete_menu(menu):
        """删除菜单（软删除）"""
        # 检查是否有子菜单
        children_count = Menu.query.filter_by(parent_id=menu.id, is_deleted=0).count()
        if children_count > 0:
            return False, f'请先删除子菜单（共 {children_count} 个）'

        # 检查是否有角色关联此菜单
        role_count = db.session.query(role_menu).filter_by(menu_id=menu.id).count()
        if role_count > 0:
            return False, f'有 {role_count} 个角色关联此菜单，无法删除'

        menu.is_deleted = 1
        menu.save()
        return True, None

    @staticmethod
    def get_user_menus(user, factory_id=None):
        """
        获取用户菜单（用于前端渲染）
        返回菜单树形结构
        """
        # 公司内部人员：返回所有菜单
        if user.is_admin == 1:
            menus = Menu.query.filter_by(status=1, is_deleted=0).order_by(Menu.sort_order).all()
            return MenuService.build_menu_tree(menus)

        # 工厂员工/客户/协作用户：根据角色返回菜单
        if factory_id:
            from app.models.system.user_factory_role import UserFactoryRole
            from app.models.system.role import role_menu

            # 获取用户在当前工厂的角色
            role_ids = db.session.query(UserFactoryRole.role_id).filter_by(
                user_id=user.id, factory_id=factory_id, is_deleted=0
            ).all()
            role_ids = [r[0] for r in role_ids]

            if role_ids:
                menu_ids = db.session.query(role_menu.c.menu_id).filter(
                    role_menu.c.role_id.in_(role_ids)
                ).all()
                menu_ids = list(set([m[0] for m in menu_ids]))
                menus = Menu.query.filter(
                    Menu.id.in_(menu_ids),
                    Menu.status == 1,
                    Menu.is_deleted == 0
                ).order_by(Menu.sort_order).all()
            else:
                menus = []
        else:
            menus = []

        return MenuService.build_menu_tree(menus)

    @staticmethod
    def check_admin_permission(current_user):
        """检查管理员权限"""
        if not current_user or current_user.is_admin != 1:
            return False, '无权限操作菜单'
        return True, None
