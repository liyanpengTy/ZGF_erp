"""角色管理服务。"""

from app.constants.identity import (
    RELATION_TYPE_OWNER,
    ROLE_DATA_SCOPE_OWN_RELATED,
    ROLE_SCOPE_FACTORY,
    ROLE_SCOPE_PLATFORM,
    ROLE_SCOPE_SUBJECT,
)
from app.extensions import db
from app.models.system.menu import Menu
from app.models.system.role import Role, role_menu
from app.models.system.subject_role import SubjectRole, SubjectUserRole, subject_role_menu
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.services.base.base_service import BaseService
from app.utils.cache import SimpleTTLCache


FACTORY_ROLE_FORBIDDEN_PERMISSION_PREFIXES = ('system.',)
FACTORY_ADMIN_PERMISSION_CACHE = SimpleTTLCache(default_ttl=300)


class RoleService(BaseService):
    """提供旧角色与主体角色的统一查询、维护和授权能力。"""

    @staticmethod
    def is_subject_role(role):
        """判断角色对象是否为主体角色模型。"""
        return isinstance(role, SubjectRole)

    @staticmethod
    def get_role_model(scope_type=None, role=None):
        """根据范围类型或角色对象返回对应模型。"""
        if role is not None and RoleService.is_subject_role(role):
            return SubjectRole
        if scope_type == ROLE_SCOPE_SUBJECT:
            return SubjectRole
        return Role

    @staticmethod
    def get_role_scope_type(role):
        """返回统一后的角色范围类型。"""
        return ROLE_SCOPE_SUBJECT if RoleService.is_subject_role(role) else role.scope_type

    @staticmethod
    def get_role_scope_id(role):
        """返回统一后的角色范围主键。"""
        return role.subject_id if RoleService.is_subject_role(role) else role.scope_id

    @staticmethod
    def get_role_scope_label(role):
        """返回统一后的角色范围名称。"""
        if RoleService.is_subject_role(role):
            return '主体角色'
        return role.scope_type_label

    @staticmethod
    def get_role_is_admin(role):
        """返回统一后的管理员标记。"""
        return role.is_admin if RoleService.is_subject_role(role) else role.is_factory_admin

    @staticmethod
    def get_role_data_scope(role):
        """返回统一后的数据范围编码。"""
        return role.data_scope or ROLE_DATA_SCOPE_OWN_RELATED

    @staticmethod
    def get_role_data_scope_label(role):
        """返回统一后的数据范围名称。"""
        if RoleService.get_role_data_scope(role) == 'subject':
            return '当前主体数据'
        if RoleService.is_subject_role(role):
            labels = {
                'assigned': '分配数据',
                'own_related': '本人关联数据',
                'self_only': '仅个人数据',
            }
            return labels.get(role.data_scope, role.data_scope)
        return role.data_scope_label

    @staticmethod
    def serialize_role(role):
        """把旧角色和主体角色序列化为统一结构。"""
        return {
            'id': role.id,
            'scope_type': RoleService.get_role_scope_type(role),
            'scope_type_label': RoleService.get_role_scope_label(role),
            'scope_id': RoleService.get_role_scope_id(role),
            'name': role.name,
            'code': role.code,
            'description': role.description,
            'status': role.status,
            'sort_order': role.sort_order,
            'data_scope': RoleService.get_role_data_scope(role),
            'data_scope_label': RoleService.get_role_data_scope_label(role),
            'is_factory_admin': 1 if RoleService.get_role_is_admin(role) else 0,
            'create_time': role.create_time.strftime('%Y-%m-%d %H:%M:%S') if role.create_time else None,
            'update_time': role.update_time.strftime('%Y-%m-%d %H:%M:%S') if role.update_time else None,
        }

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
        if admin_role:
            FACTORY_ADMIN_PERMISSION_CACHE.set(cache_key, True)
            return True

        subject_admin_role = SubjectUserRole.query.join(
            SubjectRole,
            SubjectRole.id == SubjectUserRole.subject_role_id,
        ).filter(
            SubjectUserRole.user_id == user.id,
            SubjectUserRole.subject_id == factory_id,
            SubjectUserRole.is_deleted == 0,
            SubjectRole.subject_id == factory_id,
            SubjectRole.is_admin == 1,
            SubjectRole.status == 1,
            SubjectRole.is_deleted == 0,
        ).first()
        result = subject_admin_role is not None
        FACTORY_ADMIN_PERMISSION_CACHE.set(cache_key, result)
        return result

    @staticmethod
    def normalize_scope(scope_type, scope_id):
        """归一化角色范围，避免平台角色携带工厂主键。"""
        if scope_type == ROLE_SCOPE_PLATFORM:
            return ROLE_SCOPE_PLATFORM, 0
        if scope_type in {ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT}:
            if not scope_id:
                return None, None
            return scope_type, scope_id
        return scope_type, scope_id or 0

    @staticmethod
    def get_role_by_id(role_id):
        """按主键查询未删除旧角色。"""
        return Role.query.filter_by(id=role_id, is_deleted=0).first()

    @staticmethod
    def get_subject_role_by_id(role_id, subject_id=None):
        """按主键查询未删除主体角色。"""
        query = SubjectRole.query.filter_by(id=role_id, is_deleted=0)
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        return query.first()

    @staticmethod
    def get_role_resource(role_id, scope_type=None, scope_id=None):
        """根据范围类型解析统一角色对象。"""
        if scope_type == ROLE_SCOPE_SUBJECT:
            return RoleService.get_subject_role_by_id(role_id, subject_id=scope_id)
        return RoleService.get_role_by_id(role_id)

    @staticmethod
    def get_role_by_code(scope_type, scope_id, code):
        """按范围和编码查询角色。"""
        scope_type, scope_id = RoleService.normalize_scope(scope_type, scope_id)
        if scope_type == ROLE_SCOPE_SUBJECT:
            return SubjectRole.query.filter_by(subject_id=scope_id, code=code, is_deleted=0).first()
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
        if scope_type == ROLE_SCOPE_SUBJECT:
            return SubjectRole.query.filter_by(subject_id=scope_id, name=name, is_deleted=0).first()
        return Role.query.filter_by(
            scope_type=scope_type,
            scope_id=scope_id,
            name=name,
            is_deleted=0,
        ).first()

    @staticmethod
    def _apply_role_basic_filters(query, model, name='', status=None):
        """统一追加角色名称和状态筛选。"""
        if name:
            query = query.filter(model.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter(model.status == status)
        return query

    @staticmethod
    def _order_role_query(query, model):
        """统一角色排序规则。"""
        return query.order_by(model.sort_order.asc(), model.id.asc())

    @staticmethod
    def _build_role_query(current_user, current_factory_id=None, scope_type=None, scope_id=None):
        """按当前用户上下文构造角色查询。"""
        if scope_type == ROLE_SCOPE_SUBJECT or (not current_user.is_internal_user and not scope_type):
            return RoleService._build_subject_role_query(current_user, current_factory_id, scope_id)

        if current_user.is_internal_user:
            query = Role.query.filter(Role.is_deleted == 0)
            if scope_type:
                normalized_scope_type, normalized_scope_id = RoleService.normalize_scope(scope_type, scope_id)
                if scope_type == ROLE_SCOPE_FACTORY and not normalized_scope_id:
                    return None, '工厂角色必须指定 scope_id'
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
    def _build_subject_role_query(current_user, current_factory_id=None, scope_id=None):
        """按当前用户上下文构造主体角色查询。"""
        if current_user.is_internal_user:
            query = SubjectRole.query.filter(SubjectRole.is_deleted == 0)
            if scope_id:
                query = query.filter(SubjectRole.subject_id == scope_id)
            return query, None

        target_subject_id = current_factory_id or scope_id
        if not target_subject_id:
            return None, '请先选择工厂上下文'
        if scope_id and scope_id != target_subject_id:
            return None, '无权限跨主体查看角色'
        if not RoleService.has_factory_admin_permission(current_user, target_subject_id):
            return None, '无权限查看角色'
        return SubjectRole.query.filter_by(subject_id=target_subject_id, is_deleted=0), None

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

        model = RoleService.get_role_model(scope_type=scope_type)
        query = RoleService._apply_role_basic_filters(query, model, name=name, status=status)
        pagination = RoleService._order_role_query(query, model).paginate(
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

        model = RoleService.get_role_model(scope_type=scope_type)
        query = RoleService._apply_role_basic_filters(query, model, name=name, status=status)
        return RoleService._order_role_query(query, model).all(), None

    @staticmethod
    def create_role(data):
        """创建角色并初始化数据范围。"""
        scope_type, scope_id = RoleService.normalize_scope(data['scope_type'], data.get('scope_id'))
        if scope_type in {ROLE_SCOPE_FACTORY, ROLE_SCOPE_SUBJECT} and not scope_id:
            return None, '主体角色必须指定 scope_id'

        existing_code = RoleService.get_role_by_code(scope_type, scope_id, data['code'])
        if existing_code:
            return None, '角色编码已存在'

        existing_name = RoleService.get_role_by_name(scope_type, scope_id, data['name'])
        if existing_name:
            return None, '角色名称已存在'

        if scope_type == ROLE_SCOPE_SUBJECT:
            role = SubjectRole(
                subject_id=scope_id,
                name=data['name'],
                code=data['code'],
                description=data.get('description', ''),
                sort_order=data.get('sort_order', 0),
                data_scope=data.get('data_scope', 'subject'),
                is_admin=data.get('is_factory_admin', 0),
                status=1,
            )
        else:
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
        """更新角色名称、排序、状态和数据范围。"""
        if 'name' in data:
            existing = RoleService.get_role_by_name(
                RoleService.get_role_scope_type(role),
                RoleService.get_role_scope_id(role),
                data['name'],
            )
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
            if RoleService.is_subject_role(role):
                role.is_admin = data['is_factory_admin']
            else:
                role.is_factory_admin = data['is_factory_admin']

        role.save()
        RoleService.clear_permission_cache()
        return role, None

    @staticmethod
    def delete_role(role):
        """逻辑删除角色，删除前校验是否仍被使用。"""
        if RoleService.is_subject_role(role):
            user_role_count = SubjectUserRole.query.filter_by(subject_role_id=role.id, is_deleted=0).count()
        else:
            user_role_count = UserFactoryRole.query.filter_by(role_id=role.id, is_deleted=0).count()
        if user_role_count > 0:
            return False, f'已有 {user_role_count} 个用户关联此角色，无法删除'

        role.is_deleted = 1
        role.save()
        RoleService.clear_permission_cache()
        return True, None

    @staticmethod
    def get_role_menu_ids(role):
        """查询角色已绑定的菜单 ID 列表。"""
        if RoleService.is_subject_role(role):
            menu_ids = db.session.query(subject_role_menu.c.menu_id).filter_by(subject_role_id=role.id).all()
        else:
            menu_ids = db.session.query(role_menu.c.menu_id).filter_by(role_id=role.id).all()
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
                not RoleService.is_subject_role(role)
                and role.is_factory_role
                and menu.permission
                and menu.permission.startswith(FACTORY_ROLE_FORBIDDEN_PERMISSION_PREFIXES)
            ):
                return False, f'工厂角色不允许绑定平台级权限 {menu.permission}'

        if RoleService.is_subject_role(role):
            db.session.execute(subject_role_menu.delete().where(subject_role_menu.c.subject_role_id == role_id))
            for menu_id in menu_ids:
                db.session.execute(subject_role_menu.insert().values(subject_role_id=role_id, menu_id=menu_id))
        else:
            db.session.execute(role_menu.delete().where(role_menu.c.role_id == role_id))
            for menu_id in menu_ids:
                db.session.execute(role_menu.insert().values(role_id=role_id, menu_id=menu_id))

        db.session.commit()
        RoleService.clear_permission_cache()
        return True, None

    @staticmethod
    def get_role_users(role):
        """查询拥有该角色的用户 ID 列表。"""
        if RoleService.is_subject_role(role):
            user_ids = db.session.query(SubjectUserRole.user_id).filter_by(
                subject_role_id=role.id,
                is_deleted=0,
            ).all()
        else:
            user_ids = db.session.query(UserFactoryRole.user_id).filter_by(role_id=role.id, is_deleted=0).all()
        return [user_id for user_id, in user_ids]
