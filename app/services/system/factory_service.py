"""工厂管理服务。"""

from datetime import datetime
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.constants.identity import (
    PLATFORM_IDENTITY_EXTERNAL,
    RELATION_TYPE_COLLABORATOR,
    RELATION_TYPE_EMPLOYEE,
    RELATION_TYPE_OWNER,
)
from app.extensions import bcrypt, db
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService
from app.services.system.role_service import RoleService


class FactoryService(BaseService):
    """封装工厂、工厂成员和绑定二维码相关业务逻辑。"""

    @staticmethod
    def _sync_user_identity(user):
        """在工厂关系变更后，确保用户具备外部身份。"""
        if not user.platform_identity:
            user.platform_identity = PLATFORM_IDENTITY_EXTERNAL
        user.save()

    @staticmethod
    def get_factory_by_id(factory_id):
        """按主键查询未删除的工厂。"""
        return Factory.query.filter_by(id=factory_id, is_deleted=0).first()

    @staticmethod
    def get_factory_by_code(code):
        """按工厂编码查询工厂，唯一性校验会包含已删除数据。"""
        return Factory.query.filter_by(code=code).first()

    @staticmethod
    def _generate_factory_code():
        """生成工厂编码，格式为 FAC + 日期 + 4 位流水号。"""
        code_prefix = datetime.now().strftime("FAC%Y%m%d")
        latest_factory = (
            Factory.query.filter(Factory.code.like(f"{code_prefix}%"))
            .order_by(Factory.code.desc())
            .first()
        )

        next_sequence = 1
        if latest_factory and latest_factory.code:
            suffix = latest_factory.code[len(code_prefix):]
            if suffix.isdigit():
                next_sequence = int(suffix) + 1

        for sequence in range(next_sequence, 10000):
            candidate_code = f"{code_prefix}{sequence:04d}"
            factory_exists = Factory.query.filter_by(code=candidate_code).first()
            user_exists = User.query.filter_by(username=candidate_code).first()
            if not factory_exists and not user_exists:
                return candidate_code

        raise ValueError("当天工厂编码已达到生成上限")

    @staticmethod
    def get_factory_list(filters):
        """按筛选条件分页查询工厂列表。"""
        page = filters.get("page", 1)
        page_size = filters.get("page_size", 10)
        return_all = filters.get("return_all", False)
        name = filters.get("name", "")
        status = filters.get("status")

        query = Factory.query.filter_by(is_deleted=0)
        if name:
            query = query.filter(Factory.name.like(f"%{name}%"))
        if status is not None:
            query = query.filter_by(status=int(status))

        if return_all:
            items = query.order_by(Factory.id.desc()).all()
            return {
                "items": items,
                "total": len(items),
                "page": 1,
                "page_size": len(items),
                "pages": 1 if items else 0,
            }

        pagination = query.order_by(Factory.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            "items": pagination.items,
            "total": pagination.total,
            "page": page,
            "page_size": page_size,
            "pages": pagination.pages,
        }

    @staticmethod
    def get_factory_options(name=None, status=None):
        """查询工厂下拉选项。"""
        query = Factory.query.filter_by(is_deleted=0)
        if name:
            query = query.filter(Factory.name.like(f"%{name}%"))
        if status is not None:
            query = query.filter_by(status=int(status))
        return query.order_by(Factory.id.desc()).all()

    @staticmethod
    def create_factory(data, current_user_id=None):
        """创建工厂，并自动生成唯一工厂编码和默认管理员账号。"""
        del current_user_id

        for _ in range(5):
            try:
                factory_code = FactoryService._generate_factory_code()
            except ValueError as error:
                return None, None, str(error)

            factory = Factory(
                name=data["name"],
                code=factory_code,
                contact_person=data.get("contact_person", ""),
                contact_phone=data.get("contact_phone", ""),
                address=data.get("address", ""),
                remark=data.get("remark", ""),
                status=1,
                service_expire_date=data.get("service_expire_date"),
            )
            factory_admin = User(
                username=factory_code,
                password=bcrypt.generate_password_hash("123456").decode("utf-8"),
                nickname=data["name"],
                platform_identity=PLATFORM_IDENTITY_EXTERNAL,
                status=1,
                is_paid=1,
            )

            try:
                db.session.add(factory)
                db.session.add(factory_admin)
                db.session.flush()

                user_factory = UserFactory(
                    user_id=factory_admin.id,
                    factory_id=factory.id,
                    relation_type=RELATION_TYPE_OWNER,
                    status=1,
                    entry_date=datetime.now().date(),
                    remark="工厂管理员账号",
                )
                db.session.add(user_factory)
                db.session.commit()
                RoleService.clear_permission_cache()
                return factory, factory_admin, None
            except IntegrityError:
                db.session.rollback()
                continue

        return None, None, "工厂编码生成失败，请稍后重试"

    @staticmethod
    def update_factory(factory, data):
        """更新工厂基础信息，并同步工厂管理员昵称。"""
        if "name" in data:
            factory.name = data["name"]
        if "contact_person" in data:
            factory.contact_person = data["contact_person"]
        if "contact_phone" in data:
            factory.contact_phone = data["contact_phone"]
        if "address" in data:
            factory.address = data["address"]
        if "status" in data:
            factory.status = data["status"]
        if "remark" in data:
            factory.remark = data["remark"]
        if "service_expire_date" in data:
            factory.service_expire_date = data["service_expire_date"]
        factory.save()

        if "name" in data:
            user_factory = UserFactory.query.filter_by(
                factory_id=factory.id,
                relation_type=RELATION_TYPE_OWNER,
                is_deleted=0,
            ).first()
            if user_factory:
                owner_user = User.query.filter_by(id=user_factory.user_id, is_deleted=0).first()
                if owner_user:
                    owner_user.nickname = data["name"]
                    owner_user.save()
        return factory

    @staticmethod
    def delete_factory(factory):
        """软删除工厂，删除前要求先清理非 owner 关系。"""
        user_count = UserFactory.query.filter_by(factory_id=factory.id, is_deleted=0).filter(
            UserFactory.relation_type != RELATION_TYPE_OWNER
        ).count()
        if user_count > 0:
            return False, f"请先解除工厂关联的用户（共 {user_count} 个）"

        owner_relation = UserFactory.query.filter_by(
            factory_id=factory.id,
            relation_type=RELATION_TYPE_OWNER,
            is_deleted=0,
        ).first()
        if owner_relation:
            owner_relation.is_deleted = 1
            owner_relation.save()

        factory.is_deleted = 1
        factory.save()
        RoleService.clear_permission_cache()
        return True, None

    @staticmethod
    def check_factory_permission(current_user, factory_id, require_write=False):
        """校验用户是否可以访问或写入目标工厂。"""
        if not current_user:
            return False, "用户不存在"
        if current_user.is_platform_admin:
            return True, None

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return False, "工厂不存在"

        if current_user.is_internal_user and not require_write:
            return True, None

        user_factory = UserFactory.query.filter_by(
            user_id=current_user.id,
            factory_id=factory_id,
            status=1,
            is_deleted=0,
        ).first()
        if not user_factory:
            return False, "无权限查看"
        if require_write and factory.service_status in {"expired", "disabled"}:
            return False, "当前工厂已过期或被禁用，续期后可继续操作"
        return True, None

    @staticmethod
    def get_factory_users(factory_id, filters):
        """分页查询工厂用户，并补齐身份与关系信息。"""
        page = filters.get("page", 1)
        page_size = filters.get("page_size", 10)
        username = filters.get("username", "")
        status = filters.get("status")
        relation_type = filters.get("relation_type")
        collaborator_type = filters.get("collaborator_type")

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
            items.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "nickname": user.nickname,
                    "phone": user.phone,
                    "status": user.status,
                    "platform_identity": user.platform_identity,
                    "platform_identity_label": user.platform_identity_label,
                    "subject_type": user.get_subject_type([relation.relation_type]),
                    "subject_type_label": user.get_subject_type_label([relation.relation_type]),
                    "relation_type": relation.relation_type,
                    "relation_type_label": relation.relation_type_label,
                    "collaborator_type": relation.collaborator_type,
                    "collaborator_type_label": relation.collaborator_type_label,
                    "entry_date": relation.entry_date.isoformat() if relation.entry_date else None,
                    "leave_date": relation.leave_date.isoformat() if relation.leave_date else None,
                }
            )

        return {
            "items": items,
            "total": pagination.total,
            "page": page,
            "page_size": page_size,
            "pages": pagination.pages,
        }

    @staticmethod
    def add_user_to_factory(factory_id, user_id, relation_type, collaborator_type=None):
        """把已有用户挂到指定工厂。"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None, "用户不存在"

        existing = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).first()
        if existing:
            return None, "用户已关联此工厂"

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory_id,
            relation_type=relation_type,
            collaborator_type=collaborator_type if relation_type == RELATION_TYPE_COLLABORATOR else None,
            status=1,
            entry_date=datetime.now().date(),
        )
        user_factory.save()
        FactoryService._sync_user_identity(user)
        RoleService.clear_permission_cache()
        return user_factory, None

    @staticmethod
    def update_factory_owner(factory_id, user_id):
        """切换工厂 owner，确保同一工厂只有一个有效 owner。"""
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return None, "用户不存在"

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return None, "工厂不存在"

        existing_owner = UserFactory.query.filter_by(
            factory_id=factory_id,
            relation_type=RELATION_TYPE_OWNER,
            is_deleted=0,
        ).first()
        if existing_owner:
            if existing_owner.user_id == user_id:
                return None, "该用户已经是工厂管理员"
            existing_owner.is_deleted = 1
            existing_owner.save()

        existing_relation = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).first()
        if existing_relation:
            existing_relation.relation_type = RELATION_TYPE_OWNER
            existing_relation.collaborator_type = None
            existing_relation.entry_date = datetime.now().date()
            existing_relation.remark = "工厂管理员账号"
            existing_relation.save()
            user_factory = existing_relation
        else:
            user_factory = UserFactory(
                user_id=user_id,
                factory_id=factory_id,
                relation_type=RELATION_TYPE_OWNER,
                status=1,
                entry_date=datetime.now().date(),
                remark="工厂管理员账号",
            )
            user_factory.save()

        if user.nickname != factory.name:
            user.nickname = factory.name
            user.save()
        FactoryService._sync_user_identity(user)
        RoleService.clear_permission_cache()
        return user_factory, None

    @staticmethod
    def remove_user_from_factory(factory_id, user_id):
        """移除工厂普通关系用户，owner 不能通过这里删除。"""
        user_factory = UserFactory.query.filter_by(user_id=user_id, factory_id=factory_id, is_deleted=0).first()
        if not user_factory:
            return False, "用户未关联此工厂"
        if user_factory.relation_type == RELATION_TYPE_OWNER:
            return False, "不能移除工厂管理员账号"

        user_factory.is_deleted = 1
        user_factory.leave_date = datetime.now().date()
        user_factory.save()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if user:
            FactoryService._sync_user_identity(user)
        RoleService.clear_permission_cache()
        return True, None

    @staticmethod
    def get_factory_owner(factory_id):
        """查询工厂当前有效的管理员账号。"""
        user_factory = UserFactory.query.filter_by(
            factory_id=factory_id,
            relation_type=RELATION_TYPE_OWNER,
            status=1,
            is_deleted=0,
        ).first()
        if user_factory:
            return User.query.filter_by(id=user_factory.user_id, is_deleted=0).first()
        return None

    @staticmethod
    def reset_owner_password(factory_id):
        """把工厂管理员密码重置为系统默认密码。"""
        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return False, "工厂管理员账号不存在"
        owner.password = bcrypt.generate_password_hash("123456").decode("utf-8")
        owner.save()
        return True, None

    @staticmethod
    def generate_qrcode(factory):
        """为工厂生成新的绑定二维码地址和 key。"""
        qrcode_key = uuid.uuid4().hex[:32]
        qrcode_url = f"/api/v1/factories/bind?key={qrcode_key}"
        factory.qrcode = qrcode_url
        factory.qrcode_key = qrcode_key
        factory.save()
        return {"qrcode": qrcode_url, "qrcode_key": qrcode_key}

    @staticmethod
    def get_factory_by_qrcode_key(qrcode_key):
        """通过二维码 key 查询对应工厂。"""
        return Factory.query.filter_by(qrcode_key=qrcode_key, is_deleted=0).first()

    @staticmethod
    def bind_user_to_factory(user_id, qrcode_key):
        """处理扫码绑定工厂，默认把扫码用户挂为员工关系。"""
        factory = FactoryService.get_factory_by_qrcode_key(qrcode_key)
        if not factory:
            return None, "二维码无效或已过期"
        if factory.status != 1:
            return None, "工厂已禁用，无法绑定"

        existing = UserFactory.query.filter_by(user_id=user_id, factory_id=factory.id, is_deleted=0).first()
        if existing:
            return None, "您已绑定该工厂"

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory.id,
            relation_type=RELATION_TYPE_EMPLOYEE,
            status=1,
            entry_date=datetime.now().date(),
            remark="通过二维码扫码绑定",
        )
        user_factory.save()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if user:
            FactoryService._sync_user_identity(user)
        RoleService.clear_permission_cache()

        return {
            "factory_id": factory.id,
            "factory_name": factory.name,
            "factory_code": factory.code,
        }, None
