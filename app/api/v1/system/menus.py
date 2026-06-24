"""菜单管理接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.api.common.auth import get_current_claims, require_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser
from app.api.common.resource_helpers import ensure_permission_or_error, get_resource_or_error
from app.api.common.response_helpers import load_json_or_error
from app.api.common.serializers import serialize_schema
from app.constants.permissions import (
    PERM_SYSTEM_MENU_ADD,
    PERM_SYSTEM_MENU_DELETE,
    PERM_SYSTEM_MENU_EDIT,
    PERM_SYSTEM_MENU_QUERY,
)
from app.models.system.menu import Menu
from app.schemas.system.menu import MenuCreateSchema, MenuSchema, MenuUpdateSchema
from app.services import MenuService
from app.utils.permissions import login_required, permission_required
from app.utils.response import ApiResponse

menu_ns = Namespace('菜单管理-menus', description='菜单管理')

common = get_common_models(menu_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']

menu_query_parser = new_query_parser()
menu_query_parser.add_argument('type', type=int, location='args', help='菜单类型，0-目录，1-菜单，2-按钮', choices=[0, 1, 2])
menu_query_parser.add_argument('status', type=int, location='args', help='状态，0-禁用，1-启用', choices=[0, 1])

menu_create_model = menu_ns.model('MenuCreate', {
    'parent_id': fields.Integer(description='父级菜单 ID', default=0, example=0),
    'name': fields.String(required=True, description='菜单名称', example='用户管理'),
    'path': fields.String(description='路由路径', example='/system/user'),
    'component': fields.String(description='组件路径', example='system/user/index'),
    'permission': fields.String(description='权限标识', example='system.users.browse'),
    'type': fields.Integer(required=True, description='菜单类型', example=1, choices=[0, 1, 2]),
    'icon': fields.String(description='图标', example='user'),
    'sort_order': fields.Integer(description='排序', default=0, example=1),
})

menu_update_model = menu_ns.model('MenuUpdate', {
    'parent_id': fields.Integer(description='父级菜单 ID'),
    'name': fields.String(description='菜单名称'),
    'path': fields.String(description='路由路径'),
    'component': fields.String(description='组件路径'),
    'permission': fields.String(description='权限标识'),
    'type': fields.Integer(description='菜单类型', choices=[0, 1, 2]),
    'icon': fields.String(description='图标'),
    'sort_order': fields.Integer(description='排序'),
    'status': fields.Integer(description='状态', choices=[0, 1]),
})

menu_item_model = menu_ns.model('MenuItem', {
    'id': fields.Integer(description='菜单 ID'),
    'parent_id': fields.Integer(description='父级菜单 ID'),
    'name': fields.String(description='菜单名称'),
    'path': fields.String(description='路由路径'),
    'component': fields.String(description='组件路径'),
    'permission': fields.String(description='权限标识'),
    'type': fields.Integer(description='菜单类型'),
    'icon': fields.String(description='图标'),
    'sort_order': fields.Integer(description='排序值'),
    'status': fields.Integer(description='状态'),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})
menu_item_model['children'] = fields.List(
    fields.Nested(menu_item_model),
    description='递归子菜单列表，结构与当前节点一致',
)

menu_list_response = menu_ns.clone('MenuListResponse', base_response, {
    'data': fields.List(fields.Nested(menu_item_model), description='菜单树列表'),
})

menu_item_response = menu_ns.clone('MenuItemResponse', base_response, {
    'data': fields.Nested(menu_item_model, description='菜单详情数据'),
})

menu_schema = MenuSchema()
menus_schema = MenuSchema(many=True)
menu_create_schema = MenuCreateSchema()
menu_update_schema = MenuUpdateSchema()


def get_menu_user_or_error():
    """获取菜单接口当前用户，不存在时返回统一错误响应。"""
    return require_current_user()


@menu_ns.route('')
class MenuList(Resource):
    @login_required
    @permission_required(PERM_SYSTEM_MENU_QUERY)
    @menu_ns.expect(menu_query_parser)
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    @menu_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询菜单树列表接口，支持按菜单类型和状态筛选。"""
        args = menu_query_parser.parse_args()
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = MenuService.check_admin_permission(current_user)
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        menus = MenuService.get_menu_list(args)
        menu_tree = MenuService.build_menu_tree(menus, menu_schema=menu_schema)
        return ApiResponse.success(menu_tree)

    @login_required
    @permission_required(PERM_SYSTEM_MENU_ADD)
    @menu_ns.expect(menu_create_model)
    @menu_ns.response(201, '创建成功', menu_item_response)
    @menu_ns.response(400, '参数错误', error_response)
    @menu_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """创建菜单接口，用于新增目录、菜单或按钮。"""
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = MenuService.check_admin_permission(current_user)
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        data, validation_error = load_json_or_error(menu_create_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        menu, error = MenuService.create_menu(data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(menu_schema, menu), '创建成功', 201)


@menu_ns.route('/<int:menu_id>')
class MenuDetail(Resource):
    @login_required
    @permission_required(PERM_SYSTEM_MENU_QUERY)
    @menu_ns.response(200, '成功', menu_item_response)
    @menu_ns.response(403, '无权限', forbidden_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    def get(self, menu_id):
        """查询菜单详情接口，返回单个菜单的完整配置。"""
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = MenuService.check_admin_permission(current_user)
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        menu, error_response_data = get_resource_or_error(lambda: MenuService.get_menu_by_id(menu_id), '菜单不存在')
        if error_response_data:
            return error_response_data

        return ApiResponse.success(serialize_schema(menu_schema, menu))

    @login_required
    @permission_required(PERM_SYSTEM_MENU_EDIT)
    @menu_ns.expect(menu_update_model)
    @menu_ns.response(200, '更新成功', menu_item_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    @menu_ns.response(403, '无权限', forbidden_response)
    def patch(self, menu_id):
        """更新菜单接口，可修改菜单基础信息与状态。"""
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = MenuService.check_admin_permission(current_user)
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        menu, error_response_data = get_resource_or_error(lambda: MenuService.get_menu_by_id(menu_id), '菜单不存在')
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(menu_update_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        menu, error = MenuService.update_menu(menu, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(menu_schema, menu), '更新成功')

    @login_required
    @permission_required(PERM_SYSTEM_MENU_DELETE)
    @menu_ns.response(200, '删除成功', base_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    @menu_ns.response(403, '无权限', forbidden_response)
    @menu_ns.response(409, '存在子菜单或关联角色', error_response)
    def delete(self, menu_id):
        """删除菜单接口，存在子菜单或角色关联时会阻止删除。"""
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = MenuService.check_admin_permission(current_user)
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        menu, error_response_data = get_resource_or_error(lambda: MenuService.get_menu_by_id(menu_id), '菜单不存在')
        if error_response_data:
            return error_response_data

        success, error = MenuService.delete_menu(menu)
        if not success:
            return ApiResponse.error(error, 409)

        return ApiResponse.success(message='删除成功')


@menu_ns.route('/tree')
class MenuTree(Resource):
    @login_required
    @permission_required(PERM_SYSTEM_MENU_QUERY)
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    @menu_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询启用菜单树接口，供角色分配权限时选择菜单节点。"""
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        has_permission, error = MenuService.check_admin_permission(current_user)
        permission_error = ensure_permission_or_error(has_permission, error, 403)
        if permission_error:
            return permission_error

        menus = Menu.query.filter_by(status=1, is_deleted=0).order_by(Menu.sort_order).all()
        menu_tree = MenuService.build_menu_tree(menus, menu_schema=menu_schema)
        return ApiResponse.success(menu_tree)


@menu_ns.route('/user-menus')
class UserMenus(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询当前账号可见菜单树接口，按登录身份与工厂上下文返回菜单。"""
        current_user, error_response_data = get_menu_user_or_error()
        if error_response_data:
            return error_response_data

        claims = get_current_claims()
        factory_id = claims.get('factory_id')
        menu_tree = MenuService.get_user_menus(current_user, factory_id)
        return ApiResponse.success(menu_tree)
