from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.user_factory import UserFactory
from app.utils.response import ApiResponse
from app.schemas.system.factory import FactorySchema, FactoryCreateSchema, FactoryUpdateSchema
from app.schemas.auth.user import UserSchema
from marshmallow import ValidationError
from datetime import datetime
from app.api.v1.shared_models import get_shared_models

factory_ns = Namespace('factories', description='工厂管理')

shared = get_shared_models(factory_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

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
                                       choices=['employee', 'customer', 'collaborator'])

factory_create_model = factory_ns.model('FactoryCreate', {
    'name': fields.String(required=True, description='工厂名称', example='测试工厂', min_length=2, max_length=100),
    'code': fields.String(required=True, description='工厂编码', example='TEST001', min_length=2, max_length=50),
    'contact_person': fields.String(description='联系人', example='张三', max_length=50),
    'contact_phone': fields.String(description='联系电话', example='13800138000', max_length=20),
    'address': fields.String(description='地址', example='广东省深圳市南山区', max_length=255),
    'remark': fields.String(description='备注', max_length=500)
})

factory_update_model = factory_ns.model('FactoryUpdate', {
    'name': fields.String(description='工厂名称', min_length=2, max_length=100),
    'contact_person': fields.String(description='联系人', max_length=50),
    'contact_phone': fields.String(description='联系电话', max_length=20),
    'address': fields.String(description='地址', max_length=255),
    'status': fields.Integer(description='状态', choices=[0, 1]),
    'remark': fields.String(description='备注', max_length=500)
})

add_user_model = factory_ns.model('AddUser', {
    'user_id': fields.Integer(required=True, description='用户ID', example=1),
    'relation_type': fields.String(required=True, description='关系类型',
                                   choices=['employee', 'customer', 'collaborator'])
})

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

factory_schema = FactorySchema()
factories_schema = FactorySchema(many=True)
factory_create_schema = FactoryCreateSchema()
factory_update_schema = FactoryUpdateSchema()
user_schema = UserSchema()


@factory_ns.route('')
class FactoryList(Resource):
    @jwt_required()
    @factory_ns.expect(factory_query_parser)
    @factory_ns.response(200, '成功', factory_list_response)
    @factory_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = factory_query_parser.parse_args()

        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        # 只有公司内部人员可以查看工厂列表
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看工厂列表', 403)

        page = args['page']
        page_size = args['page_size']
        name = args.get('name', '')
        status = args.get('status')

        query = Factory.query.filter_by(is_deleted=0)

        if name:
            query = query.filter(Factory.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Factory.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': factories_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @jwt_required()
    @factory_ns.expect(factory_create_model)
    @factory_ns.response(201, '创建成功', factory_create_response)
    @factory_ns.response(400, '参数错误', error_response)
    @factory_ns.response(403, '只有管理员可以创建', forbidden_response)
    @factory_ns.response(409, '工厂编码已存在', error_response)
    def post(self):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建工厂', 403)

        try:
            data = factory_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        existing_factory = Factory.query.filter_by(code=data['code'], is_deleted=0).first()
        if existing_factory:
            return ApiResponse.error('工厂编码已存在')

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

        # 创建工厂管理员用户
        factory_admin = User(
            username=data['code'],
            password=bcrypt.generate_password_hash('123456').decode('utf-8'),
            nickname=data['name'],
            is_admin=0,
            status=1
        )
        factory_admin.save()

        # 关联用户到工厂（作为员工）
        user_factory = UserFactory(
            user_id=factory_admin.id,
            factory_id=factory.id,
            relation_type='employee',
            status=1,
            entry_date=datetime.now().date()
        )
        user_factory.save()

        result = factory_schema.dump(factory)
        result['admin_username'] = factory_admin.username
        result['admin_password'] = '123456'

        return ApiResponse.success(result, '创建成功', 201)


@factory_ns.route('/<int:factory_id>')
class FactoryDetail(Resource):
    @jwt_required()
    @factory_ns.response(200, '成功', factory_item_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def get(self, factory_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 权限验证
        if current_user.is_admin != 1:
            # 检查用户是否关联该工厂
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id, factory_id=factory_id, status=1, is_deleted=0
            ).first()
            if not user_factory:
                return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(factory_schema.dump(factory))

    @jwt_required()
    @factory_ns.expect(factory_update_model)
    @factory_ns.response(200, '更新成功', factory_item_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def put(self, factory_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 只有公司内部人员可以更新工厂
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限更新', 403)

        try:
            data = factory_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

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

        return ApiResponse.success(factory_schema.dump(factory), '更新成功')

    @jwt_required()
    @factory_ns.response(200, '删除成功', base_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    @factory_ns.response(403, '只有管理员可以删除', forbidden_response)
    @factory_ns.response(409, '存在关联用户无法删除', error_response)
    def delete(self, factory_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除工厂', 403)

        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 检查是否有用户关联该工厂
        user_count = UserFactory.query.filter_by(factory_id=factory_id, is_deleted=0).count()
        if user_count > 0:
            return ApiResponse.error(f'请先解除工厂关联的用户（共 {user_count} 个）')

        factory.delete()

        return ApiResponse.success(message='删除成功')


@factory_ns.route('/<int:factory_id>/users')
class FactoryUsers(Resource):
    @jwt_required()
    @factory_ns.expect(factory_user_query_parser)
    @factory_ns.response(200, '成功', user_list_response)
    @factory_ns.response(404, '工厂不存在', error_response)
    def get(self, factory_id):
        args = factory_user_query_parser.parse_args()

        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        # 权限验证
        if current_user.is_admin != 1:
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id, factory_id=factory_id, status=1, is_deleted=0
            ).first()
            if not user_factory:
                return ApiResponse.error('无权限查看', 403)

        page = args['page']
        page_size = args['page_size']
        username = args.get('username', '')
        status = args.get('status')
        relation_type = args.get('relation_type')

        query = UserFactory.query.filter_by(factory_id=factory_id, is_deleted=0)

        if relation_type:
            query = query.filter_by(relation_type=relation_type)

        # 获取用户ID列表
        user_factory_list = query.all()
        user_ids = [uf.user_id for uf in user_factory_list]

        if not user_ids:
            return ApiResponse.success({
                'items': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'pages': 0
            })

        user_query = User.query.filter(User.id.in_(user_ids), User.is_deleted == 0)

        if username:
            user_query = user_query.filter(User.username.like(f'%{username}%'))
        if status is not None:
            user_query = user_query.filter_by(status=status)

        pagination = user_query.order_by(User.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        # 组装返回数据
        items = []
        for user in pagination.items:
            uf = next((x for x in user_factory_list if x.user_id == user.id), None)
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
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @jwt_required()
    @factory_ns.expect(add_user_model)
    @factory_ns.response(200, '添加成功', user_item_response)
    @factory_ns.response(403, '只有管理员可以添加', forbidden_response)
    @factory_ns.response(404, '用户不存在', error_response)
    @factory_ns.response(409, '用户已关联', error_response)
    def post(self, factory_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以添加用户到工厂', 403)

        factory = Factory.query.filter_by(id=factory_id, is_deleted=0).first()
        if not factory:
            return ApiResponse.error('工厂不存在')

        data = request.get_json()
        user_id = data.get('user_id')
        relation_type = data.get('relation_type')

        if not user_id or not relation_type:
            return ApiResponse.error('请指定用户ID和关系类型', 400)

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        # 检查是否已关联
        existing = UserFactory.query.filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).first()
        if existing:
            return ApiResponse.error('用户已关联此工厂', 409)

        user_factory = UserFactory(
            user_id=user_id,
            factory_id=factory_id,
            relation_type=relation_type,
            status=1,
            entry_date=datetime.now().date()
        )
        user_factory.save()

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
    @jwt_required()
    @factory_ns.response(200, '移除成功', base_response)
    @factory_ns.response(403, '只有管理员可以移除', forbidden_response)
    @factory_ns.response(404, '关联不存在', error_response)
    def delete(self, factory_id, user_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以移除用户', 403)

        user_factory = UserFactory.query.filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).first()

        if not user_factory:
            return ApiResponse.error('用户未关联此工厂', 404)

        # 逻辑删除关联
        user_factory.delete()

        return ApiResponse.success(message='移除成功')
