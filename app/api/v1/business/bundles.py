"""菲查询、流转与打印预览接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from marshmallow import ValidationError

from app.api.common.auth import get_current_claims, get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import page_parser
from app.schemas.business.bundle import (
    BundleCompleteSchema,
    BundleIssueSchema,
    BundlePrintSchema,
    BundleReturnSchema,
    BundleTransferSchema,
    ProductionBundleSchema,
)
from app.services import BundleService, FactoryService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

bundle_ns = Namespace('菲管理-bundles', description='菲查询、流转与打印预览')

common = get_common_models(bundle_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
build_page_data_model = common['build_page_data_model']
build_page_response_model = common['build_page_response_model']

bundle_query_parser = page_parser.copy()
bundle_query_parser.add_argument('order_no', type=str, location='args', help='订单号')
bundle_query_parser.add_argument('style_no', type=str, location='args', help='款号')
bundle_query_parser.add_argument('cut_batch_no', type=int, location='args', help='床次')
bundle_query_parser.add_argument('status', type=str, location='args', help='菲状态', choices=['created', 'issued', 'in_progress', 'returned', 'completed', 'rework', 'cancelled'])
bundle_query_parser.add_argument('priority', type=str, location='args', help='优先级', choices=['normal', 'urgent', 'top'])

bundle_in_hand_stats_parser = reqparse.RequestParser()
bundle_in_hand_stats_parser.add_argument('holder_user_id', type=int, location='args', help='持有人用户ID')
bundle_in_hand_stats_parser.add_argument('process_id', type=int, location='args', help='工序ID')

bundle_flow_model = bundle_ns.model('BundleFlowView', {
    'id': fields.Integer(description='流转记录ID'),
    'process_id': fields.Integer(description='工序ID', allow_null=True),
    'process_name': fields.String(description='工序名称', allow_null=True),
    'user_id': fields.Integer(description='操作人ID', allow_null=True),
    'user_name': fields.String(description='操作人名称', allow_null=True),
    'from_user_id': fields.Integer(description='来源人ID', allow_null=True),
    'from_user_name': fields.String(description='来源人名称', allow_null=True),
    'to_user_id': fields.Integer(description='去向人ID', allow_null=True),
    'to_user_name': fields.String(description='去向人名称', allow_null=True),
    'action_type': fields.String(description='动作类型', example='create'),
    'action_type_label': fields.String(description='动作类型名称', example='生成菲'),
    'quantity': fields.Integer(description='动作数量', example=30),
    'action_time': fields.String(description='动作时间'),
    'remark': fields.String(description='备注', allow_null=True),
})

bundle_item_model = bundle_ns.model('BundleItemView', {
    'id': fields.Integer(description='菲ID'),
    'factory_id': fields.Integer(description='工厂ID'),
    'cutting_report_id': fields.Integer(description='裁床报工ID'),
    'template_id': fields.Integer(description='模板ID', allow_null=True),
    'template_version': fields.Integer(description='模板版本号'),
    'bundle_no': fields.String(description='菲号', example='FEI-4-2-1-1'),
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
    'cut_batch_no': fields.Integer(description='床次', example=2),
    'bed_no': fields.Integer(description='床号', example=1),
    'bundle_quantity': fields.Integer(description='数量', example=30),
    'priority': fields.String(description='优先级编码', example='urgent'),
    'priority_label': fields.String(description='优先级名称', example='加急'),
    'status': fields.String(description='状态编码', example='created'),
    'status_label': fields.String(description='状态名称', example='已生成'),
    'current_holder_user_id': fields.Integer(description='当前持有人ID', allow_null=True),
    'current_holder_name': fields.String(description='当前持有人名称', allow_null=True),
    'current_process_id': fields.Integer(description='当前工序ID', allow_null=True),
    'current_process_name': fields.String(description='当前工序名称', allow_null=True),
    'printed_content': fields.String(description='打印内容快照', allow_null=True),
    'printed_at': fields.String(description='最近打印时间', allow_null=True),
    'print_count': fields.Integer(description='打印次数', example=0),
    'issued_quantity': fields.Integer(description='累计领货数量', example=30),
    'returned_quantity': fields.Integer(description='累计交货数量', example=10),
    'in_hand_quantity': fields.Integer(description='当前在手数量', example=20),
    'remark': fields.String(description='备注', allow_null=True),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
    'flows': fields.List(fields.Nested(bundle_flow_model), description='流转记录列表'),
})

bundle_list_data = build_page_data_model(bundle_ns, 'BundleListData', bundle_item_model, items_description='菲列表')
bundle_list_response = build_page_response_model(bundle_ns, 'BundleListResponse', base_response, bundle_list_data, '菲分页数据')
bundle_item_response = bundle_ns.clone('BundleItemResponse', base_response, {
    'data': fields.Nested(bundle_item_model, description='菲详情'),
})

bundle_print_preview_model = bundle_ns.model('BundlePrintPreviewView', {
    'bundle_id': fields.Integer(description='菲ID'),
    'bundle_no': fields.String(description='菲号', example='FEI-4-2-1-1'),
    'template_id': fields.Integer(description='模板ID', allow_null=True),
    'template_version': fields.Integer(description='模板版本号'),
    'content': fields.String(description='打印内容快照'),
    'lines': fields.List(fields.String, description='按行拆分后的打印预览内容'),
})

bundle_print_preview_response = bundle_ns.clone('BundlePrintPreviewResponse', base_response, {
    'data': fields.Nested(bundle_print_preview_model, description='打印预览数据'),
})

bundle_issue_model = bundle_ns.model('BundleIssueRequest', {
    'process_id': fields.Integer(required=True, description='领货工序ID', example=1),
    'holder_user_id': fields.Integer(description='领货人ID；不传则默认当前登录人', example=15),
    'remark': fields.String(description='备注', example='车位领货'),
})

bundle_return_model = bundle_ns.model('BundleReturnRequest', {
    'quantity': fields.Integer(required=True, description='本次交货数量', example=10),
    'remark': fields.String(description='备注', example='首批交回 10 件'),
})

bundle_transfer_model = bundle_ns.model('BundleTransferRequest', {
    'to_user_id': fields.Integer(required=True, description='接收人用户ID', example=19),
    'process_id': fields.Integer(required=True, description='接收后所属工序ID', example=2),
    'remark': fields.String(description='备注', example='A 车位转给 B 车位'),
})

bundle_complete_model = bundle_ns.model('BundleCompleteRequest', {
    'remark': fields.String(description='备注', example='质检通过，确认完工'),
})

bundle_print_model = bundle_ns.model('BundlePrintRequest', {
    'remark': fields.String(description='澶囨敞', example='琛ュ墦涓€寮犵粰杞︿綅'),
})

bundle_holder_total_model = bundle_ns.model('BundleHolderTotal', {
    'user_id': fields.Integer(description='持有人ID', allow_null=True),
    'user_name': fields.String(description='持有人名称', allow_null=True),
    'bundle_count': fields.Integer(description='在手菲数量', example=2),
    'quantity': fields.Integer(description='在手件数', example=40),
})

bundle_process_total_model = bundle_ns.model('BundleProcessTotal', {
    'process_id': fields.Integer(description='工序ID', allow_null=True),
    'process_name': fields.String(description='工序名称', allow_null=True),
    'bundle_count': fields.Integer(description='在手菲数量', example=2),
    'quantity': fields.Integer(description='在手件数', example=40),
})

bundle_status_total_model = bundle_ns.model('BundleStatusTotal', {
    'status': fields.String(description='菲状态编码', example='issued'),
    'status_label': fields.String(description='菲状态名称', example='已领出'),
    'bundle_count': fields.Integer(description='在手菲数量', example=2),
    'quantity': fields.Integer(description='在手件数', example=40),
})

bundle_in_hand_statistics_model = bundle_ns.model('BundleInHandStatistics', {
    'bundle_count': fields.Integer(description='当前命中筛选条件的在手菲数量', example=2),
    'bundle_quantity': fields.Integer(description='对应菲总数量', example=60),
    'issued_quantity': fields.Integer(description='累计领货数量', example=60),
    'returned_quantity': fields.Integer(description='累计交货数量', example=20),
    'in_hand_quantity': fields.Integer(description='当前在手数量', example=40),
    'holder_totals': fields.List(fields.Nested(bundle_holder_total_model), description='按持有人汇总'),
    'process_totals': fields.List(fields.Nested(bundle_process_total_model), description='按工序汇总'),
    'status_totals': fields.List(fields.Nested(bundle_status_total_model), description='按状态汇总'),
})

bundle_in_hand_statistics_response = bundle_ns.clone('BundleInHandStatisticsResponse', base_response, {
    'data': fields.Nested(bundle_in_hand_statistics_model, description='在手统计数据'),
})

bundle_schema = ProductionBundleSchema()
bundles_schema = ProductionBundleSchema(many=True)
bundle_transfer_schema = BundleTransferSchema()
bundle_issue_schema = BundleIssueSchema()
bundle_return_schema = BundleReturnSchema()
bundle_complete_schema = BundleCompleteSchema()
bundle_print_schema = BundlePrintSchema()


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


def check_issue_permission(current_user, holder_user_id=None):
    """校验领货权限；工厂管理员和平台内部人员可代他人领货，其余仅允许给自己领货。"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    if current_user.is_internal_user or relation_type == 'owner':
        return True
    if holder_user_id and holder_user_id != current_user.id:
        return False
    return relation_type in {'employee', 'collaborator'}


def check_return_permission(current_user, bundle):
    """校验交货权限；工厂管理员和平台内部人员可代交，其余仅允许交回自己在手的菲。"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    if current_user.is_internal_user or relation_type == 'owner':
        return True
    return bundle.current_holder_user_id == current_user.id


def check_transfer_permission(current_user, bundle):
    """校验转交权限；工厂管理员和平台内部人员可代转交，其余仅允许转交自己在手的菲。"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    if current_user.is_internal_user or relation_type == 'owner':
        return True
    return bundle.current_holder_user_id == current_user.id


def check_complete_permission(current_user):
    """校验完工确认权限；当前仅允许工厂管理员或平台内部人员确认完工。"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    return current_user.is_internal_user or relation_type == 'owner'


def check_print_permission(current_user):
    """鏍￠獙鎵撳嵃鏉冮檺锛涘厑璁稿伐鍘傜鐞嗗憳銆佸憳宸ャ€佸崗浣滅敤鎴峰拰骞冲彴鍐呴儴浜哄憳鎵撳嵃鑿层€?"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    return current_user.is_internal_user or relation_type in {'owner', 'employee', 'collaborator'}


@bundle_ns.route('/in-hand-statistics')
class BundleInHandStatistics(Resource):
    @login_required
    @bundle_ns.expect(bundle_in_hand_stats_parser)
    @bundle_ns.response(200, '成功', bundle_in_hand_statistics_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """统计当前工厂的在手菲数量，并按持有人、工序和状态汇总。"""
        _, current_factory_id, error_response_obj = resolve_factory_context()
        if error_response_obj:
            return error_response_obj
        args = bundle_in_hand_stats_parser.parse_args()
        result = BundleService.get_in_hand_statistics(current_factory_id, args)
        return ApiResponse.success(result)


@bundle_ns.route('')
class BundleList(Resource):
    @login_required
    @bundle_ns.expect(bundle_query_parser)
    @bundle_ns.response(200, '成功', bundle_list_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """分页查询当前工厂的菲列表。"""
        _, current_factory_id, error_response_obj = resolve_factory_context()
        if error_response_obj:
            return error_response_obj
        args = bundle_query_parser.parse_args()
        result = BundleService.get_bundle_list(current_factory_id, args)
        return ApiResponse.success({
            'items': bundles_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages'],
        })


@bundle_ns.route('/<int:bundle_id>')
class BundleDetail(Resource):
    @login_required
    @bundle_ns.response(200, '成功', bundle_item_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    @bundle_ns.response(404, '菲不存在', error_response)
    def get(self, bundle_id):
        """查询指定菲详情。"""
        _, current_factory_id, error_response_obj = resolve_factory_context()
        if error_response_obj:
            return error_response_obj
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        return ApiResponse.success(bundle_schema.dump(bundle))


@bundle_ns.route('/<int:bundle_id>/issue')
class BundleIssue(Resource):
    @login_required
    @bundle_ns.expect(bundle_issue_model)
    @bundle_ns.response(200, '领货成功', bundle_item_response)
    @bundle_ns.response(400, '参数错误', error_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    def post(self, bundle_id):
        """整菲领货：把指定菲挂到某个工序和领货人名下。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        try:
            data = bundle_issue_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        if not check_issue_permission(current_user, data.get('holder_user_id')):
            return ApiResponse.error('当前用户没有代他人领货权限', 403)
        bundle, error = BundleService.issue_bundle(
            bundle,
            operator_user=current_user,
            process_id=data['process_id'],
            holder_user_id=data.get('holder_user_id'),
            remark=data.get('remark', ''),
        )
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_schema.dump(bundle), '领货成功')


@bundle_ns.route('/<int:bundle_id>/return')
class BundleReturn(Resource):
    @login_required
    @bundle_ns.expect(bundle_return_model)
    @bundle_ns.response(200, '交货成功', bundle_item_response)
    @bundle_ns.response(400, '参数错误', error_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    def post(self, bundle_id):
        """交货回仓：支持分次交回，全部交回后自动清空当前持有人。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        if not check_return_permission(current_user, bundle):
            return ApiResponse.error('当前用户没有交回这张菲的权限', 403)
        try:
            data = bundle_return_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        bundle, error = BundleService.return_bundle(
            bundle,
            operator_user=current_user,
            quantity=data['quantity'],
            remark=data.get('remark', ''),
        )
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_schema.dump(bundle), '交货成功')


@bundle_ns.route('/<int:bundle_id>/transfer')
class BundleTransfer(Resource):
    @login_required
    @bundle_ns.expect(bundle_transfer_model)
    @bundle_ns.response(200, '转交成功', bundle_item_response)
    @bundle_ns.response(400, '参数错误', error_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    def post(self, bundle_id):
        """转交当前在手菲给新的接收人，并同步更新当前工序。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        if not check_transfer_permission(current_user, bundle):
            return ApiResponse.error('当前用户没有转交这张菲的权限', 403)
        try:
            data = bundle_transfer_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        bundle, error = BundleService.transfer_bundle(
            bundle,
            operator_user=current_user,
            to_user_id=data['to_user_id'],
            process_id=data['process_id'],
            remark=data.get('remark', ''),
        )
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_schema.dump(bundle), '转交成功')


@bundle_ns.route('/<int:bundle_id>/complete')
class BundleComplete(Resource):
    @login_required
    @bundle_ns.expect(bundle_complete_model)
    @bundle_ns.response(200, '完工确认成功', bundle_item_response)
    @bundle_ns.response(400, '参数错误', error_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    def post(self, bundle_id):
        """确认指定菲已经全部完工。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        if not check_complete_permission(current_user):
            return ApiResponse.error('当前用户没有完工确认权限', 403)
        try:
            data = bundle_complete_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        bundle, error = BundleService.complete_bundle(
            bundle,
            operator_user=current_user,
            remark=data.get('remark', ''),
        )
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_schema.dump(bundle), '完工确认成功')


@bundle_ns.route('/<int:bundle_id>/print-preview')
class BundlePrintPreview(Resource):
    @login_required
    @bundle_ns.response(200, '成功', bundle_print_preview_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    @bundle_ns.response(404, '菲不存在', error_response)
    def get(self, bundle_id):
        """查询指定菲的打印预览内容。"""
        _, current_factory_id, error_response_obj = resolve_factory_context()
        if error_response_obj:
            return error_response_obj
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        return ApiResponse.success(BundleService.build_print_preview(bundle))


@bundle_ns.route('/<int:bundle_id>/print')
class BundlePrint(Resource):
    @login_required
    @bundle_ns.expect(bundle_print_model)
    @bundle_ns.response(200, '打印登记成功', bundle_item_response)
    @bundle_ns.response(400, '参数错误', error_response)
    @bundle_ns.response(401, '未登录', unauthorized_response)
    @bundle_ns.response(403, '无权限', error_response)
    @bundle_ns.response(404, '菲不存在', error_response)
    def post(self, bundle_id):
        """执行菲打印登记，更新最近打印时间、打印次数，并记录打印动作。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_print_permission(current_user):
            return ApiResponse.error('当前用户没有打印菲的权限', 403)
        bundle = BundleService.get_bundle_by_id(bundle_id)
        if not bundle or bundle.factory_id != current_factory_id:
            return ApiResponse.error('菲不存在', 404)
        try:
            data = bundle_print_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        bundle, error = BundleService.print_bundle(
            bundle,
            operator_user=current_user,
            remark=data.get('remark', ''),
        )
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_schema.dump(bundle), '打印登记成功')
