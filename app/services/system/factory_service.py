"""工厂管理服务。"""

from datetime import datetime

from sqlalchemy.orm import joinedload

from app.constants.identity import (
    PLATFORM_IDENTITY_EXTERNAL,
    RELATION_TYPE_COLLABORATOR,
    RELATION_TYPE_EMPLOYEE,
    RELATION_TYPE_OWNER,
)
from app.extensions import bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService


class FactoryService(BaseService):
    """工厂管理服务。"""

    @staticmethod
    def _sync_user_identity(user):
        """在工厂关系变更后刷新用户身份，当前仅保留 platform_identity 单一来源。"""
        if not user.platform_identity:
            user.platform_identity = PLATFORM_IDENTITY_EXTERNAL
        user.save()

    @staticmethod
    def get_factory_by_id(factory_id):
        """按主键查询未删除的工厂。"""
        return Factory.query.filter_by(id=factory_id, is_deleted=0).first()

    @staticmethod
    def get_factory_by_code(code):
        """按工厂编码查询未删除的工厂。"""
        return Factory.query.filter_by(code=code, is_deleted=0).first()

    @staticmethod
    def get_factory_list(filters):
        """按筛选条件分页查询工厂列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        query = Factory.query.filter_by(is_deleted=0)
        if name:
            query = query.filter(Factory.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Factory.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def create_factory(data, current_user_id=None):
        """创建工厂、默认工厂管理员账号以及 owner 关系。"""
        existing = FactoryService.get_factory_by_code(data['code'])
        if existing:
            return None, None, '工厂编码已存在'

        factory = Factory(
            name=data['name'],
            code=data['code'],
            contact_person=data.get('contact_person', ''),
            contact_phone=data.get('contact_phone', ''),
            address=data.get('address', ''),
            remark=data.get('remark', ''),
            status=1,
            service_expire_date=data.get('service_expire_date')
        )
        factory.save()

        existing_user = User.query.filter_by(username=data['code'], is_deleted=0).first()
        if existing_user:
            existing_user.nickname = data['name']
            existing_user.platform_identity = PLATFORM_IDENTITY_EXTERNAL
            existing_user.status = 1
            existing_user.save()
            factory_admin = existing_user
        else:
            factory_admin = User(
                username=data['code'],
                password=bcrypt.generate_password_hash('123456').decode('utf-8'),
                nickname=data['name'],
                platform_identity=PLATFORM_IDENTITY_EXTERNAL,
                status=1
            )
            factory_admin.save()

        old_relation = UserFactory.query.filter_by(user_id=factory_admin.id, factory_id=factory.id, is_deleted=0).first()
        if old_relation:
            old_relation.is_deleted = 1
            old_relation.save()

        user_factory = UserFactory(
            user_id=factory_admin.id,
            factory_id=factory.id,
            relation_type=RELATION_TYPE_OWNER,
            status=1,
            entry_date=datetime.now().date(),
            remark='工厂管理员账户'
        )
        user_factory.save()
        FactoryService._sync_user_identity(factory_admin)

        factory_admin.is_paid = 1
        factory_admin.save()

        if factory_admin.invited_by:
            from app.services.system.reward_service import RewardService

            inviter = User.query.get(factory_admin.invited_by)
            if inviter:
                inviter.invited_count += 1
                inviter.save()
                RewardService.check_and_create_rewards(inviter.id)

        return factory, factory_admin, None

    @staticmethod
    def update_factory(factory, data):
        """更新工厂基础信息，并同步工厂管理员昵称。"""
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
        if 'service_expire_date' in data:
            factory.service_expire_date = data['service_expire_date']
        factory.save()

        if 'name' in data:
            user_factory = UserFactory.query.filter_by(factory_id=factory.id, relation_type=RELATION_TYPE_OWNER, is_deleted=0).first()
            if user_factory:
                owner_user = User.query.filter_by(id=user_factory.user_id, is_deleted=0).first()
                if owner_user:
                    owner_user.nickname = data['name']
                    owner_user.save()
        return factory

    @staticmethod
    def delete_factory(factory):
        """软删除工厂，删除前要求先清理非 owner 关系。"""
        user_count = UserFactory.query.filter_by(factory_id=factory.id, is_deleted=0).filter(
            UserFactory.relation_type != RELATION_TYPE_OWNER
        ).count()
        if user_count > 0:
            return False, f'请先解除工厂关联的用户（共 {user_count} 个）'

        owner_relation = UserFactory.query.filter_by(
            factory_id=factory.id,
            relation_type=RELATION_TYPE_OWNER,
            is_deleted=0
        ).first()
        if owner_relation:
            owner_relation.is_deleted = 1
            owner_relation.save()

        factory.is_deleted = 1
        factory.save()
        return True, None

    @staticmethod
    def check_factory_permission(current_user, factory_id, require_write=False):
        """校验用户是否可以访问或写入目标工厂。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_platform_admin:
            return True, None

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return False, '工厂不存在'

        if current_user.is_internal_user and not require_write:
            return True, None

        user_factory = UserFactory.query.filter_by(
            user_id=current_user.id,
            factory_id=factory_id,
            status=1,
            is_deleted=0
        ).first()
        if not user_factory:
            return False, '无权限查看'
        if require_write and factory.service_status in {'expired', 'disabled'}:
            return False, '当前工厂已过期或被禁用，续期后可继续操作'
        return True, None

    @staticmethod
    def get_factory_users(factory_id, filters):
        """分页查询工厂下的用户，并补齐身份、主体和协作类型信息。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        status = filters.get('status')
        relation_type = filters.get('relation_type')
        collaborator_type = filters.get('collaborator_type')

        query = UserFactory.query.filter_by(factory_id=factory_id, is_deleted=0).options(joinedload(UserFactory.user))
        if relation_type:
            query = query.filter_by(relation_type=relation_type)
        if collaborator_type:
            query = query.filter_by(collaborator_type=collaborator_type)

        pagination = query.order_by(UserFactory.id.desc()).paginate(page=page, per_page=page_size, error_out=False)

        items = []
        for relation in pagination.items:
            user = relation.user
            if username and username not in user.username:
                continue
            if status is not None and user.status != status:
                continue
            items.append({
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'phone': user.phone,
                'status': user.status,
                'platform_identity': user.platform_identity,
                'platform_identity_label': user.platform_identity_label,
                'subject_type': user.get_subject_type([relation.relation_type]),
                'subject_type_label': user.get_subject_type_label([relation.relation_type]),
                'relation_type': relation.relation_type,
                'relation_type_label': relation.relation_type_label,
                'collaborator_type': relation.collaborator_type,
                'collaborator_type_label': relation.collaborator_type_label,
                'entry_date': relation.entry_date.isoformat() if relation.entry_date else None,
                'leave_date': relation.leave_date.isoformat() if relation.leave_date else None
            })

        return {
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def add_user_to_factory(factory_id, user_id, relation_type, collaborator_type=None):
        """把已有用户挂到指定工厂，并按需要记录协作类型。"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None, '用户不存在'

        existing = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).first()
        if existing:
            return None, '用户已关联此工厂'

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory_id,
            relation_type=relation_type,
            collaborator_type=collaborator_type if relation_type == RELATION_TYPE_COLLABORATOR else None,
            status=1,
            entry_date=datetime.now().date()
        )
        user_factory.save()
        FactoryService._sync_user_identity(user)
        return user_factory, None

    @staticmethod
    def update_factory_owner(factory_id, user_id):
        """切换工厂 owner，确保同一工厂只有一个有效 owner。"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None, '用户不存在'

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return None, '工厂不存在'

        existing_owner = UserFactory.query.filter_by(factory_id=factory_id, relation_type=RELATION_TYPE_OWNER, is_deleted=0).first()
        if existing_owner:
            if existing_owner.user_id == user_id:
                return None, '该用户已经是工厂管理员'
            existing_owner.is_deleted = 1
            existing_owner.save()

        existing_relation = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).first()
        if existing_relation:
            existing_relation.relation_type = RELATION_TYPE_OWNER
            existing_relation.collaborator_type = None
            existing_relation.entry_date = datetime.now().date()
            existing_relation.remark = '工厂管理员账户'
            existing_relation.save()
            user_factory = existing_relation
        else:
            user_factory = UserFactory(
                user_id=user_id,
                factory_id=factory_id,
                relation_type=RELATION_TYPE_OWNER,
                status=1,
                entry_date=datetime.now().date(),
                remark='工厂管理员账户'
            )
            user_factory.save()

        if user.nickname != factory.name:
            user.nickname = factory.name
            user.save()
        FactoryService._sync_user_identity(user)
        return user_factory, None

    @staticmethod
    def remove_user_from_factory(factory_id, user_id):
        """移除工厂普通关系用户，owner 关系不允许通过这里删除。"""
        user_factory = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).first()
        if not user_factory:
            return False, '用户未关联此工厂'
        if user_factory.relation_type == RELATION_TYPE_OWNER:
            return False, '不能移除工厂管理员账户'

        user_factory.is_deleted = 1
        user_factory.leave_date = datetime.now().date()
        user_factory.save()
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if user:
            FactoryService._sync_user_identity(user)
        return True, None

    @staticmethod
    def get_factory_owner(factory_id):
        """查询工厂当前有效的管理员账号。"""
        user_factory = UserFactory.query.filter_by(
            factory_id=factory_id,
            relation_type=RELATION_TYPE_OWNER,
            status=1,
            is_deleted=0
        ).first()
        if user_factory:
            return User.query.filter_by(id=user_factory.user_id, is_deleted=0).first()
        return None

    @staticmethod
    def reset_owner_password(factory_id):
        """将工厂管理员密码重置为系统默认密码。"""
        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return False, '工厂管理员账户不存在'
        owner.password = bcrypt.generate_password_hash('123456').decode('utf-8')
        owner.save()
        return True, None

    @staticmethod
    def generate_qrcode(factory):
        """为工厂生成新的绑定二维码地址和二维码 key。"""
        import uuid

        qrcode_key = uuid.uuid4().hex[:32]
        qrcode_url = f'/api/v1/factories/bind?key={qrcode_key}'
        factory.qrcode = qrcode_url
        factory.qrcode_key = qrcode_key
        factory.save()
        return {'qrcode': qrcode_url, 'qrcode_key': qrcode_key}

    @staticmethod
    def get_factory_by_qrcode_key(qrcode_key):
        """通过二维码 key 查询对应工厂。"""
        return Factory.query.filter_by(qrcode_key=qrcode_key, is_deleted=0).first()

    @staticmethod
    def bind_user_to_factory(user_id, qrcode_key):
        """处理扫码绑定工厂，把扫码用户挂为员工关系。"""
        factory = FactoryService.get_factory_by_qrcode_key(qrcode_key)
        if not factory:
            return None, '二维码无效或已过期'
        if factory.status != 1:
            return None, '工厂已禁用，无法绑定'

        existing = UserFactory.query.filter_by(user_id=user_id, factory_id=factory.id, is_deleted=0).first()
        if existing:
            return None, '您已绑定该工厂'

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory.id,
            relation_type=RELATION_TYPE_EMPLOYEE,
            status=1,
            entry_date=datetime.now().date(),
            remark='通过二维码扫码绑定'
        )
        user_factory.save()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if user:
            FactoryService._sync_user_identity(user)

        return {
            'factory_id': factory.id,
            'factory_name': factory.name,
            'factory_code': factory.code
        }, None
