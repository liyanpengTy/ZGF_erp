"""工厂管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.system.factory import FactorySchema, FactoryCreateSchema, FactoryUpdateSchema
from marshmallow import ValidationError
from datetime import datetime
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, FactoryService
from app.models.auth.user import User

factory_ns = Namespace('factories', description='工厂管理')

shared = get_shared_models(factory_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

# ========== 请求解析器 ==========
factory_query_parser = factory_ns.parser()
factory_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
factory_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
factory_query_parser.add_argument('name', type=str, location='args', help='工厂名称（模糊查询）')
factory_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

factory_user_query_parser = factory_ns.parser()
factory_user_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
factory_user_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
factory_user_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
factory_user_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
factory_user_query_parser.add_argument('relation_type', type=str, location='args', help='关系类型',
                                       choices=['owner', 'employee', 'customer', 'collaborator'])

# ========== 请求模型 ==========
factory_create_model = factory_ns.model('FactoryCreate', {
    'name': fields.String(required=True, description='工厂名称', example='测试工厂'),
    'code': fields.String(required=True, description='工厂编码', example='TEST001'),
    'contact_person': fields.String(description='联系人', example='张三'),
    'contact_phone': fields.String(description='联系电话', example='13800138000'),
    'address': fields.String(description='地址', example='广东省深圳市南山区'),
    'remark': fields.String(description='备注')
})

factory_update_model = factory_ns.model('FactoryUpdate', {
    'name': fields.String(description='工厂名称'),
    'contact_person': fields.String(description='联系人'),
    'contact_phone': fields.String(description='联系电话'),
    'address': fields.String(description='地址'),
    'status': fields.Integer(description='状态', choices=[0, 1]),
    'remark': fields.String(description='备注')
})

add_user_model = factory_ns.model('AddUser', {
    'user_id': fields.Integer(required=True, description='用户ID', example=1),
    'relation_type': fields.String(required=True, description='关系类型',
                                   choices=['owner', 'employee', 'customer', 'collaborator'])
})

# ========== 响应模型 ==========
factory_item_model = factory_ns.model('FactoryItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'code': fields.String(),
    'contact_person': fields.String(),
    'contact_phone': fields.String(),
    'address': fields.String(),
    'status': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

factory_list_data = factory_ns.model('FactoryListData', {
    'items': fields.List(fields.Nested(factory_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

factory_create_response_data = factory_ns.model('FactoryCreateResponseData', {
    'id': fields.Integer(),
    'name': fields.String(),
    'code': fields.String(),
    'contact_person': fields.String(),
    'contact_phone': fields.String(),
    'address': fields.String(),
    'status': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String(),
    'admin_username': fields.String(),
    'admin_password': fields.String()
})

user_item_model = factory_ns.model('FactoryUserItem', {
    'id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'phone': fields.String(),
    'status': fields.Integer(),
    'relation_type': fields.String(),
    'entry_date': fields.String(),
    'leave_date': fields.String()
})

user_list_data = factory_ns.model('UserListData', {
    'items': fields.List(fields.Nested(user_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

factory_list_response = factory_ns.clone('FactoryListResponse', base_response, {
    'data': fields.Nested(factory_list_data)
})

factory_item_response = factory_ns.clone('FactoryItemResponse', base_response, {
    'data': fields.Nested(factory_item_model)
})

factory_create_response = factory_ns.clone('FactoryCreateResponse', base_response, {
    'data': fields.Nested(factory_create_response_data)
})

user_list_response = factory_ns.clone('UserListResponse', base_response, {
    'data': fields.Nested(user_list_data)
})

user_item_response = factory_ns.clone('UserItemResponse', base_response, {
    'data': fields.Nested(user_item_model)
})

# ========== Schema 初始化 ==========
factory_schema = FactorySchema()
factories_schema = FactorySchema(many=True)
factory_create_schema = FactoryCreateSchema()
factory_update_schema = FactoryUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@factory_ns.route('')
class FactoryList(Resource):
    @login_required
    @factory_ns.expect(factory_query_parser)
    @factory_ns.response(200, '成功', factory_list_response)
    @factory_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """工厂列表"""
        args = factory_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以查看工厂列表
        if current_user.is_admin != 1:
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
    @factory_ns.response(403, '只有管理员可以创建', forbidden_response)
    @factory_ns.response(409, '工厂编码已存在', error_response)
    def post(self):
        """创建工厂"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建工厂', 403)

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
        """工厂详情"""
        current_user = get_current_user()

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 权限验证
        has_permission, error = FactoryService.check_factory_permission(current_user, factory_id)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(factory_schema.dump(factory))

    @login_required
    @factory_ns.expect(factory_update_model)
    @factory_ns.response(200, '更新成功', factory_item_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def put(self, factory_id):
        """更新工厂信息"""
        current_user = get_current_user()

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 只有公司内部人员可以更新工厂
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限更新', 403)

        try:
            data = factory_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        factory = FactoryService.update_factory(factory, data)

        return ApiResponse.success(factory_schema.dump(factory), '更新成功')

    @login_required
    @factory_ns.response(200, '删除成功', base_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    @factory_ns.response(403, '只有管理员可以删除', forbidden_response)
    @factory_ns.response(409, '存在关联用户无法删除', error_response)
    def delete(self, factory_id):
        """删除工厂"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除工厂', 403)

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
        """获取工厂用户列表"""
        args = factory_user_query_parser.parse_args()
        current_user = get_current_user()

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 权限验证
        has_permission, error = FactoryService.check_factory_permission(current_user, factory_id)
        if not has_permission:
            return ApiResponse.error(error, 403)

        result = FactoryService.get_factory_users(factory_id, args)

        # 组装返回数据
        items = []
        for user in result['items']:
            uf = result['user_factory_map'].get(user.id)
            items.append({
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'phone': user.phone,
                'status': user.status,
                'relation_type': uf.relation_type if uf else None,
                'entry_date': uf.entry_date.isoformat() if uf and uf.entry_date else None,
                'leave_date': uf.leave_date.isoformat() if uf and uf.leave_date else None
            })

        return ApiResponse.success({
            'items': items,
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @factory_ns.expect(add_user_model)
    @factory_ns.response(200, '添加成功', user_item_response)
    @factory_ns.response(403, '只有管理员可以添加', forbidden_response)
    @factory_ns.response(404, '用户不存在', error_response)
    @factory_ns.response(409, '用户已关联', error_response)
    def post(self, factory_id):
        """添加用户到工厂"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以添加用户到工厂', 403)

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        data = request.get_json()
        user_id = data.get('user_id')
        relation_type = data.get('relation_type')

        if not user_id or not relation_type:
            return ApiResponse.error('请指定用户ID和关系类型', 400)

        # 如果是 owner 类型，使用专门的方法
        if relation_type == 'owner':
            # 更新工厂主体关联
            user_factory, error = FactoryService.update_factory_owner(factory_id, user_id)
            if error:
                return ApiResponse.error(error, 409)
        else:
            user_factory, error = FactoryService.add_user_to_factory(factory_id, user_id, relation_type)

        if error:
            return ApiResponse.error(error, 409 if '已关联' in error else 404)

        user = user_factory.user if hasattr(user_factory, 'user') else User.query.get(user_id)

        return ApiResponse.success({
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'phone': user.phone,
            'status': user.status,
            'relation_type': relation_type,
            'entry_date': datetime.now().date().isoformat(),
            'leave_date': None
        }, '添加成功')


@factory_ns.route('/<int:factory_id>/users/<int:user_id>')
class FactoryUserDetail(Resource):
    @login_required
    @factory_ns.response(200, '移除成功', base_response)
    @factory_ns.response(403, '只有管理员可以移除', forbidden_response)
    @factory_ns.response(404, '关联不存在', error_response)
    def delete(self, factory_id, user_id):
        """从工厂移除用户"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以移除用户', 403)

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
        """获取工厂主体账号"""
        current_user = get_current_user()

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 权限验证
        has_permission, error = FactoryService.check_factory_permission(current_user, factory_id)
        if not has_permission:
            return ApiResponse.error(error, 403)

        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return ApiResponse.error('工厂主体账号不存在', 404)

        return ApiResponse.success({
            'id': owner.id,
            'username': owner.username,
            'nickname': owner.nickname,
            'phone': owner.phone,
            'status': owner.status
        })


@factory_ns.route('/<int:factory_id>/owner/reset-password')
class FactoryOwnerResetPassword(Resource):
    @login_required
    @factory_ns.response(200, '重置成功', base_response)
    @factory_ns.response(403, '无权限', forbidden_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def post(self, factory_id):
        """重置工厂主体账号密码"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以重置工厂主体密码', 403)

        factory = FactoryService.get_factory_by_id(factory_id)
        if not factory:
            return ApiResponse.error('工厂不存在')

        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return ApiResponse.error('工厂主体账号不存在', 404)

        # 重置密码为默认密码
        from app.extensions import bcrypt
        owner.password = bcrypt.generate_password_hash('123456').decode('utf-8')
        owner.save()

        return ApiResponse.success(message='密码已重置为 123456')
