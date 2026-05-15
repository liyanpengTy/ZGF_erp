"""工厂管理接口。"""

from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.system.factory import FactoryCreateSchema, FactorySchema, FactoryUpdateSchema
from app.services import FactoryService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

factory_ns = Namespace('工厂管理-factories', description='工厂管理')

common = get_common_models(factory_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']

factory_query_parser = page_parser.copy()
factory_query_parser.add_argument('name', type=str, location='args', help='工厂名称（模糊查询）')
factory_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

factory_user_query_parser = page_parser.copy()
factory_user_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
factory_user_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
factory_user_query_parser.add_argument(
    'relation_type',
    type=str,
    location='args',
    help='关系类型',
    choices=['owner', 'employee', 'customer', 'collaborator']
)
factory_user_query_parser.add_argument(
    'collaborator_type',
    type=str,
    location='args',
    help='协作类型',
    choices=['button_partner', 'shrink_partner', 'print_partner', 'other_partner']
)

factory_create_model = factory_ns.model('FactoryCreate', {
    'name': fields.String(required=True, description='工厂名称', example='测试工厂'),
    'code': fields.String(required=True, description='工厂编码', example='TEST001'),
    'contact_person': fields.String(description='联系人', example='张三'),
    'contact_phone': fields.String(description='联系电话', example='13800138000'),
    'address': fields.String(description='地址', example='广东省深圳市南山区'),
    'service_expire_date': fields.String(description='服务到期日期', example='2026-12-31'),
    'remark': fields.String(description='备注')
})

factory_update_model = factory_ns.model('FactoryUpdate', {
    'name': fields.String(description='工厂名称'),
    'contact_person': fields.String(description='联系人'),
    'contact_phone': fields.String(description='联系电话'),
    'address': fields.String(description='地址'),
    'service_expire_date': fields.String(description='服务到期日期', example='2026-12-31'),
    'status': fields.Integer(description='状态', choices=[0, 1]),
    'remark': fields.String(description='备注')
})

add_user_model = factory_ns.model('AddUser', {
    'user_id': fields.Integer(required=True, description='用户ID', example=1),
    'relation_type': fields.String(required=True, description='关系类型', choices=['owner', 'employee', 'customer', 'collaborator']),
    'collaborator_type': fields.String(description='协作类型，仅 relation_type=collaborator 时使用', choices=['button_partner', 'shrink_partner', 'print_partner', 'other_partner'])
})

qrcode_response_data = factory_ns.model('QRCodeResponseData', {
    'qrcode': fields.String(description='二维码内容或地址', example='factory-bind://TEST001?key=abc123'),
    'qrcode_key': fields.String(description='二维码绑定键值', example='abc123')
})

qrcode_response = factory_ns.clone('QRCodeResponse', base_response, {
    'data': fields.Nested(qrcode_response_data, description='二维码数据')
})

bind_factory_model = factory_ns.model('BindFactory', {
    'key': fields.String(required=True, description='二维码标识')
})

bind_response_data = factory_ns.model('BindResponseData', {
    'factory_id': fields.Integer(description='工厂ID', example=1),
    'factory_name': fields.String(description='工厂名称', example='测试工厂'),
    'factory_code': fields.String(description='工厂编码', example='TEST001')
})

bind_response = factory_ns.clone('BindResponse', base_response, {
    'data': fields.Nested(bind_response_data, description='绑定结果数据')
})

factory_item_model = factory_ns.model('FactoryItem', {
    'id': fields.Integer(description='工厂ID', example=1),
    'name': fields.String(description='工厂名称', example='测试工厂'),
    'code': fields.String(description='工厂编码', example='TEST001'),
    'contact_person': fields.String(description='联系人', example='张三'),
    'contact_phone': fields.String(description='联系电话', example='13800138000'),
    'address': fields.String(description='地址', example='广东省深圳市南山区'),
    'status': fields.Integer(description='状态', example=1),
    'qrcode': fields.String(description='工厂二维码', example=None),
    'remark': fields.String(description='备注', example=None),
    'service_expire_date': fields.String(description='服务到期日期', example=None),
    'service_status': fields.String(description='服务状态', example='active'),
    'create_time': fields.String(description='创建时间', example='2026-04-21 01:17:24'),
    'update_time': fields.String(description='更新时间', example='2026-04-21 01:17:24')
})

factory_list_data = factory_ns.model('FactoryListData', {
    'items': fields.List(fields.Nested(factory_item_model), description='工厂列表'),
    'total': fields.Integer(description='总条数'),
    'page': fields.Integer(description='当前页码'),
    'page_size': fields.Integer(description='每页条数'),
    'pages': fields.Integer(description='总页数')
})

factory_create_response_data = factory_ns.model('FactoryCreateResponseData', {
    'id': fields.Integer(description='工厂ID', example=1),
    'name': fields.String(description='工厂名称', example='测试工厂'),
    'code': fields.String(description='工厂编码', example='TEST001'),
    'contact_person': fields.String(description='联系人', example='张三'),
    'contact_phone': fields.String(description='联系电话', example='13800138000'),
    'address': fields.String(description='地址', example='广东省深圳市南山区'),
    'status': fields.Integer(description='状态', example=1),
    'remark': fields.String(description='备注', example=None),
    'service_expire_date': fields.String(description='服务到期日期', example='2026-12-31'),
    'service_status': fields.String(description='服务状态', example='active'),
    'create_time': fields.String(description='创建时间', example='2026-04-21 01:17:24'),
    'update_time': fields.String(description='更新时间', example='2026-04-21 01:17:24'),
    'admin_username': fields.String(description='默认管理员账号', example='factory_admin'),
    'admin_password': fields.String(description='默认管理员密码', example='123456')
})

user_item_model = factory_ns.model('FactoryUserItem', {
    'id': fields.Integer(description='用户ID', example=2),
    'username': fields.String(description='用户名', example='factory_admin'),
    'nickname': fields.String(description='昵称', example='工厂管理员'),
    'phone': fields.String(description='手机号', example='18370601281'),
    'status': fields.Integer(description='状态', example=1),
    'platform_identity': fields.String(description='平台身份', example='external_user'),
    'platform_identity_label': fields.String(description='平台身份名称', example='外部人员'),
    'subject_type': fields.String(description='主体类型', example='individual_subject'),
    'subject_type_label': fields.String(description='主体类型名称', example='个人主体'),
    'relation_type': fields.String(description='关联关系类型', example='employee'),
    'relation_type_label': fields.String(description='关联关系名称', example='工厂员工'),
    'collaborator_type': fields.String(description='协作方类型', example=None),
    'collaborator_type_label': fields.String(description='协作方类型名称', example=None),
    'entry_date': fields.String(description='入厂日期', example='2026-04-21'),
    'leave_date': fields.String(description='离厂日期', example=None)
})

user_list_data = factory_ns.model('FactoryUserListData', {
    'items': fields.List(fields.Nested(user_item_model), description='工厂用户列表'),
    'total': fields.Integer(description='总条数'),
    'page': fields.Integer(description='当前页码'),
    'page_size': fields.Integer(description='每页条数'),
    'pages': fields.Integer(description='总页数')
})

factory_list_response = factory_ns.clone('FactoryListResponse', base_response, {
    'data': fields.Nested(factory_list_data, description='工厂分页数据')
})
factory_item_response = factory_ns.clone('FactoryItemResponse', base_response, {
    'data': fields.Nested(factory_item_model, description='工厂详情数据')
})
factory_create_response = factory_ns.clone('FactoryCreateResponse', base_response, {
    'data': fields.Nested(factory_create_response_data, description='工厂创建结果数据')
})
user_list_response = factory_ns.clone('FactoryUserListResponse', base_response, {
    'data': fields.Nested(user_list_data, description='工厂用户分页数据')
})
user_item_response = factory_ns.clone('FactoryUserItemResponse', base_response, {
    'data': fields.Nested(user_item_model, description='工厂用户详情数据')
})

factory_schema = FactorySchema()
factories_schema = FactorySchema(many=True)
factory_create_schema = FactoryCreateSchema()
factory_update_schema = FactoryUpdateSchema()


@factory_ns.route('')
class FactoryList(Resource):
    @login_required
    @factory_ns.expect(factory_query_parser)
    @factory_ns.response(200, '成功', factory_list_response)
    @factory_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询工厂列表，仅平台内部人员可访问。"""
        args = factory_query_parser.parse_args()
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')
        if not current_user.is_internal_user:
            return ApiResponse.error('无权限查看工厂列表', 403)

        result = FactoryService.get_factory_list(args)
        return ApiResponse.success({
            'items': factories_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @factory_ns.expect(factory_create_model)
    @factory_ns.response(201, '创建成功', factory_create_response)
    @factory_ns.response(400, '参数错误', error_response)
    @factory_ns.response(403, '只有平台管理员可创建', forbidden_response)
    @factory_ns.response(409, '工厂编码已存在', error_response)
    def post(self):
        """创建工厂及其默认管理员账号。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以创建工厂', 403)

        try:
            data = factory_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        factory, factory_admin, error = FactoryService.create_factory(data, current_user.id)
        if error:
            return ApiResponse.error(error, 409)

        result = factory_schema.dump(factory)
        result['admin_username'] = factory_admin.username
        result['admin_password'] = '123456'
        return ApiResponse.success(result, '创建成功', 201)


@factory_ns.route('/<int:factory_id>')
class FactoryDetail(Resource):
    @login_required
    @factory_ns.response(200, '成功', factory_item_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def get(self, factory_id):
        """查看单个工厂详情。"""
        current_user = get_current_user()
        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        has_permission, error = FactoryService.check_factory_permission(current_user, factory_id)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(factory_schema.dump(factory))

    @login_required
    @factory_ns.expect(factory_update_model)
    @factory_ns.response(200, '更新成功', factory_item_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def patch(self, factory_id):
        """更新工厂基础信息和服务到期信息。"""
        current_user = get_current_user()
        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以更新工厂', 403)

        try:
            data = factory_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        factory = FactoryService.update_factory(factory, data)
        return ApiResponse.success(factory_schema.dump(factory), '更新成功')

    @login_required
    @factory_ns.response(200, '删除成功', base_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    @factory_ns.response(403, '只有平台管理员可删除', forbidden_response)
    @factory_ns.response(409, '存在关联用户无法删除', error_response)
    def delete(self, factory_id):
        """删除工厂，删除前会校验是否还有关联用户。"""
        current_user = get_current_user()
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以删除工厂', 403)

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        success, error = FactoryService.delete_factory(factory)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')


@factory_ns.route('/<int:factory_id>/users')
class FactoryUsers(Resource):
    @login_required
    @factory_ns.expect(factory_user_query_parser)
    @factory_ns.response(200, '成功', user_list_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def get(self, factory_id):
        """查询工厂下的用户列表，并支持关系类型和协作类型过滤。"""
        args = factory_user_query_parser.parse_args()
        current_user = get_current_user()
        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        has_permission, error = FactoryService.check_factory_permission(current_user, factory_id)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = FactoryService.get_factory_users(factory_id, args)
        return ApiResponse.success(result)

    @login_required
    @factory_ns.expect(add_user_model)
    @factory_ns.response(200, '添加成功', user_item_response)
    @factory_ns.response(403, '无权限', forbidden_response)
    @factory_ns.response(404, '用户不存在', error_response)
    @factory_ns.response(409, '用户已关联', error_response)
    def post(self, factory_id):
        """向工厂新增用户关系，支持 owner、employee、customer、collaborator。"""
        current_user = get_current_user()
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以添加工厂用户', 403)

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        data = request.get_json() or {}
        user_id = data.get('user_id')
        relation_type = data.get('relation_type')
        collaborator_type = data.get('collaborator_type')

        if not user_id or not relation_type:
            return ApiResponse.error('请指定用户ID和关系类型', 400)

        if relation_type == 'owner':
            user_factory, error = FactoryService.update_factory_owner(factory_id, user_id)
        else:
            user_factory, error = FactoryService.add_user_to_factory(
                factory_id,
                user_id,
                relation_type,
                collaborator_type=collaborator_type
            )

        if error:
            status_code = 409 if '已关联' in error or '已经是' in error else 404
            return ApiResponse.error(error, status_code)

        user = user_factory.user
        return ApiResponse.success({
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'phone': user.phone,
            'status': user.status,
            'platform_identity': user.platform_identity,
            'platform_identity_label': user.platform_identity_label,
            'subject_type': user.get_subject_type([user_factory.relation_type]),
            'subject_type_label': user.get_subject_type_label([user_factory.relation_type]),
            'relation_type': user_factory.relation_type,
            'relation_type_label': user_factory.relation_type_label,
            'collaborator_type': user_factory.collaborator_type,
            'collaborator_type_label': user_factory.collaborator_type_label,
            'entry_date': datetime.now().date().isoformat(),
            'leave_date': None
        }, '添加成功')


@factory_ns.route('/<int:factory_id>/users/<int:user_id>')
class FactoryUserDetail(Resource):
    @login_required
    @factory_ns.response(200, '移除成功', base_response)
    @factory_ns.response(403, '无权限', forbidden_response)
    @factory_ns.response(404, '关联不存在', error_response)
    def delete(self, factory_id, user_id):
        """从工厂中移除指定用户关系。"""
        current_user = get_current_user()
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以移除工厂用户', 403)

        success, error = FactoryService.remove_user_from_factory(factory_id, user_id)
        if not success:
            return ApiResponse.error(error, 404)
        return ApiResponse.success(message='移除成功')


@factory_ns.route('/<int:factory_id>/owner')
class FactoryOwner(Resource):
    @login_required
    @factory_ns.response(200, '成功', user_item_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def get(self, factory_id):
        """查询工厂当前管理员账号信息。"""
        current_user = get_current_user()
        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        has_permission, error = FactoryService.check_factory_permission(current_user, factory_id)
        if not has_permission:
            return ApiResponse.error(error, 403)

        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return ApiResponse.error('工厂管理员账号不存在', 404)

        return ApiResponse.success({
            'id': owner.id,
            'username': owner.username,
            'nickname': owner.nickname,
            'phone': owner.phone,
            'status': owner.status,
            'platform_identity': owner.platform_identity,
            'platform_identity_label': owner.platform_identity_label,
            'subject_type': owner.get_subject_type(['owner']),
            'subject_type_label': owner.get_subject_type_label(['owner']),
            'relation_type': 'owner',
            'relation_type_label': '工厂管理员',
            'collaborator_type': None,
            'collaborator_type_label': None,
            'entry_date': None,
            'leave_date': None
        })


@factory_ns.route('/<int:factory_id>/owner/reset-password')
class FactoryOwnerResetPassword(Resource):
    @login_required
    @factory_ns.response(200, '重置成功', base_response)
    @factory_ns.response(403, '无权限', forbidden_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def post(self, factory_id):
        """重置工厂管理员密码为默认值。"""
        current_user = get_current_user()
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以重置工厂管理员密码', 403)

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        success, error = FactoryService.reset_owner_password(factory_id)
        if not success:
            return ApiResponse.error(error, 404)
        return ApiResponse.success(message='密码已重置为 123456')


@factory_ns.route('/<int:factory_id>/qrcode')
class FactoryQRCode(Resource):
    @login_required
    @factory_ns.response(200, '成功', qrcode_response)
    @factory_ns.response(403, '无权限', forbidden_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def post(self, factory_id):
        """为工厂生成新的绑定二维码。"""
        current_user = get_current_user()
        if not current_user.is_platform_admin:
            return ApiResponse.error('只有平台管理员可以生成二维码', 403)

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        result = FactoryService.generate_qrcode(factory)
        return ApiResponse.success(result, '二维码生成成功')


@factory_ns.route('/bind')
class BindFactory(Resource):
    @factory_ns.expect(bind_factory_model)
    @factory_ns.response(200, '绑定成功', bind_response)
    @factory_ns.response(400, '参数错误', error_response)
    @factory_ns.response(401, '未登录', unauthorized_response)
    @factory_ns.response(404, '二维码无效', error_response)
    def post(self):
        """用户扫码后绑定工厂，默认建立 employee 关系。"""
        data = request.get_json() or {}
        qrcode_key = data.get('key')
        if not qrcode_key:
            return ApiResponse.error('无效的二维码', 400)

        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('请先登录', 401)

        result, error = FactoryService.bind_user_to_factory(current_user.id, qrcode_key)
        if error:
            return ApiResponse.error(error, 404)
        return ApiResponse.success(result, '绑定成功')
