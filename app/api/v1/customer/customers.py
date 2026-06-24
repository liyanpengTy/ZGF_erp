"""客户管理与客户侧接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import Schema, fields as ma_fields, validate

from app.api.common.business_resource_helpers import get_business_request_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.api.common.response_helpers import load_json_or_error, success_mapped_page
from app.api.common.serializers import build_mapping_serializer, safe_isoformat
from app.constants.identity import (
    CUSTOMER_INVITE_EXPIRE_MONTH,
    CUSTOMER_INVITE_EXPIRE_WEEK,
    CUSTOMER_INVITE_EXPIRE_YEAR,
    CUSTOMER_RELATION_STATUS_ACTIVE,
    CUSTOMER_RELATION_STATUS_INACTIVE,
)
from app.services import CustomerService
from app.utils.customer_auth import customer_login_required, get_current_customer
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

customer_ns = Namespace('客户管理-customers', description='客户管理')

common = get_common_models(customer_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']
build_item_response_model = common['build_item_response_model']
build_list_response_model = common['build_list_response_model']


class CustomerRegisterSchema(Schema):
    """客户注册入参。"""

    phone = ma_fields.Str(required=True, validate=validate.Length(min=6, max=20))
    name = ma_fields.Str(validate=validate.Length(max=50))
    password = ma_fields.Str(required=True, validate=validate.Length(min=6, max=64))


class CustomerLoginSchema(Schema):
    """客户登录入参。"""

    phone = ma_fields.Str(required=True, validate=validate.Length(min=6, max=20))
    password = ma_fields.Str(required=True, validate=validate.Length(min=6, max=64))


class InviteCodeCreateSchema(Schema):
    """创建客户邀请码入参。"""

    expire_type = ma_fields.Str(
        required=True,
        validate=validate.OneOf([
            CUSTOMER_INVITE_EXPIRE_WEEK,
            CUSTOMER_INVITE_EXPIRE_MONTH,
            CUSTOMER_INVITE_EXPIRE_YEAR,
        ]),
    )


class SubjectCustomerCreateSchema(Schema):
    """主体后台代注册或绑定客户入参。"""

    phone = ma_fields.Str(required=True, validate=validate.Length(min=6, max=20))
    name = ma_fields.Str(validate=validate.Length(max=50))
    password = ma_fields.Str(validate=validate.Length(min=6, max=64))


customer_register_schema = CustomerRegisterSchema()
customer_login_schema = CustomerLoginSchema()
invite_code_create_schema = InviteCodeCreateSchema()
subject_customer_create_schema = SubjectCustomerCreateSchema()

customer_query_parser = page_parser.copy()
customer_query_parser.add_argument('factory_id', type=int, location='args', help='主体 ID；平台内部人员可传入指定主体过滤')
customer_query_parser.add_argument('keyword', type=str, location='args', help='客户手机号或名称')
customer_query_parser.add_argument(
    'status',
    type=str,
    location='args',
    help='关联状态',
    choices=[CUSTOMER_RELATION_STATUS_ACTIVE, CUSTOMER_RELATION_STATUS_INACTIVE],
)

customer_order_query_parser = page_parser.copy()
customer_order_query_parser.add_argument('subject_id', type=int, location='args', help='主体 ID')
customer_order_query_parser.add_argument(
    'status',
    type=str,
    location='args',
    help='订单状态',
    choices=['pending', 'confirmed', 'processing', 'completed', 'cancelled'],
)

customer_register_model = customer_ns.model('CustomerRegister', {
    'phone': fields.String(required=True, description='手机号', example='13800138000'),
    'name': fields.String(description='客户名称', example='张三客户'),
    'password': fields.String(required=True, description='密码', example='123456'),
})

customer_login_model = customer_ns.model('CustomerLogin', {
    'phone': fields.String(required=True, description='手机号', example='13800138000'),
    'password': fields.String(required=True, description='密码', example='123456'),
})

customer_item_model = customer_ns.model('CustomerItem', {
    'id': fields.Integer(description='客户 ID', example=1),
    'phone': fields.String(description='手机号', example='13800138000'),
    'name': fields.String(description='客户名称', example='张三客户'),
    'status': fields.String(description='状态', example='active'),
    'tier': fields.String(description='客户等级', example='free'),
    'quota_limit': fields.Integer(description='订单数量上限', example=None),
    'created_by_subject_id': fields.Integer(description='代注册主体 ID', example=1),
    'create_time': fields.String(description='创建时间', example='2026-06-05T10:00:00'),
    'update_time': fields.String(description='更新时间', example='2026-06-05T10:00:00'),
})

customer_login_data_model = customer_ns.model('CustomerLoginData', {
    'access_token': fields.String(description='访问令牌'),
    'refresh_token': fields.String(description='刷新令牌'),
    'customer_info': fields.Nested(customer_item_model, description='客户信息'),
})

subject_item_model = customer_ns.model('CustomerSubjectItem', {
    'id': fields.Integer(description='主体 ID', example=1),
    'name': fields.String(description='主体名称', example='测试工厂'),
    'code': fields.String(description='主体编码', example='FAC202606050001'),
    'subject_category': fields.String(description='主体分类', example='factory'),
    'subject_label': fields.String(description='主体标签', example='服装加工厂'),
    'contact_person': fields.String(description='联系人', example='张三'),
    'contact_phone': fields.String(description='联系电话', example='13800138000'),
    'service_status': fields.String(description='服务状态', example='active'),
})

relation_item_model = customer_ns.model('CustomerSubjectRelationItem', {
    'id': fields.Integer(description='关联 ID', example=1),
    'customer_id': fields.Integer(description='客户 ID', example=1),
    'subject_id': fields.Integer(description='主体 ID', example=1),
    'status': fields.String(description='关联状态', example='active'),
    'created_via': fields.String(description='创建方式', example='qrcode'),
    'create_time': fields.String(description='创建时间', example='2026-06-05T10:00:00'),
    'subject': fields.Nested(subject_item_model, description='主体信息'),
})

invite_code_create_model = customer_ns.model('CustomerInviteCodeCreate', {
    'expire_type': fields.String(
        required=True,
        description='有效期类型',
        choices=[CUSTOMER_INVITE_EXPIRE_WEEK, CUSTOMER_INVITE_EXPIRE_MONTH, CUSTOMER_INVITE_EXPIRE_YEAR],
        example='week',
    ),
})

invite_code_item_model = customer_ns.model('CustomerInviteCodeItem', {
    'id': fields.Integer(description='邀请码 ID', example=1),
    'subject_id': fields.Integer(description='主体 ID', example=1),
    'code': fields.String(description='邀请码', example='ABCD1234EFGH'),
    'expire_type': fields.String(description='有效期类型', example='week'),
    'expire_at': fields.String(description='过期时间', example='2026-06-12T10:00:00'),
    'status': fields.String(description='状态', example='active'),
    'subject': fields.Nested(subject_item_model, description='主体信息'),
})

subject_customer_create_model = customer_ns.model('SubjectCustomerCreate', {
    'phone': fields.String(required=True, description='客户手机号', example='13800138000'),
    'name': fields.String(description='客户名称', example='张三客户'),
    'password': fields.String(description='初始密码；不传时默认手机号后 6 位', example='123456'),
})

subject_customer_item_model = customer_ns.model('SubjectCustomerItem', {
    'relation_id': fields.Integer(description='关联 ID', example=1),
    'customer': fields.Nested(customer_item_model, description='客户信息'),
    'status': fields.String(description='关联状态', example='active'),
    'created_via': fields.String(description='创建方式', example='admin'),
    'initial_password': fields.String(description='新建客户初始密码，仅创建时返回', example='123456'),
})

customer_order_item_model = customer_ns.model('CustomerOrderItem', {
    'id': fields.Integer(description='订单 ID', example=1),
    'order_no': fields.String(description='订单号', example='ORD1202606050001'),
    'subject_id': fields.Integer(description='主体 ID', example=1),
    'subject_name': fields.String(description='主体名称', example='测试工厂'),
    'customer_user_id': fields.Integer(description='客户用户 ID', example=1),
    'customer_name': fields.String(description='客户名称', example='张三客户'),
    'order_date': fields.String(description='订单日期', example='2026-06-05'),
    'delivery_date': fields.String(description='交期', example='2026-06-20'),
    'expected_finish_at': fields.String(description='预计完成时间', example='2026-06-18T18:00:00'),
    'status': fields.String(description='订单状态', example='pending'),
    'status_label': fields.String(description='订单状态名称', example='待确认'),
    'total_quantity': fields.Integer(description='订单总数量', example=100),
    'completed_quantity': fields.Integer(description='已完成数量', example=30),
    'create_time': fields.String(description='创建时间', example='2026-06-05T10:00:00'),
})

customer_login_response = customer_ns.clone('CustomerLoginResponse', base_response, {
    'data': fields.Nested(customer_login_data_model, description='客户登录结果'),
})
customer_item_response = build_item_response_model(customer_ns, 'CustomerItemResponse', base_response, customer_item_model, '客户信息')
relation_item_response = build_item_response_model(customer_ns, 'CustomerRelationItemResponse', base_response, relation_item_model, '客户主体关联信息')
relation_list_response = build_list_response_model(customer_ns, 'CustomerRelationListResponse', base_response, relation_item_model, '客户已关联主体列表')
invite_code_response = build_item_response_model(customer_ns, 'CustomerInviteCodeResponse', base_response, invite_code_item_model, '客户邀请码信息')
subject_customer_page_data = build_page_data_model(
    customer_ns,
    'SubjectCustomerPageData',
    subject_customer_item_model,
    items_description='主体客户列表',
)
subject_customer_page_response = build_page_response_model(
    customer_ns,
    'SubjectCustomerPageResponse',
    base_response,
    subject_customer_page_data,
    '主体客户分页数据',
)
subject_customer_item_response = build_item_response_model(customer_ns, 'SubjectCustomerItemResponse', base_response, subject_customer_item_model, '主体客户信息')
customer_order_page_data = build_page_data_model(
    customer_ns,
    'CustomerOrderPageData',
    customer_order_item_model,
    items_description='客户订单列表',
)
customer_order_page_response = build_page_response_model(
    customer_ns,
    'CustomerOrderPageResponse',
    base_response,
    customer_order_page_data,
    '客户订单分页数据',
)
customer_order_item_response = build_item_response_model(customer_ns, 'CustomerOrderItemResponse', base_response, customer_order_item_model, '客户订单详情')


def build_customer_login_payload(customer, access_token, refresh_token):
    """构造客户登录和注册成功返回结构。"""
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'customer_info': CustomerService.serialize_customer(customer),
    }


serialize_invite = build_mapping_serializer(
    {
        'id': 'id',
        'subject_id': 'subject_id',
        'code': 'code',
        'expire_type': 'expire_type',
        'expire_at': ('expire_at', safe_isoformat),
        'status': 'status',
    }
)


def serialize_subject_customer(relation, initial_password=None):
    """序列化主体后台客户列表项。"""
    return {
        'relation_id': relation.id,
        'customer': CustomerService.serialize_customer(relation.customer),
        'status': relation.status,
        'created_via': relation.created_via,
        'initial_password': initial_password,
    }


@customer_ns.route('/auth/register')
class CustomerRegister(Resource):
    @customer_ns.expect(customer_register_model)
    @customer_ns.response(201, '注册成功', customer_login_response)
    @customer_ns.response(400, '参数错误', error_response)
    @customer_ns.response(409, '手机号已注册', error_response)
    def post(self):
        """客户自助注册接口，注册成功后直接返回客户 token。"""
        data, validation_error = load_json_or_error(customer_register_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        customer, error = CustomerService.register_customer(data)
        if error:
            return ApiResponse.error(error, 409)

        access_token, refresh_token = CustomerService.create_tokens(customer)
        return ApiResponse.success(build_customer_login_payload(customer, access_token, refresh_token), '注册成功', 201)


@customer_ns.route('/auth/login')
class CustomerLogin(Resource):
    @customer_ns.expect(customer_login_model)
    @customer_ns.response(200, '登录成功', customer_login_response)
    @customer_ns.response(400, '手机号或密码错误', error_response)
    def post(self):
        """客户手机号密码登录接口。"""
        data, validation_error = load_json_or_error(customer_login_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        customer, error = CustomerService.authenticate(data['phone'], data['password'])
        if error:
            return ApiResponse.error(error, 400)

        access_token, refresh_token = CustomerService.create_tokens(customer)
        return ApiResponse.success(build_customer_login_payload(customer, access_token, refresh_token), '登录成功')


@customer_ns.route('/auth/me')
class CustomerMe(Resource):
    @customer_login_required
    @customer_ns.response(200, '成功', customer_item_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询当前客户账号信息接口。"""
        customer = get_current_customer()
        return ApiResponse.success(CustomerService.serialize_customer(customer))


@customer_ns.route('/invite-codes/<string:code>')
class CustomerInvitePreview(Resource):
    @customer_ns.response(200, '成功', invite_code_response)
    @customer_ns.response(404, '邀请码无效', error_response)
    def get(self, code):
        """查询客户邀请码预览接口，扫码后用于展示将要关联的主体信息。"""
        invite, error = CustomerService.get_invite_for_use(code)
        if error:
            return ApiResponse.error(error, 404)
        data = serialize_invite(invite)
        data['subject'] = CustomerService.serialize_subject(invite.subject) if invite.subject else None
        return ApiResponse.success(data)


@customer_ns.route('/invite-codes/<string:code>/confirm')
class CustomerInviteConfirm(Resource):
    @customer_login_required
    @customer_ns.response(200, '关联成功', relation_item_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(404, '邀请码无效', error_response)
    def post(self, code):
        """客户扫码确认关联主体接口。"""
        customer = get_current_customer()
        relation, error = CustomerService.confirm_invite(customer.id, code)
        if error:
            return ApiResponse.error(error, 404)
        return ApiResponse.success(CustomerService.serialize_relation(relation), '关联成功')


@customer_ns.route('/subjects')
class CustomerSubjects(Resource):
    @customer_login_required
    @customer_ns.response(200, '成功', relation_list_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询客户已关联主体列表接口，用于客户下单前选择工厂。"""
        customer = get_current_customer()
        relations = CustomerService.get_customer_subjects(customer.id)
        return ApiResponse.success_list([CustomerService.serialize_relation(relation) for relation in relations])


@customer_ns.route('/subjects/<int:subject_id>')
class CustomerSubjectDetail(Resource):
    @customer_login_required
    @customer_ns.response(200, '解除成功', base_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(404, '关联不存在', error_response)
    def delete(self, subject_id):
        """客户主动解除与主体的关联接口。"""
        customer = get_current_customer()
        success, error = CustomerService.unbind_customer_subject(customer.id, subject_id)
        if not success:
            return ApiResponse.error(error, 404)
        return ApiResponse.success(message='解除成功')


@customer_ns.route('/orders')
class CustomerOrders(Resource):
    @customer_login_required
    @customer_ns.expect(customer_order_query_parser)
    @customer_ns.response(200, '成功', customer_order_page_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询客户自己的订单列表接口，支持按主体和订单状态过滤。"""
        customer = get_current_customer()
        args = customer_order_query_parser.parse_args()
        result = CustomerService.get_customer_order_list(customer.id, args)
        items = [CustomerService.serialize_order_for_customer(order) for order in result['items']]
        return success_mapped_page(result, items)


@customer_ns.route('/orders/<int:order_id>')
class CustomerOrderDetail(Resource):
    @customer_login_required
    @customer_ns.response(200, '成功', customer_order_item_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(404, '订单不存在', error_response)
    def get(self, order_id):
        """查询客户自己的订单详情接口，只返回客户可见的订单摘要。"""
        customer = get_current_customer()
        order = CustomerService.get_customer_order_detail(customer.id, order_id)
        if not order:
            return ApiResponse.error('订单不存在', 404)
        return ApiResponse.success(CustomerService.serialize_order_for_customer(order))


@customer_ns.route('/subject/invite-codes')
class SubjectInviteCodes(Resource):
    @login_required
    @customer_ns.expect(invite_code_create_model)
    @customer_ns.response(201, '创建成功', invite_code_response)
    @customer_ns.response(400, '参数错误', error_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """主体后台生成客户邀请二维码邀请码接口。"""
        _, current_subject_id, error_response_data = get_business_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(invite_code_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        invite, error = CustomerService.create_invite_code(current_subject_id, data['expire_type'])
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(serialize_invite(invite), '创建成功', 201)


@customer_ns.route('/subject/customers')
class SubjectCustomers(Resource):
    @login_required
    @customer_ns.expect(customer_query_parser)
    @customer_ns.response(200, '成功', subject_customer_page_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """主体后台查询客户列表接口，展示当前主体关联客户。"""
        args = customer_query_parser.parse_args()
        _, current_subject_id, error_response_data = get_business_request_context(
            query_factory_id=args.get('factory_id'),
            allow_internal_without_factory=False,
        )
        if error_response_data:
            return error_response_data

        result = CustomerService.get_subject_customers(current_subject_id, args)
        items = [serialize_subject_customer(relation) for relation in result['items']]
        return success_mapped_page(result, items)

    @login_required
    @customer_ns.expect(subject_customer_create_model)
    @customer_ns.response(201, '绑定成功', subject_customer_item_response)
    @customer_ns.response(400, '参数错误', error_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """主体后台代注册或绑定客户接口。"""
        _, current_subject_id, error_response_data = get_business_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(subject_customer_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        _, relation, initial_password, error = CustomerService.create_or_bind_customer_for_subject(
            current_subject_id,
            data,
        )
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(serialize_subject_customer(relation, initial_password), '绑定成功', 201)


@customer_ns.route('/subject/customers/<int:customer_id>')
class SubjectCustomerDetail(Resource):
    @login_required
    @customer_ns.response(200, '解除成功', base_response)
    @customer_ns.response(401, '未登录', unauthorized_response)
    @customer_ns.response(403, '无权限', forbidden_response)
    @customer_ns.response(404, '客户关联不存在', error_response)
    def delete(self, customer_id):
        """主体后台解除客户关联接口。"""
        _, current_subject_id, error_response_data = get_business_request_context(require_write=True)
        if error_response_data:
            return error_response_data

        success, error = CustomerService.subject_unbind_customer(current_subject_id, customer_id)
        if not success:
            return ApiResponse.error(error, 404)
        return ApiResponse.success(message='解除成功')
