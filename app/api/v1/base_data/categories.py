from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.base_data.category import Category
from app.utils.response import ApiResponse
from app.schemas.base_data.category import CategorySchema, CategoryCreateSchema, CategoryUpdateSchema
from marshmallow import ValidationError
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required

category_ns = Namespace('categories', description='分类管理')

shared = get_shared_models(category_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

category_query_parser = category_ns.parser()
category_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
category_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
category_query_parser.add_argument('name', type=str, location='args', help='分类名称')
category_query_parser.add_argument('parent_id', type=int, location='args', help='父分类ID')
category_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
category_query_parser.add_argument('factory_only', type=int, location='args', help='是否只查工厂自定义', choices=[0, 1])

category_item_model = category_ns.model('CategoryItem', {
    'id': fields.Integer(),
    'name': fields.String(),
    'parent_id': fields.Integer(),
    'code': fields.String(),
    'factory_id': fields.Integer(),
    'sort_order': fields.Integer(),
    'status': fields.Integer(),
    'create_time': fields.String(),
    'update_time': fields.String(),
    'children': fields.List(fields.Raw)
})

category_list_data = category_ns.model('CategoryListData', {
    'items': fields.List(fields.Nested(category_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

category_list_response = category_ns.clone('CategoryListResponse', base_response, {
    'data': fields.Nested(category_list_data)
})

category_item_response = category_ns.clone('CategoryItemResponse', base_response, {
    'data': fields.Nested(category_item_model)
})

category_tree_response = category_ns.clone('CategoryTreeResponse', base_response, {
    'data': fields.List(fields.Nested(category_item_model))
})

category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()


def build_category_tree(categories, parent_id=0):
    tree = []
    for cat in categories:
        if cat.parent_id == parent_id and cat.is_deleted == 0:
            children = build_category_tree(categories, cat.id)
            cat_dict = category_schema.dump(cat)
            if children:
                cat_dict['children'] = children
            tree.append(cat_dict)
    return tree


@category_ns.route('')
class CategoryList(Resource):
    @login_required
    @category_ns.expect(category_query_parser)
    @category_ns.response(200, '成功', category_list_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = category_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        name = args.get('name', '')
        parent_id = args.get('parent_id')
        status = args.get('status')
        factory_only = args.get('factory_only', 0)

        query = Category.query.filter_by(is_deleted=0)

        if factory_only:
            query = query.filter(Category.factory_id == current_user.factory_id)
        else:
            query = query.filter((Category.factory_id == 0) | (Category.factory_id == current_user.factory_id))

        if name:
            query = query.filter(Category.name.like(f'%{name}%'))
        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Category.sort_order).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': categories_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @category_ns.response(201, '创建成功', category_item_response)
    @category_ns.response(400, '参数错误', error_response)
    @category_ns.response(409, '编码已存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = category_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        existing = Category.query.filter_by(
            factory_id=current_user.factory_id,
            code=data['code'],
            is_deleted=0
        ).first()
        if existing:
            return ApiResponse.error('分类编码已存在')

        if data.get('parent_id', 0) != 0:
            parent = Category.query.filter_by(id=data['parent_id'], is_deleted=0).first()
            if not parent:
                return ApiResponse.error('父分类不存在')

        category = Category(
            name=data['name'],
            parent_id=data.get('parent_id', 0),
            code=data['code'],
            factory_id=current_user.factory_id,
            sort_order=data.get('sort_order', 0),
            status=1
        )
        category.save()

        return ApiResponse.success(category_schema.dump(category), '创建成功', 201)


@category_ns.route('/tree')
class CategoryTree(Resource):
    @login_required
    @category_ns.response(200, '成功', category_tree_response)
    @category_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        categories = Category.query.filter_by(is_deleted=0).filter(
            (Category.factory_id == 0) | (Category.factory_id == current_user.factory_id)
        ).order_by(Category.sort_order).all()

        tree = build_category_tree(categories)

        return ApiResponse.success(tree)


@category_ns.route('/<int:category_id>')
class CategoryDetail(Resource):
    @login_required
    @category_ns.response(200, '成功', category_item_response)
    @category_ns.response(404, '不存在', error_response)
    def get(self, category_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        category = Category.query.filter_by(id=category_id, is_deleted=0).first()
        if not category:
            return ApiResponse.error('分类不存在')

        if category.factory_id != 0 and category.factory_id != current_user.factory_id:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(category_schema.dump(category))

    @login_required
    @category_ns.response(200, '更新成功', category_item_response)
    @category_ns.response(404, '不存在', error_response)
    def put(self, category_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        category = Category.query.filter_by(id=category_id, is_deleted=0).first()
        if not category:
            return ApiResponse.error('分类不存在')

        if category.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的分类', 403)

        try:
            data = category_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'name' in data:
            category.name = data['name']
        if 'parent_id' in data:
            if data['parent_id'] == category.id:
                return ApiResponse.error('不能将父分类设为自己')
            category.parent_id = data['parent_id']
        if 'sort_order' in data:
            category.sort_order = data['sort_order']
        if 'status' in data:
            category.status = data['status']

        category.save()

        return ApiResponse.success(category_schema.dump(category), '更新成功')

    @login_required
    @category_ns.response(200, '删除成功', base_response)
    @category_ns.response(404, '不存在', error_response)
    def delete(self, category_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        category = Category.query.filter_by(id=category_id, is_deleted=0).first()
        if not category:
            return ApiResponse.error('分类不存在')

        if category.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的分类', 403)

        children_count = Category.query.filter_by(parent_id=category_id, is_deleted=0).count()
        if children_count > 0:
            return ApiResponse.error('请先删除子分类', 409)

        category.delete()

        return ApiResponse.success(message='删除成功')
