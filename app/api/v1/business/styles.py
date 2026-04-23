from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.business.style import Style
from app.models.base_data.category import Category
from app.utils.response import ApiResponse
from app.schemas.business.style import StyleSchema, StyleCreateSchema, StyleUpdateSchema
from app.api.v1.shared_models import get_shared_models
from marshmallow import ValidationError

style_ns = Namespace('styles', description='款号管理')

shared = get_shared_models(style_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

style_query_parser = style_ns.parser()
style_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_query_parser.add_argument('style_no', type=str, location='args', help='款号')
style_query_parser.add_argument('name', type=str, location='args', help='款号名称')
style_query_parser.add_argument('category_id', type=int, location='args', help='分类ID')
style_query_parser.add_argument('gender', type=str, location='args', help='性别')
style_query_parser.add_argument('season', type=str, location='args', help='季节')
style_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])

style_item_model = style_ns.model('StyleItem', {
    'id': fields.Integer(),
    'factory_id': fields.Integer(),
    'style_no': fields.String(),
    'customer_style_no': fields.String(),
    'name': fields.String(),
    'category_id': fields.Integer(),
    'category_name': fields.String(),
    'gender': fields.String(),
    'season': fields.String(),
    'material': fields.String(),
    'description': fields.String(),
    'status': fields.Integer(),
    'images': fields.List(fields.String()),
    'need_cutting': fields.Integer(),
    'cutting_reserve': fields.Float(),
    'custom_attributes': fields.Raw(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_list_data = style_ns.model('StyleListData', {
    'items': fields.List(fields.Nested(style_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_list_response = style_ns.clone('StyleListResponse', base_response, {
    'data': fields.Nested(style_list_data)
})

style_item_response = style_ns.clone('StyleItemResponse', base_response, {
    'data': fields.Nested(style_item_model)
})

style_schema = StyleSchema()
styles_schema = StyleSchema(many=True)
style_create_schema = StyleCreateSchema()
style_update_schema = StyleUpdateSchema()


def get_category_name(category_id):
    if category_id:
        category = Category.query.filter_by(id=category_id, is_deleted=0).first()
        return category.name if category else None
    return None


@style_ns.route('')
class StyleList(Resource):
    @jwt_required()
    @style_ns.expect(style_query_parser)
    @style_ns.response(200, '成功', style_list_response)
    @style_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        style_no = args.get('style_no', '')
        name = args.get('name', '')
        category_id = args.get('category_id')
        gender = args.get('gender', '')
        season = args.get('season', '')
        status = args.get('status')

        query = Style.query.filter_by(factory_id=current_user.factory_id, is_deleted=0)

        if style_no:
            query = query.filter(Style.style_no.like(f'%{style_no}%'))
        if name:
            query = query.filter(Style.name.like(f'%{name}%'))
        if category_id:
            query = query.filter_by(category_id=category_id)
        if gender:
            query = query.filter_by(gender=gender)
        if season:
            query = query.filter_by(season=season)
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Style.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        items = []
        for style in pagination.items:
            item = style_schema.dump(style)
            item['category_name'] = get_category_name(style.category_id)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @jwt_required()
    @style_ns.expect(style_ns.model('StyleCreate', {
        'style_no': fields.String(required=True),
        'customer_style_no': fields.String(),
        'name': fields.String(),
        'category_id': fields.Integer(),
        'gender': fields.String(),
        'season': fields.String(),
        'material': fields.String(),
        'description': fields.String(),
        'images': fields.List(fields.String()),
        'need_cutting': fields.Integer(default=0),
        'cutting_reserve': fields.Float(default=0),
        'custom_attributes': fields.Raw()
    }))
    @style_ns.response(201, '创建成功', style_item_response)
    @style_ns.response(400, '参数错误', error_response)
    @style_ns.response(409, '款号已存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        existing = Style.query.filter_by(
            factory_id=current_user.factory_id,
            style_no=data['style_no'],
            is_deleted=0
        ).first()
        if existing:
            return ApiResponse.error('款号已存在')

        if data.get('category_id'):
            category = Category.query.filter_by(id=data['category_id'], is_deleted=0).first()
            if not category:
                return ApiResponse.error('分类不存在')

        style = Style(
            factory_id=current_user.factory_id,
            style_no=data['style_no'],
            customer_style_no=data.get('customer_style_no', ''),
            name=data.get('name', ''),
            category_id=data.get('category_id'),
            gender=data.get('gender', ''),
            season=data.get('season', ''),
            material=data.get('material', ''),
            description=data.get('description', ''),
            status=1,
            images=data.get('images', []),
            need_cutting=data.get('need_cutting', 0),
            cutting_reserve=data.get('cutting_reserve', 0),
            custom_attributes=data.get('custom_attributes', {})
        )
        style.save()

        result = style_schema.dump(style)
        result['category_name'] = get_category_name(style.category_id)

        return ApiResponse.success(result, '创建成功', 201)


@style_ns.route('/<int:style_id>')
class StyleDetail(Resource):
    @jwt_required()
    @style_ns.response(200, '成功', style_item_response)
    @style_ns.response(404, '不存在', error_response)
    def get(self, style_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        style = Style.query.filter_by(id=style_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在')

        if style.factory_id != current_user.factory_id:
            return ApiResponse.error('无权限查看', 403)

        result = style_schema.dump(style)
        result['category_name'] = get_category_name(style.category_id)

        return ApiResponse.success(result)

    @jwt_required()
    @style_ns.expect(style_ns.model('StyleUpdate', {
        'style_no': fields.String(),
        'customer_style_no': fields.String(),
        'name': fields.String(),
        'category_id': fields.Integer(),
        'gender': fields.String(),
        'season': fields.String(),
        'material': fields.String(),
        'description': fields.String(),
        'status': fields.Integer(),
        'images': fields.List(fields.String()),
        'need_cutting': fields.Integer(),
        'cutting_reserve': fields.Float(),
        'custom_attributes': fields.Raw()
    }))
    @style_ns.response(200, '更新成功', style_item_response)
    @style_ns.response(404, '不存在', error_response)
    def put(self, style_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        style = Style.query.filter_by(id=style_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在')

        if style.factory_id != current_user.factory_id:
            return ApiResponse.error('只能修改自己工厂的款号', 403)

        try:
            data = style_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'style_no' in data and data['style_no'] != style.style_no:
            existing = Style.query.filter_by(
                factory_id=current_user.factory_id,
                style_no=data['style_no'],
                is_deleted=0
            ).first()
            if existing:
                return ApiResponse.error('款号已存在')
            style.style_no = data['style_no']

        if 'customer_style_no' in data:
            style.customer_style_no = data['customer_style_no']
        if 'name' in data:
            style.name = data['name']
        if 'category_id' in data:
            if data['category_id']:
                category = Category.query.filter_by(id=data['category_id'], is_deleted=0).first()
                if not category:
                    return ApiResponse.error('分类不存在')
            style.category_id = data['category_id']
        if 'gender' in data:
            style.gender = data['gender']
        if 'season' in data:
            style.season = data['season']
        if 'material' in data:
            style.material = data['material']
        if 'description' in data:
            style.description = data['description']
        if 'status' in data:
            style.status = data['status']
        if 'images' in data:
            style.images = data['images']
        if 'need_cutting' in data:
            style.need_cutting = data['need_cutting']
        if 'cutting_reserve' in data:
            style.cutting_reserve = data['cutting_reserve']
        if 'custom_attributes' in data:
            style.custom_attributes = data['custom_attributes']

        style.save()

        result = style_schema.dump(style)
        result['category_name'] = get_category_name(style.category_id)

        return ApiResponse.success(result, '更新成功')

    @jwt_required()
    @style_ns.response(200, '删除成功', base_response)
    @style_ns.response(404, '不存在', error_response)
    def delete(self, style_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        style = Style.query.filter_by(id=style_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在')

        if style.factory_id != current_user.factory_id:
            return ApiResponse.error('只能删除自己工厂的款号', 403)

        # 检查是否有子表数据（价格、工艺、橡筋、拼接）
        from app.models.business.style_price import StylePrice
        from app.models.business.style_process import StyleProcess
        from app.models.business.style_elastic import StyleElastic
        from app.models.business.style_splice import StyleSplice

        price_count = StylePrice.query.filter_by(style_id=style_id, is_deleted=0).count()
        process_count = StyleProcess.query.filter_by(style_id=style_id, is_deleted=0).count()
        elastic_count = StyleElastic.query.filter_by(style_id=style_id, is_deleted=0).count()
        splice_count = StyleSplice.query.filter_by(style_id=style_id, is_deleted=0).count()

        if price_count > 0 or process_count > 0 or elastic_count > 0 or splice_count > 0:
            return ApiResponse.error('请先删除款号关联的价格、工艺、橡筋、拼接数据', 409)

        style.delete()

        return ApiResponse.success(message='删除成功')
