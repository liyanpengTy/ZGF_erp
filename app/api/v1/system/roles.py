"""角色管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.schemas.system.role import RoleAssignMenuSchema, RoleCreateSchema, RoleSchema, RoleUpdateSchema
from app.services import RoleService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

role_ns = Namespace('角色管理-roles', description='角色管理')

common = get_common_models(role_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']

role_query_parser = page_parser.copy()
role_query_parser.add_argument('name', type=str, location='args', help='角色名称（模糊查询）')
role_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
role_query_parser.add_argument(
    'scope_type',
    type=str,
    location='args',
    help='角色归属范围',
    choices=['platform', 'factory', 'partner_subject'],
)
role_query_parser.add_argument('scope_id', type=int, location='args', help='角色归属主键；工厂角色传工厂ID')

role_option_query_parser = new_query_parser()
role_option_query_parser.add_argument('name', type=str, location='args', help='角色名称（模糊查询）')
role_option_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
role_option_query_parser.add_argument(
    'scope_type',
    type=str,
    location='args',
    help='角色归属范围',
    choices=['platform', 'factory', 'partner_subject'],
)
role_option_query_parser.add_argument('scope_id', type=int, location='args', help='角色归属主键；工厂角色传工厂ID')

role_create_model = role_ns.model('RoleCreate', {
    'scope_type': fields.String(
        description='角色归属范围；工厂管理员创建时可不传，后端会固定为 factory',
        choices=['platform', 'factory', 'partner_subject'],
        example='factory',
    ),
    'scope_id': fields.Integer(
        description='角色归属主键；平台角色可不传，工厂管理员创建时后端会固定为当前工厂ID',
        example=1,
    ),
    'name': fields.String(required=True, description='角色名称', example='工厂管理员'),
    'code': fields.String(required=True, description='角色编码', example='factory_admin'),
    'description': fields.String(description='角色说明', example='工厂管理员角色'),
    'sort_order': fields.Integer(description='排序', default=0, example=1),
    'data_scope': fields.String(
        description='数据范围',
        choices=['all_factory', 'assigned', 'own_related', 'self_only'],
        example='all_factory',
    ),
    'is_factory_admin': fields.Integer(description='是否工厂管理员角色', choices=[0, 1], example=1),
})

role_update_model = role_ns.model('RoleUpdate', {
    'name': fields.String(description='角色名称', example='工厂管理员'),
    'description': fields.String(description='角色说明', example='工厂管理员角色'),
    'status': fields.Integer(description='状态', example=1, choices=[0, 1]),
    'sort_order': fields.Integer(description='排序', example=1),
    'data_scope': fields.String(
        description='数据范围',
        choices=['all_factory', 'assigned', 'own_related', 'self_only'],
    ),
    'is_factory_admin': fields.Integer(description='是否工厂管理员角色', choices=[0, 1]),
})

role_assign_menu_model = role_ns.model('RoleAssignMenu', {
    'menu_ids': fields.List(fields.Integer, required=True, description='菜单ID列表', example=[1, 2, 3]),
})

role_item_model = role_ns.model('RoleItem', {
    'id': fields.Integer(description='角色ID'),
    'scope_type': fields.String(description='角色归属范围'),
    'scope_type_label': fields.String(description='角色归属范围名称'),
    'scope_id': fields.Integer(description='角色归属主键'),
    'name': fields.String(description='角色名称'),
    'code': fields.String(description='角色编码'),
    'description': fields.String(description='角色说明'),
    'status': fields.Integer(description='状态'),
    'sort_order': fields.Integer(description='排序值'),
    'data_scope': fields.String(description='数据范围'),
    'data_scope_label': fields.String(description='数据范围名称'),
    'is_factory_admin': fields.Integer(description='是否工厂管理员角色'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

role_option_model = role_ns.model('RoleOptionItem', {
    'id': fields.Integer(description='角色ID', example=1),
    'name': fields.String(description='角色名称', example='工厂管理员'),
    'code': fields.String(description='角色编码', example='factory_admin'),
    'scope_type': fields.String(description='角色归属范围', example='factory'),
    'scope_type_label': fields.String(description='角色归属范围名称', example='工厂角色'),
    'scope_id': fields.Integer(description='角色归属主键', example=1),
    'is_factory_admin': fields.Integer(description='是否工厂管理员角色', example=1),
})

role_list_data = role_ns.model('RoleListData', {
    'items': fields.List(fields.Nested(role_item_model), description='角色列表'),
    'total': fields.Integer(description='总条数'),
    'page': fields.Integer(description='当前页码'),
    'page_size': fields.Integer(description='每页条数'),
    'pages': fields.Integer(description='总页数'),
})

role_list_response = role_ns.clone('RoleListResponse', base_response, {
    'data': fields.Nested(role_list_data, description='角色分页数据'),
})
role_item_response = role_ns.clone('RoleItemResponse', base_response, {
    'data': fields.Nested(role_item_model, description='角色详情数据'),
})
role_options_response = role_ns.clone('RoleOptionsResponse', base_response, {
    'data': fields.List(fields.Nested(role_option_model), description='角色下拉选项列表'),
})
menu_ids_response = role_ns.clone('MenuIdsResponse', base_response, {
    'data': fields.List(fields.Integer, description='菜单ID列表'),
})

role_user_item_model = role_ns.model('RoleUserItem', {
    'id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'nickname': fields.String(description='昵称'),
    'phone': fields.String(description='手机号'),
    'status': fields.Integer(description='状态'),
})

role_users_response = role_ns.clone('RoleUsersResponse', base_response, {
    'data': fields.List(fields.Nested(role_user_item_model), description='角色下的用户列表'),
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
        """分页查询角色列表。"""
        args = role_query_parser.parse_args()
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        result, error = RoleService.get_role_list(current_user, args, get_current_factory_id())
        if error:
            return ApiResponse.error(error, 403 if error == '无权限查看角色' else 400)

        return ApiResponse.success({
            'items': roles_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @role_ns.expect(role_create_model)
    @role_ns.response(201, '创建成功', role_item_response)
    @role_ns.response(400, '参数错误', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(409, '角色编码或名称已存在', error_response)
    def post(self):
        """按归属范围创建角色，支持平台角色和工厂角色。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = role_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        if not current_user.is_platform_admin:
            if not RoleService.has_factory_admin_permission(current_user, current_factory_id):
                return ApiResponse.error('只有平台管理员或工厂管理员可以创建角色', 403)
            data['scope_type'] = 'factory'
            data['scope_id'] = current_factory_id

        role, error = RoleService.create_role(data)
        if error:
            return ApiResponse.error(error, 400 if 'scope_id' in error else 409)
        return ApiResponse.success(role_schema.dump(role), '创建成功', 201)


@role_ns.route('/options')
class RoleOptions(Resource):
    @login_required
    @role_ns.expect(role_option_query_parser)
    @role_ns.response(200, '成功', role_options_response)
    @role_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询角色下拉选项列表，供角色选择器直接使用。"""
        current_user = get_current_user()
        if not current_user:
            return ApiResponse.error('用户不存在')

        roles, error = RoleService.get_role_options(current_user, role_option_query_parser.parse_args(), get_current_factory_id())
        if error:
            return ApiResponse.error(error, 403 if error == '无权限查看角色' else 400)

        return ApiResponse.success([
            {
                'id': role.id,
                'name': role.name,
                'code': role.code,
                'scope_type': role.scope_type,
                'scope_type_label': role.scope_type_label,
                'scope_id': role.scope_id,
                'is_factory_admin': role.is_factory_admin,
            }
            for role in roles
        ])


@role_ns.route('/<int:role_id>')
class RoleDetail(Resource):
    @login_required
    @role_ns.response(200, '成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """查看单个角色详情。"""
        current_user = get_current_user()
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')
        if not RoleService.verify_role_permission(current_user, role):
            return ApiResponse.error('无权限查看此角色', 403)
        return ApiResponse.success(role_schema.dump(role))

    @login_required
    @role_ns.expect(role_update_model)
    @role_ns.response(200, '更新成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def patch(self, role_id):
        """更新角色名称、数据范围和工厂管理员标识。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')
        if not RoleService.can_manage_role(current_user, role, current_factory_id):
            return ApiResponse.error('只有平台管理员或本工厂管理员可以更新角色', 403)

        try:
            data = role_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        role, error = RoleService.update_role(role, data)
        if error:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(role_schema.dump(role), '更新成功')

    @login_required
    @role_ns.response(200, '删除成功', base_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    @role_ns.response(409, '角色已被使用', error_response)
    def delete(self, role_id):
        """删除角色；删除前会检查是否仍被用户占用。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')
        if not RoleService.can_manage_role(current_user, role, current_factory_id):
            return ApiResponse.error('只有平台管理员或本工厂管理员可以删除角色', 403)

        success, error = RoleService.delete_role(role)
        if not success:
            return ApiResponse.error(error, 409)
        return ApiResponse.success(message='删除成功')


@role_ns.route('/<int:role_id>/menus')
class RoleMenus(Resource):
    @login_required
    @role_ns.response(200, '成功', menu_ids_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """查询角色已绑定的菜单权限。"""
        current_user = get_current_user()
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')
        if not RoleService.verify_role_permission(current_user, role):
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(RoleService.get_role_menu_ids(role_id))

    @login_required
    @role_ns.expect(role_assign_menu_model)
    @role_ns.response(200, '分配成功', base_response)
    @role_ns.response(404, '角色或菜单不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def post(self, role_id):
        """重建角色菜单权限绑定关系。"""
        current_user = get_current_user()
        current_factory_id = get_current_factory_id()
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')
        if not RoleService.can_manage_role(current_user, role, current_factory_id):
            return ApiResponse.error('只有平台管理员或本工厂管理员可以分配权限', 403)

        try:
            data = role_assign_menu_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        success, error = RoleService.assign_role_menus(role_id, data['menu_ids'], current_user, role)
        if not success:
            return ApiResponse.error(error, 403 if '不允许' in error else 404)
        return ApiResponse.success(message='权限分配成功')


@role_ns.route('/<int:role_id>/users')
class RoleUsers(Resource):
    @login_required
    @role_ns.response(200, '成功', role_users_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """查询当前角色下的用户列表。"""
        current_user = get_current_user()
        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')
        if not RoleService.verify_role_permission(current_user, role):
            return ApiResponse.error('无权限查看', 403)

        user_ids = RoleService.get_role_users(role_id)
        from app.models.auth.user import User

        users = User.query.filter(User.id.in_(user_ids), User.is_deleted == 0).all() if user_ids else []
        return ApiResponse.success([
            {
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'phone': user.phone,
                'status': user.status,
            }
            for user in users
        ])
