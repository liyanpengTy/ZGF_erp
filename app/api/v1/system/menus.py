"""菜单管理接口"""
from flask_restx import Namespace, Resource, fields
from flask import request
from app.models.system.menu import Menu
from app.utils.response import ApiResponse
from app.schemas.system.menu import MenuSchema, MenuCreateSchema, MenuUpdateSchema
from marshmallow import ValidationError
from app.api.common.models import get_common_models
from app.utils.permissions import login_required
from app.services import AuthService, MenuService

menu_ns = Namespace('菜单管理-menus', description='菜单管理')

common = get_common_models(menu_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
page_response = common['page_response']

# ========== 请求解析器 ==========
menu_query_parser = menu_ns.parser()
menu_query_parser.add_argument('type', type=int, location='args', help='菜单类型 (0:目录,1:菜单,2:按钮)',
                               choices=[0, 1, 2])
menu_query_parser.add_argument('status', type=int, location='args', help='状态 (0:禁用,1:启用)', choices=[0, 1])

# ========== 请求模型 ==========
menu_create_model = menu_ns.model('MenuCreate', {
    'parent_id': fields.Integer(description='父菜单ID', default=0, example=0),
    'name': fields.String(required=True, description='菜单名称', example='用户管理'),
    'path': fields.String(description='路由路径', example='/system/user'),
    'component': fields.String(description='组件路径', example='system/user/index'),
    'permission': fields.String(description='权限标识', example='system:user:list'),
    'type': fields.Integer(required=True, description='类型', example=1, choices=[0, 1, 2]),
    'icon': fields.String(description='图标', example='user'),
    'sort_order': fields.Integer(description='排序', default=0, example=1)
})

menu_update_model = menu_ns.model('MenuUpdate', {
    'parent_id': fields.Integer(description='父菜单ID'),
    'name': fields.String(description='菜单名称'),
    'path': fields.String(description='路由路径'),
    'component': fields.String(description='组件路径'),
    'permission': fields.String(description='权限标识'),
    'type': fields.Integer(description='类型', choices=[0, 1, 2]),
    'icon': fields.String(description='图标'),
    'sort_order': fields.Integer(description='排序'),
    'status': fields.Integer(description='状态', choices=[0, 1])
})

# ========== 响应模型 ==========
menu_item_model = menu_ns.model('MenuItem', {
    'id': fields.Integer(),
    'parent_id': fields.Integer(),
    'name': fields.String(),
    'path': fields.String(),
    'component': fields.String(),
    'permission': fields.String(),
    'type': fields.Integer(),
    'icon': fields.String(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'update_time': fields.String(),
    'children': fields.List(fields.Raw)
})

menu_list_response = menu_ns.clone('MenuListResponse', base_response, {
    'data': fields.List(fields.Nested(menu_item_model))
})

menu_item_response = menu_ns.clone('MenuItemResponse', base_response, {
    'data': fields.Nested(menu_item_model)
})

# ========== Schema 初始化 ==========
menu_schema = MenuSchema()
menus_schema = MenuSchema(many=True)
menu_create_schema = MenuCreateSchema()
menu_update_schema = MenuUpdateSchema()


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@menu_ns.route('')
class MenuList(Resource):
    @login_required
    @menu_ns.expect(menu_query_parser)
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """菜单列表（树型）"""
        args = menu_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以查看菜单管理
        has_permission, error = MenuService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        menus = MenuService.get_menu_list(args)
        menu_tree = MenuService.build_menu_tree(menus, menu_schema=menu_schema)

        return ApiResponse.success(menu_tree)

    @login_required
    @menu_ns.expect(menu_create_model)
    @menu_ns.response(201, '创建成功', menu_item_response)
    @menu_ns.response(400, '参数错误', error_response)
    @menu_ns.response(403, '只有管理员可以创建', forbidden_response)
    def post(self):
        """创建菜单"""
        current_user = get_current_user()

        has_permission, error = MenuService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        try:
            data = menu_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        menu, error = MenuService.create_menu(data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(menu_schema.dump(menu), '创建成功', 201)


@menu_ns.route('/<int:menu_id>')
class MenuDetail(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_item_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    def get(self, menu_id):
        """菜单详情"""
        current_user = get_current_user()

        has_permission, error = MenuService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        menu = MenuService.get_menu_by_id(menu_id)
        if not menu:
            return ApiResponse.error('菜单不存在')

        return ApiResponse.success(menu_schema.dump(menu))

    @login_required
    @menu_ns.expect(menu_update_model)
    @menu_ns.response(200, '更新成功', menu_item_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    @menu_ns.response(403, '只有管理员可以更新', forbidden_response)
    def patch(self, menu_id):
        """更新菜单"""
        current_user = get_current_user()

        has_permission, error = MenuService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        menu = MenuService.get_menu_by_id(menu_id)
        if not menu:
            return ApiResponse.error('菜单不存在')

        try:
            data = menu_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        menu, error = MenuService.update_menu(menu, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(menu_schema.dump(menu), '更新成功')

    @login_required
    @menu_ns.response(200, '删除成功', base_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    @menu_ns.response(403, '只有管理员可以删除', forbidden_response)
    @menu_ns.response(409, '存在子菜单或关联角色', error_response)
    def delete(self, menu_id):
        """删除菜单"""
        current_user = get_current_user()

        has_permission, error = MenuService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        menu = MenuService.get_menu_by_id(menu_id)
        if not menu:
            return ApiResponse.error('菜单不存在')

        success, error = MenuService.delete_menu(menu)
        if not success:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(message='删除成功')


@menu_ns.route('/tree')
class MenuTree(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """菜单树（分配权限使用）"""
        current_user = get_current_user()

        has_permission, error = MenuService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        menus = Menu.query.filter_by(status=1, is_deleted=0).order_by(Menu.sort_order).all()
        menu_tree = MenuService.build_menu_tree(menus, menu_schema=menu_schema)

        return ApiResponse.success(menu_tree)


@menu_ns.route('/user-menus')
class UserMenus(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """当前用户菜单"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 获取工厂ID（从Token中）
        from flask_jwt_extended import get_jwt
        claims = get_jwt()
        factory_id = claims.get('factory_id')

        menu_tree = MenuService.get_user_menus(current_user, factory_id)

        return ApiResponse.success(menu_tree)
