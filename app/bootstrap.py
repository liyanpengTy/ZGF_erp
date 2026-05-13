"""初始化与种子数据工具。"""

from datetime import date, timedelta

from sqlalchemy import or_

from app.constants.identity import PLATFORM_IDENTITY_ADMIN, PLATFORM_IDENTITY_EXTERNAL
from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.menu import Menu
from app.models.system.reward_config import RewardConfig
from app.models.system.role import Role, role_menu
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole


MENU_SEEDS = [
    {'key': 'system_root', 'parent_key': None, 'name': '系统管理', 'path': '/system', 'component': 'Layout', 'type': 0, 'icon': 'system', 'sort_order': 1, 'permission': ''},
    {'key': 'system_users', 'parent_key': 'system_root', 'name': '用户管理', 'path': '/system/user', 'component': 'system/user/index', 'type': 1, 'icon': 'user', 'sort_order': 1, 'permission': 'system:user:list'},
    {'key': 'system_user_query', 'parent_key': 'system_users', 'name': '用户查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'system:user:query'},
    {'key': 'system_user_add', 'parent_key': 'system_users', 'name': '用户新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2, 'permission': 'system:user:add'},
    {'key': 'system_user_edit', 'parent_key': 'system_users', 'name': '用户编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3, 'permission': 'system:user:edit'},
    {'key': 'system_user_delete', 'parent_key': 'system_users', 'name': '用户删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4, 'permission': 'system:user:delete'},
    {'key': 'system_roles', 'parent_key': 'system_root', 'name': '角色管理', 'path': '/system/role', 'component': 'system/role/index', 'type': 1, 'icon': 'role', 'sort_order': 2, 'permission': 'system:role:list'},
    {'key': 'system_role_query', 'parent_key': 'system_roles', 'name': '角色查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'system:role:query'},
    {'key': 'system_role_add', 'parent_key': 'system_roles', 'name': '角色新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2, 'permission': 'system:role:add'},
    {'key': 'system_role_edit', 'parent_key': 'system_roles', 'name': '角色编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3, 'permission': 'system:role:edit'},
    {'key': 'system_role_delete', 'parent_key': 'system_roles', 'name': '角色删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4, 'permission': 'system:role:delete'},
    {'key': 'system_menus', 'parent_key': 'system_root', 'name': '菜单管理', 'path': '/system/menu', 'component': 'system/menu/index', 'type': 1, 'icon': 'menu', 'sort_order': 3, 'permission': 'system:menu:list'},
    {'key': 'system_menu_query', 'parent_key': 'system_menus', 'name': '菜单查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'system:menu:query'},
    {'key': 'system_menu_add', 'parent_key': 'system_menus', 'name': '菜单新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2, 'permission': 'system:menu:add'},
    {'key': 'system_menu_edit', 'parent_key': 'system_menus', 'name': '菜单编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3, 'permission': 'system:menu:edit'},
    {'key': 'system_menu_delete', 'parent_key': 'system_menus', 'name': '菜单删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4, 'permission': 'system:menu:delete'},
    {'key': 'system_factories', 'parent_key': 'system_root', 'name': '工厂管理', 'path': '/system/factory', 'component': 'system/factory/index', 'type': 1, 'icon': 'factory', 'sort_order': 4, 'permission': 'system:factory:list'},
    {'key': 'system_factory_query', 'parent_key': 'system_factories', 'name': '工厂查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'system:factory:query'},
    {'key': 'system_factory_add', 'parent_key': 'system_factories', 'name': '工厂新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2, 'permission': 'system:factory:add'},
    {'key': 'system_factory_edit', 'parent_key': 'system_factories', 'name': '工厂编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3, 'permission': 'system:factory:edit'},
    {'key': 'system_factory_delete', 'parent_key': 'system_factories', 'name': '工厂删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4, 'permission': 'system:factory:delete'},
    {'key': 'system_logs', 'parent_key': 'system_root', 'name': '日志管理', 'path': '/system/log', 'component': 'system/log/index', 'type': 1, 'icon': 'log', 'sort_order': 5, 'permission': 'system:log:list'},
    {'key': 'system_log_operation', 'parent_key': 'system_logs', 'name': '操作日志', 'path': '/system/log/operation', 'component': 'system/log/operation', 'type': 1, 'icon': '', 'sort_order': 1, 'permission': 'system:log:operation'},
    {'key': 'system_log_login', 'parent_key': 'system_logs', 'name': '登录日志', 'path': '/system/log/login', 'component': 'system/log/login', 'type': 1, 'icon': '', 'sort_order': 2, 'permission': 'system:log:login'},
    {'key': 'system_monitor', 'parent_key': 'system_root', 'name': '服务监控', 'path': '/system/monitor', 'component': 'system/monitor/index', 'type': 1, 'icon': 'monitor', 'sort_order': 6, 'permission': 'system:monitor:view'},
    {'key': 'system_rewards', 'parent_key': 'system_root', 'name': '奖励管理', 'path': '/system/reward', 'component': 'system/reward/index', 'type': 1, 'icon': 'reward', 'sort_order': 7, 'permission': 'system:reward:view'},
    {'key': 'system_reward_distribute', 'parent_key': 'system_rewards', 'name': '奖励发放', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'system:reward:distribute'},
    {'key': 'system_employee_wage', 'parent_key': 'system_root', 'name': '员工计酬', 'path': '/system/employee-wage', 'component': 'system/employee-wage/index', 'type': 1, 'icon': 'money', 'sort_order': 8, 'permission': 'system:employee_wage:view'},
    {'key': 'system_employee_wage_add', 'parent_key': 'system_employee_wage', 'name': '计酬新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'system:employee_wage:add'},
    {'key': 'system_employee_wage_edit', 'parent_key': 'system_employee_wage', 'name': '计酬编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2, 'permission': 'system:employee_wage:edit'},
    {'key': 'system_employee_wage_delete', 'parent_key': 'system_employee_wage', 'name': '计酬删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3, 'permission': 'system:employee_wage:delete'},
    {'key': 'base_root', 'parent_key': None, 'name': '基础数据', 'path': '/base', 'component': 'Layout', 'type': 0, 'icon': 'database', 'sort_order': 2, 'permission': ''},
    {'key': 'base_sizes', 'parent_key': 'base_root', 'name': '尺码管理', 'path': '/base/size', 'component': 'base/size/index', 'type': 1, 'icon': 'size', 'sort_order': 1, 'permission': 'base:size:list'},
    {'key': 'base_categories', 'parent_key': 'base_root', 'name': '分类管理', 'path': '/base/category', 'component': 'base/category/index', 'type': 1, 'icon': 'category', 'sort_order': 2, 'permission': 'base:category:list'},
    {'key': 'base_colors', 'parent_key': 'base_root', 'name': '颜色管理', 'path': '/base/color', 'component': 'base/color/index', 'type': 1, 'icon': 'color', 'sort_order': 3, 'permission': 'base:color:list'},
    {'key': 'business_root', 'parent_key': None, 'name': '业务管理', 'path': '/business', 'component': 'Layout', 'type': 0, 'icon': 'business', 'sort_order': 3, 'permission': ''},
    {'key': 'business_styles', 'parent_key': 'business_root', 'name': '款号管理', 'path': '/business/style', 'component': 'business/style/index', 'type': 1, 'icon': 'style', 'sort_order': 1, 'permission': 'business:style:list'},
    {'key': 'business_style_query', 'parent_key': 'business_styles', 'name': '款号查询', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 1, 'permission': 'business:style:query'},
    {'key': 'business_style_add', 'parent_key': 'business_styles', 'name': '款号新增', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 2, 'permission': 'business:style:add'},
    {'key': 'business_style_edit', 'parent_key': 'business_styles', 'name': '款号编辑', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 3, 'permission': 'business:style:edit'},
    {'key': 'business_style_delete', 'parent_key': 'business_styles', 'name': '款号删除', 'path': '', 'component': '', 'type': 2, 'icon': '', 'sort_order': 4, 'permission': 'business:style:delete'},
    {'key': 'business_processes', 'parent_key': 'business_root', 'name': '工序管理', 'path': '/business/processes', 'component': 'business/processes/index', 'type': 1, 'icon': 'process', 'sort_order': 2, 'permission': 'business:process:list'},
    {'key': 'business_orders', 'parent_key': 'business_root', 'name': '订单管理', 'path': '/business/orders', 'component': 'business/orders/index', 'type': 1, 'icon': 'order', 'sort_order': 3, 'permission': 'business:order:list'},
    {'key': 'profile_root', 'parent_key': None, 'name': '个人中心', 'path': '/profile', 'component': 'Layout', 'type': 0, 'icon': 'profile', 'sort_order': 99, 'permission': ''},
    {'key': 'profile_info', 'parent_key': 'profile_root', 'name': '个人信息', 'path': '/profile/info', 'component': 'profile/info/index', 'type': 1, 'icon': 'info', 'sort_order': 1, 'permission': ''},
    {'key': 'profile_password', 'parent_key': 'profile_root', 'name': '修改密码', 'path': '/profile/password', 'component': 'profile/password/index', 'type': 1, 'icon': 'password', 'sort_order': 2, 'permission': ''},
]

REWARD_CONFIG_SEEDS = [
    {'name': '邀请 5 人工厂延期', 'rule_type': 'invite_count', 'threshold': 5, 'reward_object': 'factory', 'reward_type': 'extend', 'reward_value': 365, 'is_active': 1, 'remark': '邀请满 5 人，工厂服务期延长一年'},
    {'name': '邀请 5 人现金奖励', 'rule_type': 'invite_count', 'threshold': 5, 'reward_object': 'personal', 'reward_type': 'cash', 'reward_value': 400, 'is_active': 1, 'remark': '邀请满 5 人，个人现金奖励 400 元'},
    {'name': '邀请 10 人工厂延期', 'rule_type': 'invite_count', 'threshold': 10, 'reward_object': 'factory', 'reward_type': 'extend', 'reward_value': 730, 'is_active': 1, 'remark': '邀请满 10 人，工厂服务期延长两年'},
]


def create_tables():
    """创建数据库表。"""
    db.create_all()


def _ensure_user(username, nickname, platform_identity=PLATFORM_IDENTITY_EXTERNAL, password='123456'):
    """确保指定用户名存在，不存在则创建。"""
    user = User.query.filter_by(username=username, is_deleted=0).first()
    if user:
        return user, False

    user = User(
        username=username,
        password=bcrypt.generate_password_hash(password).decode('utf-8'),
        nickname=nickname,
        platform_identity=platform_identity,
        status=1,
    )
    user.save()
    return user, True


def _ensure_user_factory(user_id, factory_id, relation_type, collaborator_type=None):
    """确保用户与工厂的关系存在。"""
    record = UserFactory.query.filter_by(
        user_id=user_id,
        factory_id=factory_id,
        relation_type=relation_type,
        is_deleted=0
    ).first()
    if record:
        return record, False

    record = UserFactory(
        user_id=user_id,
        factory_id=factory_id,
        relation_type=relation_type,
        collaborator_type=collaborator_type,
        status=1,
        entry_date=date.today(),
    )
    record.save()
    return record, True


def _ensure_role(factory_id, code, name, description, sort_order, data_scope='own_related', is_factory_admin=0):
    """确保角色存在。"""
    role = Role.query.filter_by(factory_id=factory_id, code=code, is_deleted=0).first()
    if role:
        return role, False

    role = Role(
        factory_id=factory_id,
        code=code,
        name=name,
        description=description,
        status=1,
        sort_order=sort_order,
        data_scope=data_scope,
        is_factory_admin=is_factory_admin,
    )
    role.save()
    return role, True


def _ensure_user_role(user_id, factory_id, role_id):
    """确保用户角色关系存在。"""
    record = UserFactoryRole.query.filter_by(
        user_id=user_id,
        factory_id=factory_id,
        role_id=role_id,
        is_deleted=0
    ).first()
    if record:
        return record, False

    record = UserFactoryRole(user_id=user_id, factory_id=factory_id, role_id=role_id)
    record.save()
    return record, True


def seed_admin_user():
    """创建平台管理员账号。"""
    return _ensure_user('admin', '平台管理员', PLATFORM_IDENTITY_ADMIN)


def seed_demo_factory():
    """创建演示工厂及其基础账号关系。"""
    factory = Factory.query.filter_by(code='TEST001', is_deleted=0).first()
    if not factory:
        factory = Factory(
            name='测试工厂',
            code='TEST001',
            contact_person='张三',
            contact_phone='13800138000',
            address='广东省深圳市南山区',
            service_expire_date=date.today() + timedelta(days=365),
            status=1,
        )
        factory.save()

    owner, _ = _ensure_user('factory_admin', '工厂管理员')
    employee, _ = _ensure_user('factory_employee', '工厂员工')
    customer, _ = _ensure_user('factory_customer', '订单客户')
    collaborator, _ = _ensure_user('factory_collaborator', '协作用户')

    _ensure_user_factory(owner.id, factory.id, 'owner')
    _ensure_user_factory(employee.id, factory.id, 'employee')
    _ensure_user_factory(customer.id, factory.id, 'customer')
    _ensure_user_factory(collaborator.id, factory.id, 'collaborator', 'other_partner')

    owner_role, _ = _ensure_role(
        factory.id,
        'factory_admin',
        '工厂管理员',
        '工厂管理员，拥有工厂全部权限',
        1,
        data_scope='all_factory',
        is_factory_admin=1,
    )
    employee_role, _ = _ensure_role(
        factory.id,
        'factory_staff',
        '工厂员工',
        '工厂普通员工角色',
        2,
    )

    _ensure_user_role(owner.id, factory.id, owner_role.id)
    _ensure_user_role(employee.id, factory.id, employee_role.id)

    return factory


def _find_existing_menu(menu_data, parent_id):
    """根据业务唯一性查找已存在的菜单。"""
    permission = menu_data.get('permission')
    if permission:
        menu = Menu.query.filter_by(permission=permission, is_deleted=0).first()
        if menu:
            return menu
    return Menu.query.filter_by(
        parent_id=parent_id,
        name=menu_data['name'],
        path=menu_data['path'],
        type=menu_data['type'],
        is_deleted=0,
    ).first()


def seed_menus():
    """初始化系统菜单。"""
    menu_map = {}

    for menu_data in MENU_SEEDS:
        parent_id = 0
        parent_key = menu_data.get('parent_key')
        if parent_key:
            parent_menu = menu_map[parent_key]
            parent_id = parent_menu.id

        menu = _find_existing_menu(menu_data, parent_id)
        if not menu:
            menu = Menu(
                parent_id=parent_id,
                name=menu_data['name'],
                path=menu_data['path'],
                component=menu_data['component'],
                permission=menu_data['permission'],
                type=menu_data['type'],
                icon=menu_data['icon'],
                sort_order=menu_data['sort_order'],
                status=1,
            )
            db.session.add(menu)
            db.session.flush()
        else:
            menu.parent_id = parent_id
            menu.name = menu_data['name']
            menu.path = menu_data['path']
            menu.component = menu_data['component']
            menu.permission = menu_data['permission']
            menu.type = menu_data['type']
            menu.icon = menu_data['icon']
            menu.sort_order = menu_data['sort_order']
            menu.status = 1

        menu_map[menu_data['key']] = menu

    db.session.commit()
    return menu_map


def seed_reward_configs():
    """初始化奖励配置。"""
    for config_data in REWARD_CONFIG_SEEDS:
        config = RewardConfig.query.filter_by(
            rule_type=config_data['rule_type'],
            threshold=config_data['threshold'],
            reward_object=config_data['reward_object'],
            is_deleted=0,
        ).first()
        if config:
            config.name = config_data['name']
            config.reward_type = config_data['reward_type']
            config.reward_value = config_data['reward_value']
            config.is_active = config_data['is_active']
            config.remark = config_data['remark']
            continue

        db.session.add(RewardConfig(**config_data))

    db.session.commit()


def seed_demo_role_menus():
    """给演示工厂角色补齐基础菜单权限。"""
    factory = Factory.query.filter_by(code='TEST001', is_deleted=0).first()
    if not factory:
        return

    owner_role = Role.query.filter_by(factory_id=factory.id, code='factory_admin', is_deleted=0).first()
    employee_role = Role.query.filter_by(factory_id=factory.id, code='factory_staff', is_deleted=0).first()
    if not owner_role or not employee_role:
        return

    all_menu_ids = [menu.id for menu in Menu.query.filter_by(is_deleted=0, status=1).all()]
    staff_menu_ids = [
        menu.id for menu in Menu.query.filter(
            Menu.is_deleted == 0,
            Menu.status == 1,
            or_(
                Menu.permission == '',
                Menu.permission.is_(None),
                Menu.permission.like('base:%'),
                Menu.permission.like('business:%'),
            )
        ).all()
    ]

    def sync_role_menu(role, target_menu_ids):
        existing_ids = {
            menu_id for menu_id, in db.session.query(role_menu.c.menu_id).filter(role_menu.c.role_id == role.id).all()
        }
        for menu_id in target_menu_ids:
            if menu_id not in existing_ids:
                db.session.execute(role_menu.insert().values(role_id=role.id, menu_id=menu_id))

    sync_role_menu(owner_role, all_menu_ids)
    sync_role_menu(employee_role, staff_menu_ids)
    db.session.commit()


def seed_all():
    """执行完整初始化。"""
    create_tables()
    seed_admin_user()
    seed_menus()
    seed_reward_configs()
    seed_demo_factory()
    seed_demo_role_menus()
