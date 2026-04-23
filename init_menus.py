from app import create_app
from app.extensions import db
from app.models.system.menu import Menu

app = create_app()

with app.app_context():
    # 初始化菜单数据
    menus = [
        # ========== 系统管理（目录） ==========
        {'parent_id': 0, 'name': '系统管理', 'path': '/system', 'component': 'Layout', 'type': 0, 'icon': 'system',
         'sort_order': 1, 'permission': ''},

        # 用户管理
        {'parent_id': 1, 'name': '用户管理', 'path': '/system/user', 'component': 'system/user/index', 'type': 1,
         'icon': 'user', 'sort_order': 1, 'permission': 'system:user:list'},
        {'parent_id': 2, 'name': '用户查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1,
         'permission': 'system:user:query'},
        {'parent_id': 2, 'name': '用户新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2,
         'permission': 'system:user:add'},
        {'parent_id': 2, 'name': '用户编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3,
         'permission': 'system:user:edit'},
        {'parent_id': 2, 'name': '用户删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4,
         'permission': 'system:user:delete'},

        # 角色管理
        {'parent_id': 1, 'name': '角色管理', 'path': '/system/role', 'component': 'system/role/index', 'type': 1,
         'icon': 'role', 'sort_order': 2, 'permission': 'system:role:list'},
        {'parent_id': 7, 'name': '角色查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1,
         'permission': 'system:role:query'},
        {'parent_id': 7, 'name': '角色新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2,
         'permission': 'system:role:add'},
        {'parent_id': 7, 'name': '角色编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3,
         'permission': 'system:role:edit'},
        {'parent_id': 7, 'name': '角色删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4,
         'permission': 'system:role:delete'},

        # 菜单管理
        {'parent_id': 1, 'name': '菜单管理', 'path': '/system/menu', 'component': 'system/menu/index', 'type': 1,
         'icon': 'menu', 'sort_order': 3, 'permission': 'system:menu:list'},
        {'parent_id': 12, 'name': '菜单查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1,
         'permission': 'system:menu:query'},
        {'parent_id': 12, 'name': '菜单新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2,
         'permission': 'system:menu:add'},
        {'parent_id': 12, 'name': '菜单编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3,
         'permission': 'system:menu:edit'},
        {'parent_id': 12, 'name': '菜单删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4,
         'permission': 'system:menu:delete'},

        # 工厂管理
        {'parent_id': 1, 'name': '工厂管理', 'path': '/system/factory', 'component': 'system/factory/index', 'type': 1,
         'icon': 'factory', 'sort_order': 4, 'permission': 'system:factory:list'},
        {'parent_id': 17, 'name': '工厂查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1,
         'permission': 'system:factory:query'},
        {'parent_id': 17, 'name': '工厂新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2,
         'permission': 'system:factory:add'},
        {'parent_id': 17, 'name': '工厂编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3,
         'permission': 'system:factory:edit'},
        {'parent_id': 17, 'name': '工厂删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4,
         'permission': 'system:factory:delete'},

        # 日志管理
        {'parent_id': 1, 'name': '日志管理', 'path': '/system/log', 'component': 'system/log/index', 'type': 1,
         'icon': 'log', 'sort_order': 5, 'permission': 'system:log:list'},
        {'parent_id': 22, 'name': '操作日志', 'path': '/system/log/operation', 'component': 'system/log/operation',
         'type': 1, 'icon': '', 'sort_order': 1, 'permission': 'system:log:operation'},
        {'parent_id': 22, 'name': '登录日志', 'path': '/system/log/login', 'component': 'system/log/login', 'type': 1,
         'icon': '', 'sort_order': 2, 'permission': 'system:log:login'},

        # 服务监控
        {'parent_id': 1, 'name': '服务监控', 'path': '/system/monitor', 'component': 'system/monitor/index', 'type': 1,
         'icon': 'monitor', 'sort_order': 6, 'permission': 'system:monitor:view'},

        # ========== 基础数据（目录） ==========
        {'parent_id': 0, 'name': '基础数据', 'path': '/base', 'component': 'Layout', 'type': 0, 'icon': 'database',
         'sort_order': 2, 'permission': ''},

        # 尺码管理
        {'parent_id': 26, 'name': '尺码管理', 'path': '/base/size', 'component': 'base/size/index', 'type': 1,
         'icon': 'size', 'sort_order': 1, 'permission': 'base:size:list'},

        # 分类管理
        {'parent_id': 26, 'name': '分类管理', 'path': '/base/category', 'component': 'base/category/index', 'type': 1,
         'icon': 'category', 'sort_order': 2, 'permission': 'base:category:list'},

        # 颜色管理
        {'parent_id': 26, 'name': '颜色管理', 'path': '/base/color', 'component': 'base/color/index', 'type': 1,
         'icon': 'color', 'sort_order': 3, 'permission': 'base:color:list'},

        # ========== 业务管理（目录） ==========
        {'parent_id': 0, 'name': '业务管理', 'path': '/business', 'component': 'Layout', 'type': 0, 'icon': 'business',
         'sort_order': 3, 'permission': ''},

        # 款号管理
        {'parent_id': 30, 'name': '款号管理', 'path': '/business/style', 'component': 'business/style/index', 'type': 1,
         'icon': 'style', 'sort_order': 1, 'permission': 'business:style:list'},
        {'parent_id': 31, 'name': '款号查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1,
         'permission': 'business:style:query'},
        {'parent_id': 31, 'name': '款号新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2,
         'permission': 'business:style:add'},
        {'parent_id': 31, 'name': '款号编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3,
         'permission': 'business:style:edit'},
        {'parent_id': 31, 'name': '款号删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4,
         'permission': 'business:style:delete'},

        # ========== 个人中心 ==========
        {'parent_id': 0, 'name': '个人中心', 'path': '/profile', 'component': 'Layout', 'type': 0, 'icon': 'profile',
         'sort_order': 99, 'permission': ''},
        {'parent_id': 36, 'name': '个人信息', 'path': '/profile/info', 'component': 'profile/info/index', 'type': 1,
         'icon': 'info', 'sort_order': 1, 'permission': ''},
        {'parent_id': 36, 'name': '修改密码', 'path': '/profile/password', 'component': 'profile/password/index',
         'type': 1, 'icon': 'password', 'sort_order': 2, 'permission': ''},
    ]

    for menu_data in menus:
        existing = Menu.query.filter_by(name=menu_data['name'], is_deleted=0).first()
        if not existing:
            menu = Menu(**menu_data)
            db.session.add(menu)
            print(f'✅ 菜单创建成功: {menu_data["name"]}')
        else:
            print(f'⚠️ 菜单已存在: {menu_data["name"]}')

    db.session.commit()
    print('\n🎉 菜单数据初始化完成！')
