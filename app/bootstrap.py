"""初始化与演示数据工具。"""

from datetime import date, timedelta

from sqlalchemy import or_

from app.constants.identity import PLATFORM_IDENTITY_ADMIN, PLATFORM_IDENTITY_EXTERNAL
from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.base_data.category import Category
from app.models.base_data.color import Color
from app.models.base_data.size import Size
from app.models.business.order import (
    Order,
    OrderDetail,
    OrderDetailAttributeSnapshot,
    OrderDetailSku,
    OrderDetailSkuAttribute,
    OrderDetailSkuSpliceItem,
    OrderDetailSpliceSnapshot,
)
from app.models.business.style import Style, StyleAttribute, StyleSpliceItem
from app.models.business.value_codec import encode_dynamic_value
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
    {'name': '邀请5人工厂延期', 'rule_type': 'invite_count', 'threshold': 5, 'reward_object': 'factory', 'reward_type': 'extend', 'reward_value': 365, 'is_active': 1, 'remark': '邀请满 5 人，工厂服务期延长一年'},
    {'name': '邀请5人现金奖励', 'rule_type': 'invite_count', 'threshold': 5, 'reward_object': 'personal', 'reward_type': 'cash', 'reward_value': 400, 'is_active': 1, 'remark': '邀请满 5 人，个人现金奖励 400 元'},
    {'name': '邀请10人工厂延期', 'rule_type': 'invite_count', 'threshold': 10, 'reward_object': 'factory', 'reward_type': 'extend', 'reward_value': 730, 'is_active': 1, 'remark': '邀请满 10 人，工厂服务期延长两年'},
]

DEMO_FACTORY_CODE = 'TEST001'
DEMO_FACTORY_NAME = '测试工厂'
DEMO_FACTORY_CODES = {'TEST001', 'TEST002'}
DEMO_USERNAMES = {
    'admin',
    'factory_admin',
    'factory_employee',
    'factory_customer',
    'factory_collaborator',
}


def create_tables():
    """创建数据库表。"""
    db.create_all()


def _ensure_user(username, nickname, platform_identity=PLATFORM_IDENTITY_EXTERNAL, password='123456'):
    """确保指定用户名存在，不存在则创建；存在时同步基础字段。"""
    user = User.query.filter_by(username=username, is_deleted=0).first()
    if user:
        changed = False
        if user.nickname != nickname:
            user.nickname = nickname
            changed = True
        if user.platform_identity != platform_identity:
            user.platform_identity = platform_identity
            changed = True
        if user.status != 1:
            user.status = 1
            changed = True
        if changed:
            db.session.add(user)
            db.session.commit()
        return user, False

    user = User(
        username=username,
        password=bcrypt.generate_password_hash(password).decode('utf-8'),
        nickname=nickname,
        platform_identity=platform_identity,
        status=1,
    )
    db.session.add(user)
    db.session.commit()
    return user, True


def _ensure_user_factory(user_id, factory_id, relation_type, collaborator_type=None):
    """确保用户与工厂关系存在。"""
    record = UserFactory.query.filter_by(
        user_id=user_id,
        factory_id=factory_id,
        relation_type=relation_type,
    ).order_by(UserFactory.id.asc()).first()
    if record:
        changed = False
        if record.is_deleted != 0:
            record.is_deleted = 0
            changed = True
        if record.status != 1:
            record.status = 1
            changed = True
        if record.collaborator_type != collaborator_type:
            record.collaborator_type = collaborator_type
            changed = True
        if record.entry_date is None:
            record.entry_date = date.today()
            changed = True
        if record.leave_date is not None:
            record.leave_date = None
            changed = True
        if changed:
            db.session.add(record)
            db.session.commit()
        return record, False

    record = UserFactory(
        user_id=user_id,
        factory_id=factory_id,
        relation_type=relation_type,
        collaborator_type=collaborator_type,
        status=1,
        entry_date=date.today(),
    )
    db.session.add(record)
    db.session.commit()
    return record, True


def _deactivate_other_relations(user_id, factory_id, keep_relation_types):
    """停用用户在同一工厂下不再需要的关系。"""
    keep_relation_types = set(keep_relation_types or [])
    records = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).all()
    for record in records:
        if record.relation_type in keep_relation_types:
            continue
        record.is_deleted = 1
        record.leave_date = date.today()
        db.session.add(record)
    db.session.commit()


def _ensure_role(factory_id, code, name, description, sort_order, data_scope='own_related', is_factory_admin=0, legacy_codes=None):
    """确保角色存在，并兼容旧角色编码。"""
    codes = [code] + list(legacy_codes or [])
    role = Role.query.filter(
        Role.factory_id == factory_id,
        Role.code.in_(codes),
        Role.is_deleted == 0,
    ).order_by(Role.id.asc()).first()
    if role:
        changed = False
        if role.code != code:
            role.code = code
            changed = True
        if role.name != name:
            role.name = name
            changed = True
        if role.description != description:
            role.description = description
            changed = True
        if role.sort_order != sort_order:
            role.sort_order = sort_order
            changed = True
        if role.data_scope != data_scope:
            role.data_scope = data_scope
            changed = True
        if role.is_factory_admin != is_factory_admin:
            role.is_factory_admin = is_factory_admin
            changed = True
        if role.status != 1:
            role.status = 1
            changed = True
        if changed:
            db.session.add(role)
            db.session.commit()
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
    db.session.add(role)
    db.session.commit()
    return role, True


def _replace_user_roles(user_id, factory_id, role_ids):
    """用指定角色覆盖用户在某个工厂下的角色关系。"""
    db.session.execute(
        UserFactoryRole.__table__.delete().where(
            UserFactoryRole.user_id == user_id,
            UserFactoryRole.factory_id == factory_id,
        )
    )
    for role_id in role_ids:
        db.session.add(UserFactoryRole(user_id=user_id, factory_id=factory_id, role_id=role_id))
    db.session.commit()


def _find_existing_menu(menu_data, parent_id):
    """根据业务唯一性查找已存在菜单。"""
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


def _sync_role_menu(role, target_menu_ids):
    """把指定菜单集合补齐到目标角色。"""
    existing_ids = {
        menu_id for menu_id, in db.session.query(role_menu.c.menu_id).filter(role_menu.c.role_id == role.id).all()
    }
    for menu_id in target_menu_ids:
        if menu_id not in existing_ids:
            db.session.execute(role_menu.insert().values(role_id=role.id, menu_id=menu_id))


def _create_color(factory_id, name, code, sort_order):
    """创建演示颜色。"""
    color = Color(
        factory_id=factory_id,
        name=name,
        actual_name=name,
        code=code,
        sort_order=sort_order,
        status=1,
    )
    db.session.add(color)
    db.session.flush()
    return color


def _create_size(factory_id, name, code, sort_order):
    """创建演示尺码。"""
    size = Size(
        factory_id=factory_id,
        name=name,
        code=code,
        sort_order=sort_order,
        status=1,
    )
    db.session.add(size)
    db.session.flush()
    return size


def _create_category(factory_id, parent_id, name, code, sort_order, category_type='material', remark=None):
    """创建演示分类。"""
    category = Category(
        factory_id=factory_id,
        parent_id=parent_id,
        name=name,
        code=code,
        category_type=category_type,
        sort_order=sort_order,
        status=1,
        remark=remark,
    )
    db.session.add(category)
    db.session.flush()
    return category


def _add_style_attribute(style, attr_key, value, sort_order):
    """为款号写入自定义属性。"""
    value_type, attr_value = encode_dynamic_value(value)
    db.session.add(StyleAttribute(
        style_id=style.id,
        attr_key=attr_key,
        attr_value=attr_value,
        value_type=value_type,
        sort_order=sort_order,
    ))


def _create_style(factory_id, style_no, name, material, description, unit='件', is_splice=0, splice_sections=None, customer_style_no=None):
    """创建演示款号及其附属属性。"""
    style = Style(
        factory_id=factory_id,
        style_no=style_no,
        customer_style_no=customer_style_no or style_no,
        name=name,
        material=material,
        description=description,
        status=1,
        need_cutting=0,
        cutting_reserve=0,
        is_splice=is_splice,
    )
    db.session.add(style)
    db.session.flush()

    _add_style_attribute(style, 'unit', unit, 1)
    for index, section_name in enumerate(splice_sections or [], start=1):
        db.session.add(StyleSpliceItem(style_id=style.id, sequence=index, description=section_name))
    db.session.flush()
    return style


def _snapshot_style_to_detail(detail, style):
    """把款号当前结构快照到订单明细。"""
    for item in sorted(style.splice_items, key=lambda current: (current.sequence, current.id or 0)):
        db.session.add(OrderDetailSpliceSnapshot(
            detail_id=detail.id,
            sequence=item.sequence,
            description=item.description,
        ))

    for item in sorted(style.attribute_items, key=lambda current: (current.sort_order, current.id or 0)):
        db.session.add(OrderDetailAttributeSnapshot(
            detail_id=detail.id,
            attr_key=item.attr_key,
            attr_value=item.attr_value,
            value_type=item.value_type,
            sort_order=item.sort_order,
        ))


def _add_sku_attribute(sku, attr_key, value, sort_order):
    """为订单 SKU 写入动态属性。"""
    value_type, attr_value = encode_dynamic_value(value)
    db.session.add(OrderDetailSkuAttribute(
        sku_id=sku.id,
        attr_key=attr_key,
        attr_value=attr_value,
        value_type=value_type,
        sort_order=sort_order,
    ))


def _add_sku_splice_items(sku, splice_descriptions):
    """为订单 SKU 写入拼接节位。"""
    for index, description in enumerate(splice_descriptions, start=1):
        db.session.add(OrderDetailSkuSpliceItem(
            sku_id=sku.id,
            sequence=index,
            description=description,
        ))


def _create_order(factory_id, creator_id, customer, order_no, order_date, delivery_date, remark):
    """创建演示订单主表。"""
    order = Order(
        order_no=order_no,
        factory_id=factory_id,
        customer_id=customer.id if customer else None,
        customer_name=customer.nickname if customer else None,
        order_date=order_date,
        delivery_date=delivery_date,
        status='pending',
        total_amount=0,
        remark=remark,
        create_by=creator_id,
        update_by=creator_id,
    )
    db.session.add(order)
    db.session.flush()
    return order


def _create_order_detail(order, style, remark):
    """创建订单明细并写入款号快照。"""
    detail = OrderDetail(order_id=order.id, style_id=style.id, remark=remark)
    db.session.add(detail)
    db.session.flush()
    _snapshot_style_to_detail(detail, style)
    db.session.flush()
    return detail


def cleanup_demo_data():
    """清理现有演示数据，保留系统菜单、奖励配置与平台初始化结构。"""
    demo_factories = Factory.query.filter(Factory.code.in_(DEMO_FACTORY_CODES)).all()
    demo_factory_ids = [factory.id for factory in demo_factories]

    demo_users = User.query.filter(User.username.in_(DEMO_USERNAMES - {'admin'}), User.is_deleted == 0).all()
    demo_user_ids = [user.id for user in demo_users]

    if demo_factory_ids:
        role_ids = [
            role.id for role in Role.query.filter(
                Role.factory_id.in_(demo_factory_ids),
                Role.is_deleted == 0,
            ).all()
        ]

        if role_ids:
            db.session.execute(role_menu.delete().where(role_menu.c.role_id.in_(role_ids)))

        db.session.execute(UserFactoryRole.__table__.delete().where(UserFactoryRole.factory_id.in_(demo_factory_ids)))
        if role_ids:
            db.session.query(Role).filter(Role.id.in_(role_ids)).delete(synchronize_session=False)

        db.session.query(UserFactory).filter(UserFactory.factory_id.in_(demo_factory_ids)).delete(synchronize_session=False)

        orders = Order.query.filter(Order.factory_id.in_(demo_factory_ids)).all()
        for order in orders:
            db.session.delete(order)

        styles = Style.query.filter(Style.factory_id.in_(demo_factory_ids)).all()
        for style in styles:
            db.session.delete(style)

        db.session.query(Color).filter(Color.factory_id.in_(demo_factory_ids)).delete(synchronize_session=False)
        db.session.query(Size).filter(Size.factory_id.in_(demo_factory_ids)).delete(synchronize_session=False)
        db.session.query(Category).filter(Category.factory_id.in_(demo_factory_ids)).delete(synchronize_session=False)

        for factory in demo_factories:
            db.session.delete(factory)

    if demo_user_ids:
        db.session.execute(UserFactoryRole.__table__.delete().where(UserFactoryRole.user_id.in_(demo_user_ids)))
        db.session.query(UserFactory).filter(UserFactory.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        for user in demo_users:
            db.session.delete(user)

    db.session.commit()


def seed_admin_user():
    """创建平台管理员账号。"""
    return _ensure_user('admin', '平台管理员', PLATFORM_IDENTITY_ADMIN)


def seed_demo_factory():
    """创建标准演示工厂、演示账号、关系和角色。"""
    factory = Factory(
        name=DEMO_FACTORY_NAME,
        code=DEMO_FACTORY_CODE,
        contact_person='张三',
        contact_phone='13800138000',
        address='广东省深圳市南山区',
        service_expire_date=date.today() + timedelta(days=365),
        status=1,
    )
    db.session.add(factory)
    db.session.commit()

    owner, _ = _ensure_user('factory_admin', '工厂管理员')
    employee, _ = _ensure_user('factory_employee', '工厂员工')
    customer, _ = _ensure_user('factory_customer', '订单客户')
    collaborator, _ = _ensure_user('factory_collaborator', '协作用户')

    _ensure_user_factory(owner.id, factory.id, 'owner')
    _ensure_user_factory(employee.id, factory.id, 'employee')
    _ensure_user_factory(customer.id, factory.id, 'customer')
    _ensure_user_factory(collaborator.id, factory.id, 'collaborator', 'other_partner')

    _deactivate_other_relations(owner.id, factory.id, {'owner'})
    _deactivate_other_relations(employee.id, factory.id, {'employee'})
    _deactivate_other_relations(customer.id, factory.id, {'customer'})
    _deactivate_other_relations(collaborator.id, factory.id, {'collaborator'})

    owner_role, _ = _ensure_role(
        factory.id,
        'factory_admin',
        '工厂管理员',
        '工厂管理员，拥有工厂全部权限',
        1,
        data_scope='all_factory',
        is_factory_admin=1,
        legacy_codes=['admin'],
    )
    employee_role, _ = _ensure_role(
        factory.id,
        'factory_staff',
        '工厂员工',
        '工厂普通员工角色',
        2,
        legacy_codes=['staff'],
    )

    _replace_user_roles(owner.id, factory.id, [owner_role.id])
    _replace_user_roles(employee.id, factory.id, [employee_role.id])
    return factory


def seed_demo_base_data(factory):
    """创建演示基础数据。"""
    colors = {
        '红色': _create_color(factory.id, '红色', 'RED', 1),
        '黄色': _create_color(factory.id, '黄色', 'YELLOW', 2),
        '绿色': _create_color(factory.id, '绿色', 'GREEN', 3),
        '紫色': _create_color(factory.id, '紫色', 'PURPLE', 4),
        '黑色': _create_color(factory.id, '黑色', 'BLACK', 5),
    }

    sizes = {
        '均码': _create_size(factory.id, '均码', 'ONE', 1),
        'M': _create_size(factory.id, 'M', 'M', 2),
        'L': _create_size(factory.id, 'L', 'L', 3),
        'XL': _create_size(factory.id, 'XL', 'XL', 4),
        '2XL': _create_size(factory.id, '2XL', '2XL', 5),
    }

    material_root = _create_category(factory.id, 0, '物料', 'MATERIAL', 1, category_type='material', remark='演示物料分类根节点')
    categories = {
        '物料': material_root,
        '针织': _create_category(factory.id, material_root.id, '针织', 'KNIT', 1, category_type='material'),
        '棉麻': _create_category(factory.id, material_root.id, '棉麻', 'COTTON_LINEN', 2, category_type='material'),
        '条纹': _create_category(factory.id, material_root.id, '条纹', 'STRIPE', 3, category_type='material'),
        '图案': _create_category(factory.id, material_root.id, '图案', 'PATTERN', 4, category_type='material'),
    }

    db.session.commit()
    return {'colors': colors, 'sizes': sizes, 'categories': categories}


def seed_demo_business_data(factory, base_data):
    """创建演示款号与演示订单。"""
    owner = User.query.filter_by(username='factory_admin', is_deleted=0).first()
    customer = User.query.filter_by(username='factory_customer', is_deleted=0).first()

    styles = {
        '1235#': _create_style(
            factory.id,
            '1235#',
            '1235#测试款',
            '针织',
            '测试数据-订单1对应款号',
        ),
        '2235#': _create_style(
            factory.id,
            '2235#',
            '2235#测试款',
            '棉麻',
            '测试数据-订单2对应款号',
        ),
        '3455#': _create_style(
            factory.id,
            '3455#',
            '3455#拼接测试款',
            '条纹',
            '测试数据-订单3对应拼接款号',
            is_splice=1,
            splice_sections=['第一节', '第二节', '第三节', '第四节'],
        ),
    }
    db.session.commit()

    order1 = _create_order(factory.id, owner.id, customer, 'DEMO-ORDER-001', date.today(), date.today() + timedelta(days=7), '测试数据-订单1-1235#')
    order1_detail = _create_order_detail(order1, styles['1235#'], '1235# 均码颜色订单')
    for priority, (color_name, quantity) in enumerate([
        ('红色', 20),
        ('黄色', 25),
        ('绿色', 20),
        ('紫色', 35),
        ('黑色', 20),
    ], start=1):
        color = base_data['colors'][color_name]
        size = base_data['sizes']['均码']
        sku = OrderDetailSku(
            detail_id=order1_detail.id,
            color_id=color.id,
            size_id=size.id,
            quantity=quantity,
            unit_price=0,
            priority=priority,
            remark=f'{color_name}-均码 数量 {quantity}',
        )
        db.session.add(sku)
        db.session.flush()
        _add_sku_attribute(sku, 'tag', f'{color.code}-ONE', 1)

    order2 = _create_order(factory.id, owner.id, customer, 'DEMO-ORDER-002', date.today(), date.today() + timedelta(days=8), '测试数据-订单2-2235#')
    order2_detail = _create_order_detail(order2, styles['2235#'], '2235# 颜色尺码矩阵订单')
    order2_rows = {
        '红色': {'M': 20, 'L': 20, 'XL': 20, '2XL': 25},
        '黄色': {'M': 25, 'L': 20, 'XL': 20, '2XL': 30},
        '绿色': {'M': 20, 'L': 20, 'XL': 20, '2XL': 30},
        '紫色': {'M': 35, 'L': 20, 'XL': 20, '2XL': 30},
        '黑色': {'M': 20, 'L': 20, 'XL': 20, '2XL': 30},
    }
    priority = 1
    for color_name, size_map in order2_rows.items():
        color = base_data['colors'][color_name]
        for size_name, quantity in size_map.items():
            size = base_data['sizes'][size_name]
            sku = OrderDetailSku(
                detail_id=order2_detail.id,
                color_id=color.id,
                size_id=size.id,
                quantity=quantity,
                unit_price=0,
                priority=priority,
                remark=f'{color_name}-{size_name} 数量 {quantity}',
            )
            db.session.add(sku)
            db.session.flush()
            _add_sku_attribute(sku, 'tag', f'{color.code}-{size.code}', 1)
            priority += 1

    order3 = _create_order(factory.id, owner.id, customer, 'DEMO-ORDER-003', date.today(), date.today() + timedelta(days=9), '测试数据-订单3-3455#')
    order3_detail = _create_order_detail(order3, styles['3455#'], '3455# 拼接结构订单')
    for priority, (variant_name, splice_parts, quantity, remark) in enumerate([
        ('红黄绿条纹紫', ['红', '黄', '绿，条纹', '紫'], 30, '组合一 30 件'),
        ('红黄黑条纹紫', ['红', '黄', '黑，条纹', '紫'], 40, '组合二 40 件'),
    ], start=1):
        sku = OrderDetailSku(
            detail_id=order3_detail.id,
            quantity=quantity,
            unit_price=0,
            priority=priority,
            remark=remark,
        )
        db.session.add(sku)
        db.session.flush()
        _add_sku_attribute(sku, 'variant_name', variant_name, 1)
        _add_sku_splice_items(sku, splice_parts)

    db.session.commit()
    return styles


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
    factory = Factory.query.filter_by(code=DEMO_FACTORY_CODE, is_deleted=0).first()
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

    _sync_role_menu(owner_role, all_menu_ids)
    _sync_role_menu(employee_role, staff_menu_ids)
    db.session.commit()


def seed_all():
    """执行完整初始化，包括清理旧演示数据后重建。"""
    create_tables()
    cleanup_demo_data()
    admin, _ = seed_admin_user()
    seed_menus()
    seed_reward_configs()
    factory = seed_demo_factory()
    seed_demo_role_menus()
    base_data = seed_demo_base_data(factory)
    styles = seed_demo_business_data(factory, base_data)
    return {
        'admin': admin,
        'factory': factory,
        'base_data': base_data,
        'styles': styles,
    }
