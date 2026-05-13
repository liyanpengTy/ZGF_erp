"""菜单管理服务。"""

from app.extensions import db
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService


class MenuService(BaseService):
    """菜单管理服务。"""

    @staticmethod
    def get_menu_by_id(menu_id):
        """根据 ID 获取菜单。"""
        return Menu.query.filter_by(id=menu_id, is_deleted=0).first()

    @staticmethod
    def get_menu_list(filters):
        """按筛选条件查询菜单列表。"""
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
        """将平铺菜单转换成树形结构。"""
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
        """创建菜单。"""
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
        """更新菜单。"""
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
        """删除菜单前校验子菜单和角色绑定。"""
        children_count = Menu.query.filter_by(parent_id=menu.id, is_deleted=0).count()
        if children_count > 0:
            return False, f'请先删除子菜单（共 {children_count} 个）'

        role_count = db.session.query(role_menu).filter_by(menu_id=menu.id).count()
        if role_count > 0:
            return False, f'有 {role_count} 个角色关联此菜单，无法删除'

        menu.is_deleted = 1
        menu.save()
        return True, None

    @staticmethod
    def get_role_menu_ids(role_ids):
        """汇总角色关联的菜单 ID。"""
        if not role_ids:
            return []
        menu_rows = db.session.query(role_menu.c.menu_id).filter(role_menu.c.role_id.in_(role_ids)).all()
        return list({menu_id for menu_id, in menu_rows})

    @staticmethod
    def get_user_menus(user, factory_id=None):
        """按当前身份和工厂上下文返回前端菜单树。"""
        if user.is_platform_admin:
            menus = Menu.query.filter_by(status=1, is_deleted=0).order_by(Menu.sort_order).all()
            return MenuService.build_menu_tree(menus)

        role_query = UserFactoryRole.query.join(Role, Role.id == UserFactoryRole.role_id).filter(
            UserFactoryRole.user_id == user.id,
            UserFactoryRole.is_deleted == 0,
            Role.status == 1,
            Role.is_deleted == 0
        )

        if user.is_platform_staff:
            role_query = role_query.filter(
                UserFactoryRole.factory_id == 0,
                Role.factory_id == 0
            )
        else:
            if not factory_id:
                return []
            role_query = role_query.filter(UserFactoryRole.factory_id == factory_id)

        role_ids = [record.role_id for record in role_query.all()]
        menu_ids = MenuService.get_role_menu_ids(role_ids)
        if not menu_ids:
            return []

        menus = Menu.query.filter(
            Menu.id.in_(menu_ids),
            Menu.status == 1,
            Menu.is_deleted == 0
        ).order_by(Menu.sort_order).all()
        return MenuService.build_menu_tree(menus)

    @staticmethod
    def check_admin_permission(current_user):
        """校验菜单管理是否允许访问，仅平台管理员可维护。"""
        if not current_user or not current_user.is_platform_admin:
            return False, '无权限操作菜单'
        return True, None
