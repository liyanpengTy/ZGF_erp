"""用户管理服务"""
from app.extensions import db, bcrypt
from app.models.auth.user import User
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.models.system.role import Role, role_menu
from app.services.base.base_service import BaseService
from app.models.system.menu import Menu


class UserService(BaseService):
    """用户管理服务"""

    @staticmethod
    def get_user_by_id(user_id):
        """根据ID获取用户"""
        return User.query.filter_by(id=user_id, is_deleted=0).first()

    @staticmethod
    def get_user_by_username(username):
        """根据用户名获取用户"""
        return User.query.filter_by(username=username, is_deleted=0).first()

    @staticmethod
    def get_user_list(current_user, filters):
        """
        获取用户列表
        filters: page, page_size, username, status, factory_id
        """
        query = User.query.filter_by(is_deleted=0)

        # 权限过滤
        if current_user.is_admin == 1:
            # 公司内部人员：可以查看所有用户
            factory_id = filters.get('factory_id')
            if factory_id:
                user_ids = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id, status=1, is_deleted=0
                ).all()
                user_ids = [u[0] for u in user_ids]
                query = query.filter(User.id.in_(user_ids))
        else:
            # 普通用户：只能查看自己
            query = query.filter(User.id == current_user.id)

        # 条件过滤
        username = filters.get('username')
        if username:
            query = query.filter(User.username.like(f'%{username}%'))

        status = filters.get('status')
        if status is not None:
            query = query.filter_by(status=status)

        # 分页
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        pagination = query.order_by(User.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def create_user(data, current_user_id):
        """创建用户"""
        # 检查用户名是否已存在
        existing = UserService.get_user_by_username(data['username'])
        if existing:
            return None, '用户名已存在'

        user = User(
            username=data['username'],
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            nickname=data.get('nickname', ''),
            phone=data.get('phone', ''),
            is_admin=data.get('is_admin', 0),
            status=1
        )
        user.save()

        return user, None

    @staticmethod
    def update_user(user, data):
        """更新用户信息"""
        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'phone' in data:
            user.phone = data['phone']
        if 'status' in data:
            user.status = data['status']
        user.save()
        return user

    @staticmethod
    def reset_password(user, new_password):
        """重置密码"""
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.save()
        return user

    @staticmethod
    def delete_user(user):
        """软删除用户"""
        user.is_deleted = 1
        user.save()
        return True

    @staticmethod
    def get_user_roles(user_id, factory_id):
        """获取用户的角色列表"""
        role_ids = db.session.query(UserFactoryRole.role_id).filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).all()
        role_ids = [r[0] for r in role_ids]

        if role_ids:
            return Role.query.filter(Role.id.in_(role_ids), Role.is_deleted == 0).all()
        return []

    @staticmethod
    def assign_roles(user_id, role_ids, factory_id, current_user):
        """分配角色"""
        # 验证角色
        for role_id in role_ids:
            role = Role.query.filter_by(id=role_id, is_deleted=0).first()
            if not role:
                return False, f'角色ID {role_id} 不存在'
            # 平台角色权限校验
            if role.factory_id > 0 and role.factory_id != factory_id:
                return False, f'角色 {role.name} 不属于该工厂'

        # 删除原有角色分配
        if factory_id:
            db.session.execute(
                UserFactoryRole.__table__.delete().where(
                    UserFactoryRole.user_id == user_id,
                    UserFactoryRole.factory_id == factory_id
                )
            )
        else:
            db.session.execute(
                UserFactoryRole.__table__.delete().where(
                    UserFactoryRole.user_id == user_id
                )
            )

        # 添加新角色分配
        for role_id in role_ids:
            role = Role.query.get(role_id)
            ufr = UserFactoryRole(
                user_id=user_id,
                factory_id=0 if role.factory_id == 0 else factory_id,
                role_id=role_id
            )
            db.session.add(ufr)

        db.session.commit()
        return True, None

    @staticmethod
    def get_current_user_id_from_identity(identity):
        """从 get_jwt_identity 返回值中解析用户ID"""
        if isinstance(identity, dict):
            return identity.get('user_id')
        return int(identity)

    @staticmethod
    def get_user_permissions(user_id):
        """获取用户的权限标识列表"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return []

        # 公司内部人员返回所有权限
        if user.is_admin == 1:
            menus = Menu.query.filter(
                Menu.permission.isnot(None),
                Menu.permission != '',
                Menu.status == 1,
                Menu.is_deleted == 0
            ).all()
            return [m.permission for m in menus]

        # 获取用户所在的工厂（从 Token 或关联表）
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        factory_id = claims.get('factory_id')

        if not factory_id:
            return []

        # 获取用户在该工厂下的角色
        role_records = UserFactoryRole.query.filter_by(
            user_id=user.id, factory_id=factory_id, is_deleted=0
        ).all()
        role_ids = [r.role_id for r in role_records]

        if not role_ids:
            return []

        # 获取角色关联的菜单权限
        menu_records = db.session.query(role_menu).filter(
            role_menu.c.role_id.in_(role_ids)
        ).all()
        menu_ids = list(set([r.menu_id for r in menu_records]))

        if not menu_ids:
            return []

        # 获取权限标识
        menus = Menu.query.filter(
            Menu.id.in_(menu_ids),
            Menu.permission.isnot(None),
            Menu.permission != '',
            Menu.status == 1,
            Menu.is_deleted == 0
        ).all()

        return [m.permission for m in menus]