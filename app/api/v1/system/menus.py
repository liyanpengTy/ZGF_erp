from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.auth.user import User
from app.models.system.menu import Menu
from app.models.system.user_factory_role import UserFactoryRole
from app.models.system.role import role_menu
from app.utils.response import ApiResponse
from app.schemas.system.menu import MenuSchema, MenuCreateSchema, MenuUpdateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required

menu_ns = Namespace('menus', description='菜单管理')

shared = get_shared_models(menu_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

menu_query_parser = menu_ns.parser()
menu_query_parser.add_argument('type', type=int, location='args', help='菜单类型 (0:目录,1:菜单,2:按钮)',
                               choices=[0, 1, 2])
menu_query_parser.add_argument('status', type=int, location='args', help='状态 (0:禁用,1:启用)', choices=[0, 1])

menu_create_model = menu_ns.model('MenuCreate', {
    'parent_id': fields.Integer(description='父菜单ID', default=0, example=0),
    'name': fields.String(required=True, description='菜单名称', example='用户管理', min_length=1, max_length=50),
    'path': fields.String(description='路由路径', example='/system/user', max_length=100),
    'component': fields.String(description='组件路径', example='system/user/index', max_length=100),
    'permission': fields.String(description='权限标识', example='system:user:list', max_length=100),
    'type': fields.Integer(required=True, description='类型', example=1, choices=[0, 1, 2]),
    'icon': fields.String(description='图标', example='user', max_length=50),
    'sort_order': fields.Integer(description='排序', default=0, example=1)
})

menu_update_model = menu_ns.model('MenuUpdate', {
    'parent_id': fields.Integer(description='父菜单ID'),
    'name': fields.String(description='菜单名称', min_length=1, max_length=50),
    'path': fields.String(description='路由路径', max_length=100),
    'component': fields.String(description='组件路径', max_length=100),
    'permission': fields.String(description='权限标识', max_length=100),
    'type': fields.Integer(description='类型', choices=[0, 1, 2]),
    'icon': fields.String(description='图标', max_length=50),
    'sort_order': fields.Integer(description='排序'),
    'status': fields.Integer(description='状态', choices=[0, 1])
})

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

menu_schema = MenuSchema()
menus_schema = MenuSchema(many=True)
menu_create_schema = MenuCreateSchema()
menu_update_schema = MenuUpdateSchema()


def build_menu_tree(menus, parent_id=0):
    """构建菜单树"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = build_menu_tree(menus, menu.id)
            menu_dict = menu_schema.dump(menu)
            if children:
                menu_dict['children'] = children
            tree.append(menu_dict)
    return tree


@menu_ns.route('')
class MenuList(Resource):
    @login_required
    @menu_ns.expect(menu_query_parser)
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = menu_query_parser.parse_args()

        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以查看菜单管理
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看菜单', 403)

        query = Menu.query.filter_by(is_deleted=0)
        menu_type = args.get('type')
        status = args.get('status')

        if menu_type is not None:
            query = query.filter_by(type=menu_type)
        if status is not None:
            query = query.filter_by(status=status)

        menus = query.order_by(Menu.sort_order).all()
        menu_tree = build_menu_tree(menus)

        return ApiResponse.success(menu_tree)

    @login_required
    @menu_ns.expect(menu_create_model)
    @menu_ns.response(201, '创建成功', menu_item_response)
    @menu_ns.response(400, '参数错误', error_response)
    @menu_ns.response(403, '只有管理员可以创建', forbidden_response)
    def post(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以创建菜单', 403)

        try:
            data = menu_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if data.get('parent_id', 0) != 0:
            parent_menu = Menu.query.filter_by(id=data['parent_id'], is_deleted=0).first()
            if not parent_menu:
                return ApiResponse.error('父菜单不存在')

        menu = Menu(
            parent_id=data.get('parent_id', 0),
            name=data['name'],
            path=data.get('path', ''),
            component=data.get('component', ''),
            permission=data.get('permission', ''),
            type=data['type'],
            icon=data.get('icon', ''),
            sort_order=data.get('sort_order', 0),
            status=1
        )
        menu.save()

        return ApiResponse.success(menu_schema.dump(menu), '创建成功', 201)


@menu_ns.route('/<int:menu_id>')
class MenuDetail(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_item_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    def get(self, menu_id):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
        if not menu:
            return ApiResponse.error('菜单不存在')

        return ApiResponse.success(menu_schema.dump(menu))

    @login_required
    @menu_ns.expect(menu_update_model)
    @menu_ns.response(200, '更新成功', menu_item_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    @menu_ns.response(403, '只有管理员可以更新', forbidden_response)
    def put(self, menu_id):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以更新菜单', 403)

        menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
        if not menu:
            return ApiResponse.error('菜单不存在')

        try:
            data = menu_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'parent_id' in data:
            if data['parent_id'] != 0:
                parent_menu = Menu.query.filter_by(id=data['parent_id'], is_deleted=0).first()
                if not parent_menu:
                    return ApiResponse.error('父菜单不存在')
                if data['parent_id'] == menu.id:
                    return ApiResponse.error('不能将父菜单设为自己')
            menu.parent_id = data['parent_id']

        if 'name' in data:
            menu.name = data['name']
        if 'path' in data:
            menu.path = data['path']
        if 'component' in data:
            menu.component = data['component']
        if 'permission' in data:
            menu.permission = data['permission']
        if 'type' in data:
            menu.type = data['type']
        if 'icon' in data:
            menu.icon = data['icon']
        if 'sort_order' in data:
            menu.sort_order = data['sort_order']
        if 'status' in data:
            menu.status = data['status']

        menu.save()

        return ApiResponse.success(menu_schema.dump(menu), '更新成功')

    @login_required
    @menu_ns.response(200, '删除成功', base_response)
    @menu_ns.response(404, '菜单不存在', error_response)
    @menu_ns.response(403, '只有管理员可以删除', forbidden_response)
    @menu_ns.response(409, '存在子菜单或关联角色', error_response)
    def delete(self, menu_id):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('只有管理员可以删除菜单', 403)

        menu = Menu.query.filter_by(id=menu_id, is_deleted=0).first()
        if not menu:
            return ApiResponse.error('菜单不存在')

        children_count = Menu.query.filter_by(parent_id=menu_id, is_deleted=0).count()
        if children_count > 0:
            return ApiResponse.error(f'请先删除子菜单（共 {children_count} 个）')

        role_count = db.session.query(role_menu).filter_by(menu_id=menu_id).count()
        if role_count > 0:
            return ApiResponse.error(f'有 {role_count} 个角色关联此菜单，无法删除')

        menu.delete()

        return ApiResponse.success(message='删除成功')


@menu_ns.route('/tree')
class MenuTree(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        menus = Menu.query.filter_by(status=1, is_deleted=0).order_by(Menu.sort_order).all()
        menu_tree = build_menu_tree(menus)

        return ApiResponse.success(menu_tree)


@menu_ns.route('/user-menus')
class UserMenus(Resource):
    @login_required
    @menu_ns.response(200, '成功', menu_list_response)
    @menu_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()

        if isinstance(identity, dict):
            user_id = identity.get('user_id')
            factory_id = identity.get('factory_id')
        else:
            user_id = int(identity)
            factory_id = None

        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 公司内部人员：返回所有菜单
        if current_user.is_admin == 1:
            menus = Menu.query.filter_by(status=1, is_deleted=0).order_by(Menu.sort_order).all()

        # 工厂员工/客户/协作用户：根据角色返回菜单
        elif factory_id:
            # 获取用户在当前工厂的角色
            role_ids = db.session.query(UserFactoryRole.role_id).filter_by(
                user_id=user_id, factory_id=factory_id, is_deleted=0
            ).all()
            role_ids = [r[0] for r in role_ids]

            if role_ids:
                menu_ids = db.session.query(role_menu.c.menu_id).filter(
                    role_menu.c.role_id.in_(role_ids)
                ).all()
                menu_ids = list(set([m[0] for m in menu_ids]))
                menus = Menu.query.filter(
                    Menu.id.in_(menu_ids),
                    Menu.status == 1,
                    Menu.is_deleted == 0
                ).order_by(Menu.sort_order).all()
            else:
                menus = []
        else:
            menus = []

        menu_tree = build_menu_tree(menus)

        return ApiResponse.success(menu_tree)
