"""角色管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.utils.response import ApiResponse
from app.schemas.system.role import RoleSchema, RoleCreateSchema, RoleUpdateSchema, RoleAssignMenuSchema
from marshmallow import ValidationError
from app.api.common.parsers import page_parser
from app.api.common.models import get_common_models
from app.utils.permissions import login_required
from app.services import AuthService, RoleService

role_ns = Namespace('角色管理-roles', description='角色管理')

# 获取公共模型
common = get_common_models(role_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
page_response = common['page_response']

# ========== 请求解析器 ==========
role_query_parser = page_parser.copy()
role_query_parser.add_argument('name', type=str, location='args', help='角色名称（模糊查询）')
role_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
role_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID（管理员使用）', min=1)

# ========== 请求模型 ==========
role_create_model = role_ns.model('RoleCreate', {
    'name': fields.String(required=True, description='角色名称', example='管理员'),
    'code': fields.String(required=True, description='角色编码', example='admin'),
    'description': fields.String(description='描述', example='工厂管理员'),
    'sort_order': fields.Integer(description='排序', default=0, example=1),
    'factory_id': fields.Integer(required=True, description='工厂ID')
})

role_update_model = role_ns.model('RoleUpdate', {
    'name': fields.String(description='角色名称', example='管理员'),
    'description': fields.String(description='描述', example='工厂管理员'),
    'status': fields.Integer(description='状态', example=1, choices=[0, 1]),
    'sort_order': fields.Integer(description='排序', example=1)
})

role_assign_menu_model = role_ns.model('RoleAssignMenu', {
    'menu_ids': fields.List(fields.Integer, required=True, description='菜单ID列表', example=[1, 2, 3])
})

# ========== 响应模型 ==========
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

# ========== Schema 初始化 ==========
role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)
role_create_schema = RoleCreateSchema()
role_update_schema = RoleUpdateSchema()
role_assign_menu_schema = RoleAssignMenuSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@role_ns.route('')
class RoleList(Resource):
    @login_required
    @role_ns.expect(role_query_parser)
    @role_ns.response(200, '成功', role_list_response)
    @role_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """角色列表"""
        args = role_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result, error = RoleService.get_role_list(current_user, args)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success({
            'items': roles_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })

    @login_required
    @role_ns.expect(role_create_model)
    @role_ns.response(201, '创建成功', role_item_response)
    @role_ns.response(400, '参数错误', error_response)
    @role_ns.response(403, '只有管理员可以创建', forbidden_response)
    @role_ns.response(409, '角色编码或名称已存在', error_response)
    def post(self):
        """创建角色"""
        current_user = get_current_user()

        # 只有公司内部人员可以创建角色
        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建角色', 403)

        try:
            data = role_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        factory_id = data.get('factory_id')
        if not factory_id:
            return ApiResponse.error('请指定工厂ID', 400)

        role, error = RoleService.create_role(data, factory_id)
        if error:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(role_schema.dump(role), '创建成功', 201)


@role_ns.route('/<int:role_id>')
class RoleDetail(Resource):
    @login_required
    @role_ns.response(200, '成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """角色详情"""
        current_user = get_current_user()

        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')

        # 权限验证
        if not RoleService.verify_role_permission(current_user, role):
            return ApiResponse.error('无权限查看此角色', 403)

        return ApiResponse.success(role_schema.dump(role))

    @login_required
    @role_ns.expect(role_update_model)
    @role_ns.response(200, '更新成功', role_item_response)
    @role_ns.response(404, '角色不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def patch(self, role_id):
        """更新角色"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以更新角色', 403)

        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')

        try:
            data = role_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

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
        """删除角色"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除角色', 403)

        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')

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
        """获取角色菜单"""
        current_user = get_current_user()

        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')

        if not RoleService.verify_role_permission(current_user, role):
            return ApiResponse.error('无权限查看', 403)

        menu_ids = RoleService.get_role_menu_ids(role_id)

        return ApiResponse.success(menu_ids)

    @login_required
    @role_ns.expect(role_assign_menu_model)
    @role_ns.response(200, '分配成功', base_response)
    @role_ns.response(404, '角色或菜单不存在', error_response)
    @role_ns.response(403, '无权限', forbidden_response)
    def post(self, role_id):
        """分配菜单权限"""
        current_user = get_current_user()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以分配权限', 403)

        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')

        try:
            data = role_assign_menu_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        menu_ids = data['menu_ids']

        success, error = RoleService.assign_role_menus(role_id, menu_ids)
        if not success:
            return ApiResponse.error(error, 404)

        return ApiResponse.success(message='权限分配成功')


@role_ns.route('/<int:role_id>/users')
class RoleUsers(Resource):
    @login_required
    @role_ns.response(200, '成功', role_users_response)
    @role_ns.response(404, '角色不存在', error_response)
    def get(self, role_id):
        """获取角色下的用户"""
        current_user = get_current_user()

        role = RoleService.get_role_by_id(role_id)
        if not role:
            return ApiResponse.error('角色不存在')

        if not RoleService.verify_role_permission(current_user, role):
            return ApiResponse.error('无权限查看', 403)

        user_ids = RoleService.get_role_users(role_id)

        from app.schemas.auth.user import UserSchema
        from app.models.auth.user import User

        user_schema = UserSchema()
        users = User.query.filter(User.id.in_(user_ids), User.is_deleted == 0).all() if user_ids else []

        return ApiResponse.success(user_schema.dump(users, many=True))
