"""客户账号、客户主体关联和客户订单服务。"""

import secrets
import string
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.constants.identity import (
    CUSTOMER_INVITE_EXPIRE_MONTH,
    CUSTOMER_INVITE_EXPIRE_WEEK,
    CUSTOMER_INVITE_EXPIRE_YEAR,
    CUSTOMER_INVITE_STATUS_ACTIVE,
    CUSTOMER_INVITE_STATUS_EXPIRED,
    CUSTOMER_RELATION_STATUS_ACTIVE,
    CUSTOMER_RELATION_STATUS_INACTIVE,
    CUSTOMER_TIER_FREE,
    USER_TYPE_CUSTOMER,
)
from app.extensions import bcrypt, db
from app.models.business.order import Order
from app.models.customer.customer import CustomerInviteCode, CustomerSubjectRelation, CustomerUser
from app.models.system.factory import Factory
from app.utils.datetime_helper import safe_isoformat


class CustomerService:
    """封装客户注册登录、邀请码关联、工厂客户管理和客户订单查询。"""

    INVITE_EXPIRE_DELTA = {
        CUSTOMER_INVITE_EXPIRE_WEEK: timedelta(days=7),
        CUSTOMER_INVITE_EXPIRE_MONTH: timedelta(days=30),
        CUSTOMER_INVITE_EXPIRE_YEAR: timedelta(days=365),
    }

    @staticmethod
    def serialize_customer(customer):
        """序列化客户账号基础信息，不暴露密码。"""
        return {
            'id': customer.id,
            'phone': customer.phone,
            'name': customer.name,
            'status': customer.status,
            'tier': customer.tier,
            'quota_limit': customer.quota_limit,
            'created_by_subject_id': customer.created_by_subject_id,
            'create_time': safe_isoformat(customer.create_time),
            'update_time': safe_isoformat(customer.update_time),
        }

    @staticmethod
    def serialize_subject(subject):
        """序列化客户可见的主体信息。"""
        return {
            'id': subject.id,
            'name': subject.name,
            'code': subject.code,
            'subject_category': getattr(subject, 'subject_category', None),
            'subject_label': getattr(subject, 'subject_label', None),
            'contact_person': subject.contact_person,
            'contact_phone': subject.contact_phone,
            'service_status': subject.service_status,
        }

    @staticmethod
    def serialize_relation(relation):
        """序列化客户与主体的关联关系。"""
        subject = relation.subject
        return {
            'id': relation.id,
            'customer_id': relation.customer_id,
            'subject_id': relation.subject_id,
            'status': relation.status,
            'created_via': relation.created_via,
            'create_time': safe_isoformat(relation.create_time),
            'subject': CustomerService.serialize_subject(subject) if subject else None,
        }

    @staticmethod
    def serialize_order_for_customer(order):
        """序列化客户侧订单信息，只返回客户可看的订单摘要。"""
        subject = order.subject or order.factory
        return {
            'id': order.id,
            'order_no': order.order_no,
            'subject_id': order.subject_id or order.factory_id,
            'subject_name': subject.name if subject else None,
            'customer_user_id': order.customer_user_id,
            'customer_name': order.customer_name,
            'order_date': safe_isoformat(order.order_date),
            'delivery_date': safe_isoformat(order.delivery_date),
            'expected_finish_at': safe_isoformat(order.expected_finish_at),
            'status': order.status,
            'status_label': order.get_status_label(),
            'total_quantity': order.total_quantity,
            'completed_quantity': order.completed_quantity,
            'create_time': safe_isoformat(order.create_time),
        }

    @staticmethod
    def build_claims(customer):
        """构建客户账号 JWT claims。"""
        return {
            'account_type': 'customer',
            'user_type': USER_TYPE_CUSTOMER,
            'customer_id': customer.id,
            'phone': customer.phone,
        }

    @staticmethod
    def create_tokens(customer):
        """为客户账号生成 access token 和 refresh token。"""
        claims = CustomerService.build_claims(customer)
        identity = f'customer:{customer.id}'
        return (
            create_access_token(identity=identity, additional_claims=claims),
            create_refresh_token(identity=identity, additional_claims=claims),
        )

    @staticmethod
    def get_current_customer():
        """从当前请求 JWT 中取客户账号对象。"""
        try:
            claims = get_jwt()
            customer_id = claims.get('customer_id')
            if claims.get('account_type') != 'customer' or not customer_id:
                return None
            return CustomerUser.query.filter_by(id=customer_id, status='active', is_deleted=0).first()
        except Exception:
            return None

    @staticmethod
    def register_customer(data, created_by_subject_id=None):
        """注册客户账号；工厂代注册时记录创建主体。"""
        phone = data['phone'].strip()
        name = data.get('name') or phone
        if CustomerUser.query.filter_by(phone=phone, is_deleted=0).first():
            return None, '手机号已注册'

        customer = CustomerUser(
            phone=phone,
            name=name,
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            status='active',
            tier=CUSTOMER_TIER_FREE,
            created_by_subject_id=created_by_subject_id,
        )
        customer.save()
        return customer, None

    @staticmethod
    def authenticate(phone, password):
        """校验客户手机号和密码。"""
        customer = CustomerUser.query.filter_by(phone=phone, status='active', is_deleted=0).first()
        if not customer or not bcrypt.check_password_hash(customer.password, password):
            return None, '手机号或密码错误'
        return customer, None

    @staticmethod
    def generate_code(length=12):
        """生成唯一客户邀请码。"""
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not CustomerInviteCode.query.filter_by(code=code).first():
                return code

    @staticmethod
    def create_invite_code(subject_id, expire_type):
        """为主体生成可复用客户邀请码。"""
        if expire_type not in CustomerService.INVITE_EXPIRE_DELTA:
            return None, '邀请码有效期类型不正确'

        subject = Factory.query.filter_by(id=subject_id, is_deleted=0).first()
        if not subject:
            return None, '主体不存在'

        now = datetime.now()
        invite = CustomerInviteCode(
            subject_id=subject_id,
            code=CustomerService.generate_code(),
            expire_type=expire_type,
            expire_at=now + CustomerService.INVITE_EXPIRE_DELTA[expire_type],
            status=CUSTOMER_INVITE_STATUS_ACTIVE,
        )
        invite.save()
        return invite, None

    @staticmethod
    def get_invite_for_use(code):
        """查询邀请码并自动处理过期状态。"""
        invite = CustomerInviteCode.query.filter_by(code=code, is_deleted=0).first()
        if not invite:
            return None, '邀请码无效'
        if invite.expire_at < datetime.now():
            invite.status = CUSTOMER_INVITE_STATUS_EXPIRED
            db.session.commit()
            return None, '邀请码已失效，请联系工厂获取新二维码'
        if invite.status != CUSTOMER_INVITE_STATUS_ACTIVE:
            return None, '邀请码已失效，请联系工厂获取新二维码'
        return invite, None

    @staticmethod
    def bind_customer_to_subject(customer_id, subject_id, created_via, created_by=None):
        """建立客户与主体的有效关联，已有失效关系会重新启用。"""
        subject = Factory.query.filter_by(id=subject_id, is_deleted=0).first()
        if not subject:
            return None, '主体不存在'

        relation = CustomerSubjectRelation.query.filter_by(
            customer_id=customer_id,
            subject_id=subject_id,
            is_deleted=0,
        ).first()
        if relation:
            relation.status = CUSTOMER_RELATION_STATUS_ACTIVE
            relation.created_via = relation.created_via or created_via
            relation.save()
            return relation, None

        relation = CustomerSubjectRelation(
            customer_id=customer_id,
            subject_id=subject_id,
            status=CUSTOMER_RELATION_STATUS_ACTIVE,
            created_via=created_via,
            created_by=created_by,
        )
        relation.save()
        return relation, None

    @staticmethod
    def confirm_invite(customer_id, code):
        """客户扫码确认关联主体。"""
        invite, error = CustomerService.get_invite_for_use(code)
        if error:
            return None, error
        return CustomerService.bind_customer_to_subject(
            customer_id=customer_id,
            subject_id=invite.subject_id,
            created_via='qrcode',
            created_by=customer_id,
        )

    @staticmethod
    def get_customer_subjects(customer_id):
        """查询客户已关联的主体列表。"""
        return CustomerSubjectRelation.query.options(selectinload(CustomerSubjectRelation.subject)).filter_by(
            customer_id=customer_id,
            status=CUSTOMER_RELATION_STATUS_ACTIVE,
            is_deleted=0,
        ).order_by(CustomerSubjectRelation.id.desc()).all()

    @staticmethod
    def unbind_customer_subject(customer_id, subject_id):
        """客户主动解除与主体的关联。"""
        relation = CustomerSubjectRelation.query.filter_by(
            customer_id=customer_id,
            subject_id=subject_id,
            status=CUSTOMER_RELATION_STATUS_ACTIVE,
            is_deleted=0,
        ).first()
        if not relation:
            return False, '关联关系不存在'
        relation.status = CUSTOMER_RELATION_STATUS_INACTIVE
        relation.save()
        return True, None

    @staticmethod
    def get_subject_customers(subject_id, filters):
        """分页查询主体客户列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        keyword = (filters.get('keyword') or '').strip()
        status = filters.get('status')

        query = CustomerSubjectRelation.query.options(selectinload(CustomerSubjectRelation.customer)).filter_by(
            subject_id=subject_id,
            is_deleted=0,
        )
        if status:
            query = query.filter(CustomerSubjectRelation.status == status)
        if keyword:
            query = query.join(CustomerUser).filter(
                or_(CustomerUser.phone.like(f'%{keyword}%'), CustomerUser.name.like(f'%{keyword}%'))
            )

        pagination = query.order_by(CustomerSubjectRelation.id.desc()).paginate(
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
        }

    @staticmethod
    def create_or_bind_customer_for_subject(subject_id, data):
        """主体后台代注册或绑定客户。"""
        phone = data['phone'].strip()
        customer = CustomerUser.query.filter_by(phone=phone, is_deleted=0).first()
        initial_password = None
        if not customer:
            initial_password = data.get('password') or phone[-6:] or '123456'
            customer, error = CustomerService.register_customer(
                {
                    'phone': phone,
                    'name': data.get('name') or phone,
                    'password': initial_password,
                },
                created_by_subject_id=subject_id,
            )
            if error:
                return None, None, None, error

        relation, error = CustomerService.bind_customer_to_subject(
            customer_id=customer.id,
            subject_id=subject_id,
            created_via='admin',
            created_by=subject_id,
        )
        if error:
            return None, None, None, error
        return customer, relation, initial_password, None

    @staticmethod
    def subject_unbind_customer(subject_id, customer_id):
        """主体后台解除客户关联。"""
        relation = CustomerSubjectRelation.query.filter_by(
            customer_id=customer_id,
            subject_id=subject_id,
            status=CUSTOMER_RELATION_STATUS_ACTIVE,
            is_deleted=0,
        ).first()
        if not relation:
            return False, '客户关联不存在'
        relation.status = CUSTOMER_RELATION_STATUS_INACTIVE
        relation.save()
        return True, None

    @staticmethod
    def get_customer_order_list(customer_id, filters):
        """分页查询客户自己的订单。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        status = filters.get('status')
        subject_id = filters.get('subject_id')

        query = Order.query.options(selectinload(Order.subject), selectinload(Order.factory)).filter_by(
            customer_user_id=customer_id,
            is_deleted=0,
        )
        if status:
            query = query.filter(Order.status == status)
        if subject_id:
            query = query.filter(or_(Order.subject_id == subject_id, Order.factory_id == subject_id))

        pagination = query.order_by(Order.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def get_customer_order_detail(customer_id, order_id):
        """查询客户自己的订单详情。"""
        return Order.query.options(selectinload(Order.subject), selectinload(Order.factory)).filter_by(
            id=order_id,
            customer_user_id=customer_id,
            is_deleted=0,
        ).first()
