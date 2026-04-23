from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.business.style import Style
from app.models.business.style_splice import StyleSplice
from app.models.base_data.color import Color
from app.utils.response import ApiResponse
from app.schemas.business.style_splice import StyleSpliceSchema, StyleSpliceCreateSchema, StyleSpliceUpdateSchema
from app.api.v1.shared_models import get_shared_models
from marshmallow import ValidationError

style_splice_ns = Namespace('style-splices', description='款号拼接管理')

shared = get_shared_models(style_splice_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

style_splice_query_parser = style_splice_ns.parser()
style_splice_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_splice_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_splice_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_splice_query_parser.add_argument('splice_type', type=str, location='args', help='拼接类型',
                                       choices=['color', 'fabric', 'lace', 'other'])

style_splice_item_model = style_splice_ns.model('StyleSpliceItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'splice_type': fields.String(),
    'splice_type_label': fields.String(),
    'material_id': fields.Integer(),
    'material_name': fields.String(),
    'material_code': fields.String(),
    'sort_order': fields.Integer(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_splice_list_data = style_splice_ns.model('StyleSpliceListData', {
    'items': fields.List(fields.Nested(style_splice_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_splice_list_response = style_splice_ns.clone('StyleSpliceListResponse', base_response, {
    'data': fields.Nested(style_splice_list_data)
})

style_splice_item_response = style_splice_ns.clone('StyleSpliceItemResponse', base_response, {
    'data': fields.Nested(style_splice_item_model)
})

splice_type_labels = {
    'color': '颜色拼接',
    'fabric': '布料拼接',
    'lace': '蕾丝拼接',
    'other': '其他'
}

style_splice_schema = StyleSpliceSchema()
style_splices_schema = StyleSpliceSchema(many=True)
style_splice_create_schema = StyleSpliceCreateSchema()
style_splice_update_schema = StyleSpliceUpdateSchema()


def get_material_info(material_id, splice_type):
    """获取材料信息（颜色或布料）"""
    if splice_type == 'color' and material_id:
        color = Color.query.filter_by(id=material_id, is_deleted=0).first()
        if color:
            return {
                'material_name': color.name,
                'material_code': color.code
            }
    # 布料等其他类型暂不实现，直接返回空
    return {
        'material_name': '',
        'material_code': ''
    }


@style_splice_ns.route('')
class StyleSpliceList(Resource):
    @jwt_required()
    @style_splice_ns.expect(style_splice_query_parser)
    @style_splice_ns.response(200, '成功', style_splice_list_response)
    @style_splice_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_splice_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']
        page = args['page']
        page_size = args['page_size']
        splice_type = args.get('splice_type')

        style = Style.query.filter_by(id=style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        query = StyleSplice.query.filter_by(style_id=style_id, is_deleted=0)

        if splice_type:
            query = query.filter_by(splice_type=splice_type)

        pagination = query.order_by(StyleSplice.sort_order).paginate(
            page=page, per_page=page_size, error_out=False
        )

        items = []
        for splice in pagination.items:
            item = style_splice_schema.dump(splice)
            item['splice_type_label'] = splice_type_labels.get(splice.splice_type, splice.splice_type)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @jwt_required()
    @style_splice_ns.expect(style_splice_ns.model('StyleSpliceCreate', {
        'style_id': fields.Integer(required=True),
        'splice_type': fields.String(required=True),
        'material_id': fields.Integer(),
        'material_name': fields.String(),
        'material_code': fields.String(),
        'sort_order': fields.Integer(default=0),
        'remark': fields.String()
    }))
    @style_splice_ns.response(201, '创建成功', style_splice_item_response)
    @style_splice_ns.response(400, '参数错误', error_response)
    @style_splice_ns.response(403, '无权限', forbidden_response)
    @style_splice_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_splice_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style = Style.query.filter_by(id=data['style_id'], factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        # 如果是颜色拼接，验证颜色是否存在
        if data['splice_type'] == 'color' and data.get('material_id'):
            color = Color.query.filter_by(id=data['material_id'], is_deleted=0).first()
            if not color:
                return ApiResponse.error('颜色不存在')

        splice = StyleSplice(
            style_id=data['style_id'],
            splice_type=data['splice_type'],
            material_id=data.get('material_id'),
            material_name=data.get('material_name', ''),
            material_code=data.get('material_code', ''),
            sort_order=data.get('sort_order', 0),
            remark=data.get('remark', '')
        )
        splice.save()

        result = style_splice_schema.dump(splice)
        result['splice_type_label'] = splice_type_labels.get(splice.splice_type, splice.splice_type)

        return ApiResponse.success(result, '创建成功', 201)


@style_splice_ns.route('/<int:splice_id>')
class StyleSpliceDetail(Resource):
    @jwt_required()
    @style_splice_ns.response(200, '成功', style_splice_item_response)
    @style_splice_ns.response(404, '不存在', error_response)
    def get(self, splice_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        splice = StyleSplice.query.filter_by(id=splice_id, is_deleted=0).first()
        if not splice:
            return ApiResponse.error('拼接记录不存在')

        style = Style.query.filter_by(id=splice.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限查看', 403)

        result = style_splice_schema.dump(splice)
        result['splice_type_label'] = splice_type_labels.get(splice.splice_type, splice.splice_type)

        return ApiResponse.success(result)

    @jwt_required()
    @style_splice_ns.expect(style_splice_ns.model('StyleSpliceUpdate', {
        'splice_type': fields.String(),
        'material_id': fields.Integer(),
        'material_name': fields.String(),
        'material_code': fields.String(),
        'sort_order': fields.Integer(),
        'remark': fields.String()
    }))
    @style_splice_ns.response(200, '更新成功', style_splice_item_response)
    @style_splice_ns.response(404, '不存在', error_response)
    def put(self, splice_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        splice = StyleSplice.query.filter_by(id=splice_id, is_deleted=0).first()
        if not splice:
            return ApiResponse.error('拼接记录不存在')

        style = Style.query.filter_by(id=splice.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限修改', 403)

        try:
            data = style_splice_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'splice_type' in data:
            splice.splice_type = data['splice_type']
        if 'material_id' in data:
            splice.material_id = data['material_id']
        if 'material_name' in data:
            splice.material_name = data['material_name']
        if 'material_code' in data:
            splice.material_code = data['material_code']
        if 'sort_order' in data:
            splice.sort_order = data['sort_order']
        if 'remark' in data:
            splice.remark = data['remark']

        splice.save()

        result = style_splice_schema.dump(splice)
        result['splice_type_label'] = splice_type_labels.get(splice.splice_type, splice.splice_type)

        return ApiResponse.success(result, '更新成功')

    @jwt_required()
    @style_splice_ns.response(200, '删除成功', base_response)
    @style_splice_ns.response(404, '不存在', error_response)
    def delete(self, splice_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        splice = StyleSplice.query.filter_by(id=splice_id, is_deleted=0).first()
        if not splice:
            return ApiResponse.error('拼接记录不存在')

        style = Style.query.filter_by(id=splice.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限删除', 403)

        splice.delete()

        return ApiResponse.success(message='删除成功')
