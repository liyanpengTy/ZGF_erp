"""工厂管理服务"""
from datetime import datetime
from app.extensions import bcrypt
from app.models.system.factory import Factory
from app.models.auth.user import User
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService


class FactoryService(BaseService):
    """工厂管理服务"""

    @staticmethod
    def get_factory_by_id(factory_id):
        """根据ID获取工厂"""
        return Factory.query.filter_by(id=factory_id, is_deleted=0).first()

    @staticmethod
    def get_factory_by_code(code):
        """根据编码获取工厂"""
        return Factory.query.filter_by(code=code, is_deleted=0).first()

    @staticmethod
    def get_factory_list(filters):
        """
        获取工厂列表
        filters: page, page_size, name, status
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        query = Factory.query.filter_by(is_deleted=0)

        if name:
            query = query.filter(Factory.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Factory.id.desc()).paginate(
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
    def create_factory(data):
        """
        创建工厂及其主体账号
        relation_type: owner - 工厂主体账号
        """
        # 检查编码是否存在
        existing = FactoryService.get_factory_by_code(data['code'])
        if existing:
            return None, None, '工厂编码已存在'

        # 创建工厂
        factory = Factory(
            name=data['name'],
            code=data['code'],
            contact_person=data.get('contact_person', ''),
            contact_phone=data.get('contact_phone', ''),
            address=data.get('address', ''),
            remark=data.get('remark', ''),
            status=1
        )
        factory.save()

        # 处理工厂主体账号
        # 检查是否已存在同用户名的用户
        existing_user = User.query.filter_by(username=data['code'], is_deleted=0).first()

        if existing_user:
            # 用户已存在，更新信息并关联
            existing_user.nickname = data['name']
            existing_user.is_admin = 0
            existing_user.status = 1
            existing_user.save()
            factory_admin = existing_user
        else:
            # 创建新的工厂主体用户
            factory_admin = User(
                username=data['code'],
                password=bcrypt.generate_password_hash('123456').decode('utf-8'),
                nickname=data['name'],
                is_admin=0,
                status=1
            )
            factory_admin.save()

        # 删除旧的关联（如果存在）
        old_relation = UserFactory.query.filter_by(
            user_id=factory_admin.id, factory_id=factory.id, is_deleted=0
        ).first()
        if old_relation:
            old_relation.is_deleted = 1
            old_relation.save()

        # 关联用户到工厂（作为工厂主体 owner）
        user_factory = UserFactory(
            user_id=factory_admin.id,
            factory_id=factory.id,
            relation_type='owner',
            status=1,
            entry_date=datetime.now().date(),
            remark='工厂主体账号'
        )
        user_factory.save()

        return factory, factory_admin, None

    @staticmethod
    def update_factory(factory, data):
        """更新工厂信息"""
        if 'name' in data:
            factory.name = data['name']
        if 'contact_person' in data:
            factory.contact_person = data['contact_person']
        if 'contact_phone' in data:
            factory.contact_phone = data['contact_phone']
        if 'address' in data:
            factory.address = data['address']
        if 'status' in data:
            factory.status = data['status']
        if 'remark' in data:
            factory.remark = data['remark']

        factory.save()

        # 同步更新工厂主体用户的昵称
        if 'name' in data:
            user_factory = UserFactory.query.filter_by(
                factory_id=factory.id, relation_type='owner', is_deleted=0
            ).first()
            if user_factory:
                owner_user = User.query.filter_by(id=user_factory.user_id, is_deleted=0).first()
                if owner_user:
                    owner_user.nickname = data['name']
                    owner_user.save()

        return factory

    @staticmethod
    def delete_factory(factory):
        """删除工厂（软删除）"""
        # 检查是否有用户关联该工厂（不包括 owner）
        user_count = UserFactory.query.filter_by(
            factory_id=factory.id, is_deleted=0
        ).filter(UserFactory.relation_type != 'owner').count()
        if user_count > 0:
            return False, f'请先解除工厂关联的用户（共 {user_count} 个）'

        # 解雇 owner 关联（不删除用户，只解除关联）
        owner_relation = UserFactory.query.filter_by(
            factory_id=factory.id, relation_type='owner', is_deleted=0
        ).first()
        if owner_relation:
            owner_relation.is_deleted = 1
            owner_relation.save()

        factory.is_deleted = 1
        factory.save()
        return True, None

    @staticmethod
    def check_factory_permission(current_user, factory_id):
        """检查用户是否有权限操作该工厂"""
        if not current_user:
            return False, '用户不存在'

        if current_user.is_admin == 1:
            return True, None

        user_factory = UserFactory.query.filter_by(
            user_id=current_user.id, factory_id=factory_id, status=1, is_deleted=0
        ).first()

        if user_factory:
            return True, None

        return False, '无权限查看'

    @staticmethod
    def get_factory_users(factory_id, filters):
        """
        获取工厂关联的用户列表
        filters: page, page_size, username, status, relation_type
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        status = filters.get('status')
        relation_type = filters.get('relation_type')

        query = UserFactory.query.filter_by(factory_id=factory_id, is_deleted=0)

        if relation_type:
            query = query.filter_by(relation_type=relation_type)

        user_factory_list = query.all()
        user_ids = [uf.user_id for uf in user_factory_list]

        if not user_ids:
            return {
                'items': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'pages': 0,
                'user_factory_map': {}
            }

        user_query = User.query.filter(User.id.in_(user_ids), User.is_deleted == 0)

        if username:
            user_query = user_query.filter(User.username.like(f'%{username}%'))
        if status is not None:
            user_query = user_query.filter_by(status=status)

        pagination = user_query.order_by(User.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        # 构建用户-工厂关联映射
        user_factory_map = {uf.user_id: uf for uf in user_factory_list}

        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
            'user_factory_map': user_factory_map
        }

    @staticmethod
    def add_user_to_factory(factory_id, user_id, relation_type):
        """添加用户到工厂（员工、客户、协作用户）"""
        # 检查用户是否存在
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None, '用户不存在'

        # 检查是否已关联
        existing = UserFactory.query.filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).first()
        if existing:
            return None, '用户已关联此工厂'

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory_id,
            relation_type=relation_type,
            status=1,
            entry_date=datetime.now().date()
        )
        user_factory.save()

        return user_factory, None

    @staticmethod
    def update_factory_owner(factory_id, user_id):
        """更新工厂的主体账号"""
        # 检查用户是否存在
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None, '用户不存在'

        # 检查工厂是否存在
        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return None, '工厂不存在'

        # 查找现有的 owner 关联
        existing_owner = UserFactory.query.filter_by(
            factory_id=factory_id, relation_type='owner', is_deleted=0
        ).first()

        if existing_owner:
            # 如果已是同一用户，返回错误
            if existing_owner.user_id == user_id:
                return None, '该用户已是工厂主体'
            # 解除旧关联
            existing_owner.is_deleted = 1
            existing_owner.save()

        # 检查用户是否已有其他关联
        existing_relation = UserFactory.query.filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).first()

        if existing_relation:
            existing_relation.relation_type = 'owner'
            existing_relation.entry_date = datetime.now().date()
            existing_relation.remark = '工厂主体账号'
            existing_relation.save()
            user_factory = existing_relation
        else:
            # 创建新的 owner 关联
            user_factory = UserFactory(
                user_id=user_id,
                factory_id=factory_id,
                relation_type='owner',
                status=1,
                entry_date=datetime.now().date(),
                remark='工厂主体账号'
            )
            user_factory.save()

        # 同步更新用户的 nickname
        if user.nickname != factory.name:
            user.nickname = factory.name
            user.save()

        return user_factory, None

    @staticmethod
    def remove_user_from_factory(factory_id, user_id):
        """从工厂移除用户（不能移除 owner）"""
        user_factory = UserFactory.query.filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).first()

        if not user_factory:
            return False, '用户未关联此工厂'

        # 禁止移除工厂主体
        if user_factory.relation_type == 'owner':
            return False, '不能移除工厂主体账号'

        user_factory.is_deleted = 1
        user_factory.save()
        return True, None

    @staticmethod
    def get_factory_owner(factory_id):
        """获取工厂的主体账号"""
        user_factory = UserFactory.query.filter_by(
            factory_id=factory_id, relation_type='owner', status=1, is_deleted=0
        ).first()
        if user_factory:
            return User.query.filter_by(id=user_factory.user_id, is_deleted=0).first()
        return None

    @staticmethod
    def reset_owner_password(factory_id):
        """重置工厂主体账号密码为默认密码"""
        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return False, '工厂主体账号不存在'

        owner.password = bcrypt.generate_password_hash('123456').decode('utf-8')
        owner.save()
        return True, None

    @staticmethod
    def generate_qrcode(factory):
        """生成工厂二维码"""
        import uuid

        qrcode_key = uuid.uuid4().hex[:32]
        qrcode_url = f"/api/v1/factories/bind?key={qrcode_key}"

        factory.qrcode = qrcode_url
        factory.qrcode_key = qrcode_key
        factory.save()

        return {
            'qrcode': qrcode_url,
            'qrcode_key': qrcode_key
        }

    @staticmethod
    def get_factory_by_qrcode_key(qrcode_key):
        """根据二维码标识获取工厂"""
        from app.models.system.factory import Factory
        return Factory.query.filter_by(qrcode_key=qrcode_key, is_deleted=0).first()

    @staticmethod
    def bind_user_to_factory(user_id, qrcode_key):
        """用户扫码绑定工厂"""
        from app.models.system.user_factory import UserFactory
        from datetime import datetime

        factory = FactoryService.get_factory_by_qrcode_key(qrcode_key)
        if not factory:
            return None, '二维码无效或已过期'

        if factory.status != 1:
            return None, '工厂已禁用，无法绑定'

        existing = UserFactory.query.filter_by(
            user_id=user_id, factory_id=factory.id, is_deleted=0
        ).first()

        if existing:
            return None, '您已绑定该工厂'

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory.id,
            relation_type='employee',
            status=1,
            entry_date=datetime.now().date(),
            remark='通过二维码扫码绑定'
        )
        user_factory.save()

        return {
            'factory_id': factory.id,
            'factory_name': factory.name,
            'factory_code': factory.code
        }, None
