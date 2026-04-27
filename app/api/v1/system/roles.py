from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.auth.user import User
from app.models.system.role import Role, role_menu
from app.models.system.menu import Menu
from app.models.system.user_factory_role import UserFactoryRole
from app.utils.response import ApiResponse
from app.schemas.system.role import RoleSchema, RoleCreateSchema, RoleUpdateSchema, RoleAssignMenuSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required

role_ns = Namespace('roles', description='角色管理')

shared = get_shared_models(role_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

role_query_parser = role_ns.parser()
role_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
role_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
role_query_parser.add_argument('name', type=str, location='args', help='角色名称（模糊查询）')
role_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
role_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID（管理员使用）')

role_create_model = role_ns.model('RoleCreate', {
    'name': fields.String(required=True, description='角色名称', example='管理员', min_length=2, max_length=50),
    'code': fields.String(required=True, description='角色编码', example='admin', min_length=2, max_length=50),
    'description': fields.String(description='描述', example='工厂管理员', max_length=255),
    'sort_order': fields.Integer(description='排序', default=0, example=1)
})

role_update_model = role_ns.model('RoleUpdate', {
    'name': fields.String(description='角色名称', example='管理员', min_length=2, max_length=50),
    'description': fields.String(description='描述', example='工厂管理员', max_length=255),
    'status': fields.Integer(description='状态', example=1, choices=[0, 1]),
    'sort_order': fields.Integer(description='排序', example=1)
})

role_assign_menu_model = role_ns.model('RoleAssignMenu', {
    'menu_ids': fields.List(fields.Integer, required=True, description='菜单ID列表', example=[1, 2, 3])
})

role_item_model = role_ns.model('RoleItem', {
    'id': fields.Integer(),
    'factory_id': fields.Integer(),
    'name': fields.String(),
    'code': fields.String(),
    'description': fields.String(),
    'status': fields.Integer(),
    'sort_order': fields.Integer(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

role_list_data = role_ns.model('RoleListData', {
    'items': fields.List(fields.Nested(role_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

role_list_response = role_ns.clone('RoleListResponse', base_response, {
    'data': fields.Nested(role_list_data)
})

role_item_response = role_ns.clone('RoleItemResponse', base_response, {
    'data': fields.Nested(role_item_model)
})

menu_ids_response = role_ns.clone('MenuIdsResponse', base_response, {
    'data': fields.List(fields.Integer)
})

role_users_response = role_ns.clone('RoleUsersResponse', base_response, {
    'data': fields.List(fields.Nested(role_ns.model('RoleUserItem', {
        'id': fields.Integer(),
        'username': fields.String(),
        'nickname': fields.String(),
        'phone': fields.String(),
        'status': fields.Integer()
    })))
})

role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)
role_create_schema = RoleCreateSchema()
role_update_schema = RoleUpdateSchema()
role_assign_menu_schema = RoleAssignMenuSchema()


@role_ns.route('')
class RoleList(Resource):
    @login_required
    @role_ns.expect(role_query_parser)
    @role_ns.response(200, '成功', role_list_response)
    @role_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = role_query_parser.parse_args()

        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        name = args.get('name', '')
        status = args.get('status')

        # 公司内部人员：可以查看平台角色 + 指定工厂的角色
        if current_user.is_admin == 1:
            factory_id = args.get('factory_id')
            if not factory_id:
                return ApiResponse.error('请指定工厂ID', 400)
            # 查询平台角色 + 该工厂的角色
            query = Role.query.filter(
                (Role.factory_id == 0) | (Role.factory_id == factory_id),
                Role.is_deleted == 0
            )
        else:
            # 普通用户：只能查看自己工厂的角色
            factory_id = current_user.factory_id
            query = Role.query.filter_by(factory_id=factory_id, is_deleted=0)

        if name:
            query = query.filter(Role.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Role.sort_order).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': roles_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @role_ns.expect(role_create_model)
    @role_ns.response(201, '创建成功', role_item_response)
    @role_ns.response(400, '参数错误', error_response)
    @role_ns.response(403, '只有管理员可以创建', forbidden_response)
    @role_ns.response(409, '角色编码或名称已存在', error_response)
    def post(self):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        # 只有公司内部人员可以创建角色
        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建角色', 403)

        try:
            data = role_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        factory_id = request.json.get('factory_id')
        if not factory_id:
            return ApiResponse.error('请指定工厂ID', 400)

        existing_role = Role.query.filter_by(factory_id=factory_id, code=data['code'], is_deleted=0).first()
        if existing_role:
            return ApiResponse.error('角色编码已存在')

        existing_name = Role.query.filter_by(factory_id=factory_id, name=data['name'], is_deleted=0).first()
        if existing_name:
            return ApiResponse.error('角色名称已存在')

        role = Role(
            factory_id=factory_id,
            name=data['name'],
            code=data['code'],
            description=data.get('description', ''),
            sort_order=data.get('sort_order', 0),
            status=1
        )
        role.save()

        return ApiResponse.success(role_schema.dump(role), '创建成功', 201)


@role_ns.route('/<int:role_id>')
class RoleDetail(Resource):
    @login_required
    @role_ns.response(200, '成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        role = Role.query.filter_by(id=role_id, is_deleted=0).first()
        if not role:
            return ApiResponse.error('角色不存在')

        # 权限验证
        if current_user.is_admin != 1:
            from app.models.system.user_factory import UserFactory
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id, factory_id=role.factory_id, status=1, is_deleted=0
            ).first()
            if not user_factory:
                return ApiResponse.error('无权限查看此角色', 403)

        return ApiResponse.success(role_schema.dump(role))

    @login_required
    @role_ns.expect(role_update_model)
    @role_ns.response(200, '更新成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def put(self, role_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以更新角色', 403)

        role = Role.query.filter_by(id=role_id, is_deleted=0).first()
        if not role:
            return ApiResponse.error('角色不存在')

        try:
            data = role_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'name' in data:
            existing = Role.query.filter_by(factory_id=role.factory_id, name=data['name'], is_deleted=0).first()
            if existing and existing.id != role_id:
                return ApiResponse.error('角色名称已存在')
            role.name = data['name']

        if 'description' in data:
            role.description = data['description']

        if 'status' in data:
            role.status = data['status']

        if 'sort_order' in data:
            role.sort_order = data['sort_order']

        role.save()

        return ApiResponse.success(role_schema.dump(role), '更新成功')

    @login_required
    @role_ns.response(200, '删除成功', base_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(409, '角色已被使用', error_response)
    def delete(self, role_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除角色', 403)

        role = Role.query.filter_by(id=role_id, is_deleted=0).first()
        if not role:
            return ApiResponse.error('角色不存在')

        # 检查是否有用户关联此角色
        user_role_count = UserFactoryRole.query.filter_by(role_id=role_id, is_deleted=0).count()
        if user_role_count > 0:
            return ApiResponse.error(f'有 {user_role_count} 个用户关联此角色，无法删除')

        role.delete()

        return ApiResponse.success(message='删除成功')


@role_ns.route('/<int:role_id>/menus')
class RoleMenus(Resource):
    @login_required
    @role_ns.response(200, '成功', menu_ids_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        role = Role.query.filter_by(id=role_id, is_deleted=0).first()
        if not role:
            return ApiResponse.error('角色不存在')

        if current_user.is_admin != 1:
            from app.models.system.user_factory import UserFactory
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id, factory_id=role.factory_id, status=1, is_deleted=0
            ).first()
            if not user_factory:
                return ApiResponse.error('无权限查看', 403)

        menu_ids = db.session.query(role_menu.c.menu_id).filter_by(role_id=role_id).all()
        menu_ids = [m[0] for m in menu_ids]

        return ApiResponse.success(menu_ids)

    @login_required
    @role_ns.expect(role_assign_menu_model)
    @role_ns.response(200, '分配成功', base_response)
    @role_ns.response(404, '角色或菜单不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def put(self, role_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以分配权限', 403)

        role = Role.query.filter_by(id=role_id, is_deleted=0).first()
        if not role:
            return ApiResponse.error('角色不存在')

        try:
            data = role_assign_menu_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        menu_ids = data['menu_ids']

        for menu_id in menu_ids:
            menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
            if not menu:
                return ApiResponse.error(f'菜单ID {menu_id} 不存在')

        db.session.execute(role_menu.delete().where(role_menu.c.role_id == role_id))

        for menu_id in menu_ids:
            db.session.execute(role_menu.insert().values(role_id=role_id, menu_id=menu_id))

        db.session.commit()

        return ApiResponse.success(message='权限分配成功')


@role_ns.route('/<int:role_id>/users')
class RoleUsers(Resource):
    @login_required
    @role_ns.response(200, '成功', role_users_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        role = Role.query.filter_by(id=role_id, is_deleted=0).first()
        if not role:
            return ApiResponse.error('角色不存在')

        if current_user.is_admin != 1:
            from app.models.system.user_factory import UserFactory
            user_factory = UserFactory.query.filter_by(
                user_id=current_user.id, factory_id=role.factory_id, status=1, is_deleted=0
            ).first()
            if not user_factory:
                return ApiResponse.error('无权限查看', 403)

        user_ids = db.session.query(UserFactoryRole.user_id).filter_by(
            role_id=role_id, is_deleted=0
        ).all()
        user_ids = [u[0] for u in user_ids]

        from app.schemas.auth.user import UserSchema
        user_schema = UserSchema()

        users = User.query.filter(User.id.in_(user_ids), User.is_deleted == 0).all() if user_ids else []

        return ApiResponse.success(user_schema.dump(users, many=True))
