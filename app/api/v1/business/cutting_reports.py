"""裁床报工接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_claims, get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_with_date_parser
from app.schemas.business.cutting_report import CuttingReportCreateSchema, WorkCuttingReportSchema
from app.services import CuttingReportService, FactoryService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

cutting_report_ns = Namespace('裁床报工管理-cutting-reports', description='裁床报工与菲生成')

common = get_common_models(cutting_report_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

cutting_report_query_parser = page_with_date_parser.copy()
cutting_report_query_parser.add_argument('cut_batch_no', type=int, location='args', help='床次')
cutting_report_query_parser.add_argument('order_detail_sku_id', type=int, location='args', help='订单SKU ID')

cutting_bundle_input_model = cutting_report_ns.model('CuttingBundleInput', {
    'bed_no': fields.Integer(description='床号', example=1, default=1),
    'bundle_quantity': fields.Integer(required=True, description='当前菲数量', example=30),
    'priority': fields.String(description='优先级：normal/urgent/top', example='urgent', default='normal'),
    'remark': fields.String(description='备注', example='第一床加急'),
})

cutting_report_create_model = cutting_report_ns.model('CuttingReportCreate', {
    'order_detail_sku_id': fields.Integer(required=True, description='订单SKU ID', example=8),
    'cut_date': fields.String(required=True, description='裁床日期', example='2026-05-15'),
    'cut_quantity': fields.Integer(required=True, description='实裁数量', example=60),
    'template_id': fields.Integer(description='模板ID，未传则按工厂默认模板回退', example=2),
    'remark': fields.String(description='备注', example='按床次 2 开裁'),
    'bundles': fields.List(fields.Nested(cutting_bundle_input_model), description='生成菲明细；未传则默认生成 1 张菲'),
})

cutting_report_bundle_view_model = cutting_report_ns.model('CuttingReportBundleView', {
    'id': fields.Integer(description='菲ID'),
    'bundle_no': fields.String(description='菲号', example='FEI-4-2-1-1'),
    'cut_batch_no': fields.Integer(description='床次', example=2),
    'bed_no': fields.Integer(description='床号', example=1),
    'bundle_quantity': fields.Integer(description='数量', example=30),
    'priority': fields.String(description='优先级编码', example='urgent'),
    'priority_label': fields.String(description='优先级名称', example='加急'),
    'status': fields.String(description='状态编码', example='created'),
    'status_label': fields.String(description='状态名称', example='已生成'),
    'printed_content': fields.String(description='打印内容快照'),
})

cutting_report_item_model = cutting_report_ns.model('CuttingReportItemView', {
    'id': fields.Integer(description='裁床报工ID'),
    'factory_id': fields.Integer(description='工厂ID'),
    'template_id': fields.Integer(description='模板ID', allow_null=True),
    'order_id': fields.Integer(description='订单ID'),
    'order_detail_id': fields.Integer(description='订单明细ID'),
    'order_detail_sku_id': fields.Integer(description='订单SKU ID'),
    'style_id': fields.Integer(description='款号ID'),
    'style_no': fields.String(description='款号', example='1235#'),
    'style_name': fields.String(description='款号名称', allow_null=True),
    'color_id': fields.Integer(description='颜色ID', allow_null=True),
    'color_name': fields.String(description='颜色名称', allow_null=True),
    'size_id': fields.Integer(description='尺码ID', allow_null=True),
    'size_name': fields.String(description='尺码名称', allow_null=True),
    'report_user_id': fields.Integer(description='报工人ID'),
    'report_user_name': fields.String(description='报工人名称'),
    'cut_batch_no': fields.Integer(description='床次', example=2),
    'cut_date': fields.String(description='裁床日期', example='2026-05-15'),
    'cut_quantity': fields.Integer(description='实裁数量', example=60),
    'bundle_count': fields.Integer(description='生成菲数量', example=2),
    'status': fields.String(description='状态编码', example='active'),
    'status_label': fields.String(description='状态名称', example='生效中'),
    'remark': fields.String(description='备注', allow_null=True),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
    'bundles': fields.List(fields.Nested(cutting_report_bundle_view_model), description='生成的菲列表'),
})

cutting_report_list_data = build_page_data_model(cutting_report_ns, 'CuttingReportListData', cutting_report_item_model, items_description='裁床报工列表')
cutting_report_list_response = build_page_response_model(cutting_report_ns, 'CuttingReportListResponse', base_response, cutting_report_list_data, '裁床报工分页数据')
cutting_report_item_response = cutting_report_ns.clone('CuttingReportItemResponse', base_response, {
    'data': fields.Nested(cutting_report_item_model, description='裁床报工详情'),
})

cutting_report_schema = WorkCuttingReportSchema()
cutting_reports_schema = WorkCuttingReportSchema(many=True)
cutting_report_create_schema = CuttingReportCreateSchema()


def resolve_factory_context(require_write=False):
    """解析当前工厂上下文，并按读写场景校验工厂访问权限。"""
    current_user = get_current_user()
    current_factory_id = get_current_factory_id()
    if not current_user:
        return None, None, ApiResponse.error('用户不存在', 401)
    if not current_factory_id:
        return None, None, ApiResponse.error('当前登录态缺少工厂上下文，请先切换工厂', 400)
    has_permission, error = FactoryService.check_factory_permission(current_user, current_factory_id, require_write=require_write)
    if not has_permission:
        return None, None, ApiResponse.error(error, 403 if '无权限' in error or '续期' in error else 404)
    return current_user, current_factory_id, None


def check_cutting_write_permission(current_user):
    """校验当前用户是否具备裁床报工写权限。"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    if current_user.is_internal_user:
        return True
    return relation_type in {'owner', 'employee'}


@cutting_report_ns.route('')
class CuttingReportList(Resource):
    @login_required
    @cutting_report_ns.expect(cutting_report_query_parser)
    @cutting_report_ns.response(200, '成功', cutting_report_list_response)
    @cutting_report_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询当前工厂的裁床报工记录。"""
        _, current_factory_id, error_response_obj = resolve_factory_context(require_write=False)
        if error_response_obj:
            return error_response_obj
        args = cutting_report_query_parser.parse_args()
        result = CuttingReportService.get_cutting_report_list(current_factory_id, args)
        return ApiResponse.success({
            'items': cutting_reports_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })

    @login_required
    @cutting_report_ns.expect(cutting_report_create_model)
    @cutting_report_ns.response(201, '创建成功', cutting_report_item_response)
    @cutting_report_ns.response(400, '参数错误', error_response)
    @cutting_report_ns.response(401, '未登录', unauthorized_response)
    @cutting_report_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """创建裁床报工，并按模板自动生成一张或多张菲。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_cutting_write_permission(current_user):
            return ApiResponse.error('当前用户没有裁床报工权限', 403)
        try:
            data = cutting_report_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        report, error = CuttingReportService.create_cutting_report(current_factory_id, current_user.id, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(cutting_report_schema.dump(report), '创建成功', 201)


@cutting_report_ns.route('/<int:report_id>')
class CuttingReportDetail(Resource):
    @login_required
    @cutting_report_ns.response(200, '成功', cutting_report_item_response)
    @cutting_report_ns.response(401, '未登录', unauthorized_response)
    @cutting_report_ns.response(404, '裁床报工不存在', error_response)
    def get(self, report_id):
        """查询指定裁床报工详情。"""
        _, current_factory_id, error_response_obj = resolve_factory_context(require_write=False)
        if error_response_obj:
            return error_response_obj
        report = CuttingReportService.get_cutting_report_by_id(report_id)
        if not report or report.factory_id != current_factory_id:
            return ApiResponse.error('裁床报工不存在', 404)
        return ApiResponse.success(cutting_report_schema.dump(report))

    @login_required
    @cutting_report_ns.response(200, '删除成功', base_response)
    @cutting_report_ns.response(401, '未登录', unauthorized_response)
    @cutting_report_ns.response(403, '无权限', forbidden_response)
    @cutting_report_ns.response(404, '裁床报工不存在', error_response)
    def delete(self, report_id):
        """撤销指定裁床报工；仅允许撤销尚未发生后续流转的菲。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_cutting_write_permission(current_user):
            return ApiResponse.error('当前用户没有裁床报工权限', 403)
        report = CuttingReportService.get_cutting_report_by_id(report_id)
        if not report or report.factory_id != current_factory_id:
            return ApiResponse.error('裁床报工不存在', 404)
        success, error = CuttingReportService.delete_cutting_report(report)
        if not success:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(message='删除成功')
