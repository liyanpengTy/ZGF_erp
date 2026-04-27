from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.models.business.style import Style
from app.models.business.style_process import StyleProcess
from app.utils.response import ApiResponse
from app.schemas.business.style_process import StyleProcessSchema, StyleProcessCreateSchema, StyleProcessUpdateSchema
from app.api.v1.shared_models import get_shared_models
from marshmallow import ValidationError
from app.utils.permissions import login_required

style_process_ns = Namespace('style-processes', description='款号工艺管理')

shared = get_shared_models(style_process_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

style_process_query_parser = style_process_ns.parser()
style_process_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
style_process_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
style_process_query_parser.add_argument('style_id', type=int, required=True, location='args', help='款号ID')
style_process_query_parser.add_argument('process_type', type=str, location='args', help='工艺类型',
                                        choices=['embroidery', 'print', 'other'])

style_process_item_model = style_process_ns.model('StyleProcessItem', {
    'id': fields.Integer(),
    'style_id': fields.Integer(),
    'process_type': fields.String(),
    'process_type_label': fields.String(),
    'process_name': fields.String(),
    'remark': fields.String(),
    'create_time': fields.String(),
    'update_time': fields.String()
})

style_process_list_data = style_process_ns.model('StyleProcessListData', {
    'items': fields.List(fields.Nested(style_process_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

style_process_list_response = style_process_ns.clone('StyleProcessListResponse', base_response, {
    'data': fields.Nested(style_process_list_data)
})

style_process_item_response = style_process_ns.clone('StyleProcessItemResponse', base_response, {
    'data': fields.Nested(style_process_item_model)
})

process_type_labels = {
    'embroidery': '刺绣',
    'print': '印花',
    'other': '其他'
}

style_process_schema = StyleProcessSchema()
style_processes_schema = StyleProcessSchema(many=True)
style_process_create_schema = StyleProcessCreateSchema()
style_process_update_schema = StyleProcessUpdateSchema()


@style_process_ns.route('')
class StyleProcessList(Resource):
    @login_required
    @style_process_ns.expect(style_process_query_parser)
    @style_process_ns.response(200, '成功', style_process_list_response)
    @style_process_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = style_process_query_parser.parse_args()

        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        style_id = args['style_id']
        page = args['page']
        page_size = args['page_size']
        process_type = args.get('process_type')

        style = Style.query.filter_by(id=style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        query = StyleProcess.query.filter_by(style_id=style_id, is_deleted=0)

        if process_type:
            query = query.filter_by(process_type=process_type)

        pagination = query.order_by(StyleProcess.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        items = []
        for process in pagination.items:
            item = style_process_schema.dump(process)
            item['process_type_label'] = process_type_labels.get(process.process_type, process.process_type)
            items.append(item)

        return ApiResponse.success({
            'items': items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })

    @login_required
    @style_process_ns.expect(style_process_ns.model('StyleProcessCreate', {
        'style_id': fields.Integer(required=True),
        'process_type': fields.String(required=True),
        'process_name': fields.String(),
        'remark': fields.String()
    }))
    @style_process_ns.response(201, '创建成功', style_process_item_response)
    @style_process_ns.response(400, '参数错误', error_response)
    @style_process_ns.response(403, '无权限', forbidden_response)
    @style_process_ns.response(404, '款号不存在', error_response)
    def post(self):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        if not current_user:
            return ApiResponse.error('用户不存在')

        try:
            data = style_process_create_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        style = Style.query.filter_by(id=data['style_id'], factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('款号不存在或无权限')

        process = StyleProcess(
            style_id=data['style_id'],
            process_type=data['process_type'],
            process_name=data.get('process_name', ''),
            remark=data.get('remark', '')
        )
        process.save()

        result = style_process_schema.dump(process)
        result['process_type_label'] = process_type_labels.get(process.process_type, process.process_type)

        return ApiResponse.success(result, '创建成功', 201)


@style_process_ns.route('/<int:process_id>')
class StyleProcessDetail(Resource):
    @login_required
    @style_process_ns.response(200, '成功', style_process_item_response)
    @style_process_ns.response(404, '不存在', error_response)
    def get(self, process_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        process = StyleProcess.query.filter_by(id=process_id, is_deleted=0).first()
        if not process:
            return ApiResponse.error('工艺记录不存在')

        style = Style.query.filter_by(id=process.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限查看', 403)

        result = style_process_schema.dump(process)
        result['process_type_label'] = process_type_labels.get(process.process_type, process.process_type)

        return ApiResponse.success(result)

    @login_required
    @style_process_ns.expect(style_process_ns.model('StyleProcessUpdate', {
        'process_type': fields.String(),
        'process_name': fields.String(),
        'remark': fields.String()
    }))
    @style_process_ns.response(200, '更新成功', style_process_item_response)
    @style_process_ns.response(404, '不存在', error_response)
    def put(self, process_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        process = StyleProcess.query.filter_by(id=process_id, is_deleted=0).first()
        if not process:
            return ApiResponse.error('工艺记录不存在')

        style = Style.query.filter_by(id=process.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限修改', 403)

        try:
            data = style_process_update_schema.load(request.get_json())
        except ValidationError as e:
            return ApiResponse.error(str(e.messages), 400)

        if 'process_type' in data:
            process.process_type = data['process_type']
        if 'process_name' in data:
            process.process_name = data['process_name']
        if 'remark' in data:
            process.remark = data['remark']

        process.save()

        result = style_process_schema.dump(process)
        result['process_type_label'] = process_type_labels.get(process.process_type, process.process_type)

        return ApiResponse.success(result, '更新成功')

    @login_required
    @style_process_ns.response(200, '删除成功', base_response)
    @style_process_ns.response(404, '不存在', error_response)
    def delete(self, process_id):
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)

        process = StyleProcess.query.filter_by(id=process_id, is_deleted=0).first()
        if not process:
            return ApiResponse.error('工艺记录不存在')

        style = Style.query.filter_by(id=process.style_id, factory_id=current_user.factory_id, is_deleted=0).first()
        if not style:
            return ApiResponse.error('无权限删除', 403)

        process.delete()

        return ApiResponse.success(message='删除成功')