from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db, bcrypt
from app.models.auth.user import User
from app.models.system.user_factory import UserFactory
from app.models.system.user_factory_role import UserFactoryRole
from app.models.system.role import Role
from app.utils.response import ApiResponse
from app.schemas.auth.user import UserSchema, UserCreateSchema, UserUpdateSchema, UserResetPasswordSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required

user_ns = Namespace('users', description='用户管理')

shared = get_shared_models(user_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

user_query_parser = user_ns.parser()
user_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
user_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
user_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
user_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
user_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID')

user_create_model = user_ns.model('UserCreate', {
    'username': fields.String(required=True, description='用户名', example='testuser', min_length=3, max_length=50),
    'password': fields.String(required=True, description='密码', example='123456', min_length=6, max_length=20),
    'nickname': fields.String(description='昵称', example='测试用户', max_length=50),
    'phone': fields.String(description='手机号', example='13800138000', max_length=20),
    'is_admin': fields.Integer(description='是否内部人员', example=0, choices=[0, 1]),
})

user_update_model = user_ns.model('UserUpdate', {
    'nickname': fields.String(description='昵称', max_length=50),
    'phone': fields.String(description='手机号', max_length=20),
    'status': fields.Integer(description='状态', example=1, choices=[0, 1])
})

user_reset_password_model = user_ns.model('ResetPassword', {
    'password': fields.String(required=True, description='新密码', example='123456', min_length=6, max_length=20)
})

user_assign_roles_model = user_ns.model('AssignRoles', {
    'role_ids': fields.List(fields.Integer, required=True, description='角色ID列表', example=[1, 2])
})

user_item_model = user_ns.model('UserItem', {
    'id': fields.Integer(),
    'username': fields.String(),
    'nickname': fields.String(),
    'phone': fields.String(),
    'avatar': fields.String(),
    'is_admin': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'last_login_time': fields.String()
})

user_list_data = user_ns.model('UserListData', {
    'items': fields.List(fields.Nested(user_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

user_list_response = user_ns.clone('UserListResponse', base_response, {
    'data': fields.Nested(user_list_data)
})

user_item_response = user_ns.clone('UserItemResponse', base_response, {
    'data': fields.Nested(user_item_model)
})

user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_create_schema = UserCreateSchema()
user_update_schema = UserUpdateSchema()
user_reset_password_schema = UserResetPasswordSchema()


@user_ns.route('')
class UserList(Resource):
    @login_required
    @user_ns.expect(user_query_parser)
    @user_ns.response(200, '成功', user_list_response)
    @user_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = user_query_parser.parse_args()

        identity = get_jwt_identity()
        print(identity)
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        print(current_user_id)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()
        print(current_user)

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        username = args.get('username', '')
        status = args.get('status')

        query = User.query.filter_by(is_deleted=0)

        # 权限过滤
        if current_user.is_admin == 1:
            # 公司内部人员：可以查看所有用户
            factory_id = args.get('factory_id')
            if factory_id:
                # 查询该工厂下的用户（通过 UserFactory）
                user_ids = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id, status=1, is_deleted=0
                ).all()
                user_ids = [u[0] for u in user_ids]
                query = query.filter(User.id.in_(user_ids))
        else:
            # 普通用户：只能查看自己
            query = query.filter(User.id == current_user.id)

        if username:
            query = query.filter(User.username.like(f'%{username}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(User.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': users_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @user_ns.expect(user_create_model)
    @user_ns.response(201, '创建成功', user_item_response)
    @user_ns.response(400, '参数错误', error_response)
    @user_ns.response(409, '用户名已存在', error_response)
    def post(self):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以创建用户
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限创建用户', 403)

        try:
            data = user_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        existing_user = User.query.filter_by(username=data['username'], is_deleted=0).first()
        if existing_user:
            return ApiResponse.error('用户名已存在')

        user = User(
            username=data['username'],
            password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
            nickname=data.get('nickname', ''),
            phone=data.get('phone', ''),
            is_admin=data.get('is_admin', 0),
            status=1
        )
        user.save()

        return ApiResponse.success(user_schema.dump(user), '创建成功', 201)


@user_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @login_required
    @user_ns.response(200, '成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        # 权限验证
        if current_user.is_admin != 1 and current_user.id != user.id:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(user_schema.dump(user))

    @login_required
    @user_ns.expect(user_update_model)
    @user_ns.response(200, '更新成功', user_item_response)
    @user_ns.response(404, '用户不存在', error_response)
    def put(self, user_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        # 权限验证
        if current_user.is_admin != 1 and current_user.id != user.id:
            return ApiResponse.error('无权限修改', 403)

        try:
            data = user_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'phone' in data:
            user.phone = data['phone']
        if 'status' in data:
            user.status = data['status']

        user.save()

        return ApiResponse.success(user_schema.dump(user), '更新成功')

    @login_required
    @user_ns.response(200, '删除成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    @user_ns.response(403, '不能删除自己', forbidden_response)
    def delete(self, user_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以删除用户
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限删除', 403)

        if user.id == current_user.id:
            return ApiResponse.error('不能删除当前登录用户')

        user.delete()
        return ApiResponse.success(message='删除成功')


@user_ns.route('/<int:user_id>/reset-password')
class UserResetPassword(Resource):
    @login_required
    @user_ns.expect(user_reset_password_model)
    @user_ns.response(200, '重置成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    def post(self, user_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以重置密码
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限重置密码', 403)

        try:
            data = user_reset_password_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        user.save()

        return ApiResponse.success(message='密码重置成功')


@user_ns.route('/<int:user_id>/roles')
class UserRoles(Resource):
    @login_required
    @user_ns.response(200, '成功', base_response)
    @user_ns.response(404, '用户不存在', error_response)
    def get(self, user_id):
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        identity = get_jwt_identity()
        factory_id = identity.get('factory_id') if isinstance(identity, dict) else None

        if not factory_id:
            return ApiResponse.error('请指定工厂')

        role_ids = db.session.query(UserFactoryRole.role_id).filter_by(
            user_id=user_id, factory_id=factory_id, is_deleted=0
        ).all()
        role_ids = [r[0] for r in role_ids]

        from app.schemas.system.role import RoleSchema
        roles = Role.query.filter(Role.id.in_(role_ids), Role.is_deleted == 0).all() if role_ids else []
        role_schema = RoleSchema()

        return ApiResponse.success(role_schema.dump(roles, many=True))

    @login_required
    @user_ns.expect(user_assign_roles_model)
    @user_ns.response(200, '分配成功', base_response)
    @user_ns.response(403, '无权限', forbidden_response)
    @user_ns.response(404, '用户不存在', error_response)
    def put(self, user_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        # 只有公司内部人员可以分配角色
        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以分配角色', 403)

        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return ApiResponse.error('用户不存在')

        data = request.get_json()
        role_ids = data.get('role_ids', [])
        factory_id = data.get('factory_id')

        if not factory_id and user.is_admin != 1:
            return ApiResponse.error('请指定工厂ID', 400)

        for role_id in role_ids:
            role = Role.query.filter_by(id=role_id, is_deleted=0).first()
            if not role:
                return ApiResponse.error(f'角色ID {role_id} 不存在', 400)
            # 平台角色可以分配给任何人，工厂角色需要校验工厂
            if role.factory_id > 0 and role.factory_id != factory_id:
                return ApiResponse.error(f'角色 {role.name} 不属于该工厂', 400)

        # 删除原有角色分配
        if user.is_admin == 1:
            # 平台用户：只需要 role_id，不需要 factory_id
            db.session.execute(
                UserFactoryRole.__table__.delete().where(
                    UserFactoryRole.user_id == user_id
                )
            )
        else:
            db.session.execute(
                UserFactoryRole.__table__.delete().where(
                    UserFactoryRole.user_id == user_id,
                    UserFactoryRole.factory_id == factory_id
                )
            )

        # 添加新的角色分配
        for role_id in role_ids:
            role = Role.query.get(role_id)
            ufr = UserFactoryRole(
                user_id=user_id,
                factory_id=0 if role.factory_id == 0 else factory_id,
                role_id=role_id
            )
            db.session.add(ufr)

        db.session.commit()

        return ApiResponse.success(message='角色分配成功')


@user_ns.route('/test')
class Test(Resource):
    def get(self):
        return {'message': 'test ok'}
