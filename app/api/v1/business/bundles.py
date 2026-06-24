"""菲查询、流转与打印接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields

from app.api.common.business_resource_helpers import (
    get_accessible_business_resource_or_error,
    get_business_request_context,
    get_writable_business_resource_or_error,
)
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.api.common.response_helpers import load_json_or_error, success_schema_page
from app.api.common.serializers import serialize_schema
from app.constants.permissions import (
    PERM_BUSINESS_BUNDLE_COMPLETE,
    PERM_BUSINESS_BUNDLE_ISSUE,
    PERM_BUSINESS_BUNDLE_PRINT,
    PERM_BUSINESS_BUNDLE_QUERY,
    PERM_BUSINESS_BUNDLE_RETURN,
    PERM_BUSINESS_BUNDLE_TRANSFER,
)
from app.schemas.business.bundle import (
    BundleCompleteSchema,
    BundleIssueSchema,
    BundlePrintSchema,
    BundleReturnSchema,
    BundleTransferSchema,
    ProductionBundleSchema,
)
from app.services import BundleService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

bundle_ns = Namespace("菲管理-bundles", description="菲查询、流转与打印管理")

common = get_common_models(bundle_ns)
base_response = common["base_response"]
error_response = common["error_response"]
unauthorized_response = common["unauthorized_response"]
forbidden_response = common["forbidden_response"]
build_page_data_model = common["build_page_data_model"]
build_page_response_model = common["build_page_response_model"]
build_item_response_model = common["build_item_response_model"]

bundle_query_parser = page_parser.copy()
bundle_query_parser.add_argument("factory_id", type=int, location="args", help="工厂 ID，平台内部用户可选传")
bundle_query_parser.add_argument("order_no", type=str, location="args", help="订单号")
bundle_query_parser.add_argument("style_no", type=str, location="args", help="款号")
bundle_query_parser.add_argument("cut_batch_no", type=int, location="args", help="床次")
bundle_query_parser.add_argument(
    "status",
    type=str,
    location="args",
    help="菲状态",
    choices=["created", "issued", "in_progress", "returned", "completed", "rework", "cancelled"],
)
bundle_query_parser.add_argument(
    "priority",
    type=str,
    location="args",
    help="优先级",
    choices=["normal", "urgent", "top"],
)

bundle_in_hand_stats_parser = new_query_parser()
bundle_in_hand_stats_parser.add_argument("factory_id", type=int, location="args", help="工厂 ID，平台内部用户可选传")
bundle_in_hand_stats_parser.add_argument("holder_user_id", type=int, location="args", help="持有人用户 ID")
bundle_in_hand_stats_parser.add_argument("process_id", type=int, location="args", help="当前工序 ID")

bundle_flow_model = bundle_ns.model(
    "BundleFlowView",
    {
        "id": fields.Integer(description="流转记录 ID"),
        "process_id": fields.Integer(description="工序 ID", allow_null=True),
        "process_name": fields.String(description="工序名称", allow_null=True),
        "user_id": fields.Integer(description="操作人 ID", allow_null=True),
        "user_name": fields.String(description="操作人名称", allow_null=True),
        "from_user_id": fields.Integer(description="来源人 ID", allow_null=True),
        "from_user_name": fields.String(description="来源人名称", allow_null=True),
        "to_user_id": fields.Integer(description="去向人 ID", allow_null=True),
        "to_user_name": fields.String(description="去向人名称", allow_null=True),
        "action_type": fields.String(description="动作类型", example="create"),
        "action_type_label": fields.String(description="动作类型名称", example="生成菲"),
        "quantity": fields.Integer(description="动作数量", example=30),
        "action_time": fields.String(description="动作时间"),
        "remark": fields.String(description="备注", allow_null=True),
    },
)

bundle_item_model = bundle_ns.model(
    "BundleItemView",
    {
        "id": fields.Integer(description="菲 ID"),
        "factory_id": fields.Integer(description="工厂 ID"),
        "cutting_report_id": fields.Integer(description="裁床报工 ID"),
        "template_id": fields.Integer(description="模板 ID", allow_null=True),
        "template_version": fields.Integer(description="模板版本号"),
        "bundle_no": fields.String(description="菲号", example="FEI-4-2-1-1"),
        "order_id": fields.Integer(description="订单 ID"),
        "order_detail_id": fields.Integer(description="订单明细 ID"),
        "order_detail_sku_id": fields.Integer(description="订单 SKU ID"),
        "style_id": fields.Integer(description="款号 ID"),
        "style_no": fields.String(description="款号", example="1235#"),
        "style_name": fields.String(description="款号名称", allow_null=True),
        "color_id": fields.Integer(description="颜色 ID", allow_null=True),
        "color_name": fields.String(description="颜色名称", allow_null=True),
        "size_id": fields.Integer(description="尺码 ID", allow_null=True),
        "size_name": fields.String(description="尺码名称", allow_null=True),
        "cut_batch_no": fields.Integer(description="床次", example=2),
        "bed_no": fields.Integer(description="床号", example=1),
        "bundle_quantity": fields.Integer(description="数量", example=30),
        "priority": fields.String(description="优先级编码", example="urgent"),
        "priority_label": fields.String(description="优先级名称", example="加急"),
        "status": fields.String(description="状态编码", example="created"),
        "status_label": fields.String(description="状态名称", example="已生成"),
        "current_holder_user_id": fields.Integer(description="当前持有人 ID", allow_null=True),
        "current_holder_name": fields.String(description="当前持有人名称", allow_null=True),
        "current_process_id": fields.Integer(description="当前工序 ID", allow_null=True),
        "current_process_name": fields.String(description="当前工序名称", allow_null=True),
        "printed_content": fields.String(description="打印内容快照", allow_null=True),
        "printed_at": fields.String(description="最近打印时间", allow_null=True),
        "print_count": fields.Integer(description="打印次数", example=0),
        "issued_quantity": fields.Integer(description="累计领货数量", example=30),
        "returned_quantity": fields.Integer(description="累计交货数量", example=10),
        "in_hand_quantity": fields.Integer(description="当前在手数量", example=20),
        "remark": fields.String(description="备注", allow_null=True),
        "create_time": fields.String(description="创建时间"),
        "update_time": fields.String(description="更新时间"),
        "flows": fields.List(fields.Nested(bundle_flow_model), description="流转记录列表"),
    },
)

bundle_list_data = build_page_data_model(
    bundle_ns,
    "BundleListData",
    bundle_item_model,
    items_description="菲列表",
)
bundle_list_response = build_page_response_model(
    bundle_ns,
    "BundleListResponse",
    base_response,
    bundle_list_data,
    "菲分页数据",
)
bundle_item_response = build_item_response_model(bundle_ns, "BundleItemResponse", base_response, bundle_item_model, "菲详情")

bundle_print_preview_model = bundle_ns.model(
    "BundlePrintPreviewView",
    {
        "bundle_id": fields.Integer(description="菲 ID"),
        "bundle_no": fields.String(description="菲号", example="FEI-4-2-1-1"),
        "template_id": fields.Integer(description="模板 ID", allow_null=True),
        "template_version": fields.Integer(description="模板版本号", allow_null=True),
        "content": fields.String(description="打印内容快照"),
        "lines": fields.List(fields.String, description="按行拆分后的打印预览内容"),
    },
)
bundle_print_preview_response = build_item_response_model(
    bundle_ns,
    "BundlePrintPreviewResponse",
    base_response,
    bundle_print_preview_model,
    "打印预览数据",
)

bundle_issue_model = bundle_ns.model(
    "BundleIssueRequest",
    {
        "process_id": fields.Integer(required=True, description="领货工序 ID", example=1),
        "holder_user_id": fields.Integer(description="领货人 ID，不传则默认当前登录人", example=15),
        "remark": fields.String(description="备注", example="车位领货"),
    },
)

bundle_return_model = bundle_ns.model(
    "BundleReturnRequest",
    {
        "quantity": fields.Integer(required=True, description="本次交货数量", example=10),
        "remark": fields.String(description="备注", example="首批交回 10 件"),
    },
)

bundle_transfer_model = bundle_ns.model(
    "BundleTransferRequest",
    {
        "to_user_id": fields.Integer(required=True, description="接收人用户 ID", example=19),
        "process_id": fields.Integer(required=True, description="接收后所属工序 ID", example=2),
        "remark": fields.String(description="备注", example="A 车位转给 B 车位"),
    },
)

bundle_complete_model = bundle_ns.model(
    "BundleCompleteRequest",
    {"remark": fields.String(description="备注", example="质检通过，确认完工")},
)

bundle_print_model = bundle_ns.model(
    "BundlePrintRequest",
    {"remark": fields.String(description="备注", example="补打一张")},
)

bundle_holder_total_model = bundle_ns.model(
    "BundleHolderTotal",
    {
        "user_id": fields.Integer(description="持有人 ID", allow_null=True),
        "user_name": fields.String(description="持有人名称", allow_null=True),
        "bundle_count": fields.Integer(description="在手菲数量", example=2),
        "quantity": fields.Integer(description="在手件数", example=40),
    },
)

bundle_process_total_model = bundle_ns.model(
    "BundleProcessTotal",
    {
        "process_id": fields.Integer(description="工序 ID", allow_null=True),
        "process_name": fields.String(description="工序名称", allow_null=True),
        "bundle_count": fields.Integer(description="在手菲数量", example=2),
        "quantity": fields.Integer(description="在手件数", example=40),
    },
)

bundle_status_total_model = bundle_ns.model(
    "BundleStatusTotal",
    {
        "status": fields.String(description="菲状态编码", example="issued"),
        "status_label": fields.String(description="菲状态名称", example="已领货"),
        "bundle_count": fields.Integer(description="菲数量", example=2),
        "quantity": fields.Integer(description="件数", example=40),
    },
)

bundle_in_hand_statistics_model = bundle_ns.model(
    "BundleInHandStatistics",
    {
        "bundle_count": fields.Integer(description="命中筛选条件的在手菲数量", example=2),
        "bundle_quantity": fields.Integer(description="对应菲总数量", example=60),
        "issued_quantity": fields.Integer(description="累计领货数量", example=60),
        "returned_quantity": fields.Integer(description="累计交货数量", example=20),
        "in_hand_quantity": fields.Integer(description="当前在手数量", example=40),
        "holder_totals": fields.List(fields.Nested(bundle_holder_total_model), description="按持有人汇总"),
        "process_totals": fields.List(fields.Nested(bundle_process_total_model), description="按工序汇总"),
        "status_totals": fields.List(fields.Nested(bundle_status_total_model), description="按状态汇总"),
    },
)
bundle_in_hand_statistics_response = build_item_response_model(
    bundle_ns,
    "BundleInHandStatisticsResponse",
    base_response,
    bundle_in_hand_statistics_model,
    "在手统计数据",
)

bundle_schema = ProductionBundleSchema()
bundle_transfer_schema = BundleTransferSchema()
bundle_issue_schema = BundleIssueSchema()
bundle_return_schema = BundleReturnSchema()
bundle_complete_schema = BundleCompleteSchema()
bundle_print_schema = BundlePrintSchema()


def get_accessible_bundle_or_error(bundle_id):
    """查询当前上下文可访问的菲，不可访问时返回统一错误响应。"""
    return get_accessible_business_resource_or_error(
        bundle_id,
        BundleService.get_bundle_by_id,
        BundleService.check_permission,
        "菲不存在",
    )


def get_writable_bundle_or_error(bundle_id):
    """查询当前工厂下可写入的菲，不存在时返回统一错误响应。"""
    return get_writable_business_resource_or_error(
        bundle_id,
        BundleService.get_bundle_by_id,
        BundleService.check_permission,
        "菲不存在",
    )


@bundle_ns.route("/in-hand-statistics")
class BundleInHandStatistics(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_QUERY)
    @bundle_ns.expect(bundle_in_hand_stats_parser)
    @bundle_ns.response(200, "查询成功", bundle_in_hand_statistics_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    def get(self):
        """查询菲在手统计接口，支持按工厂、持有人和工序维度汇总。"""
        args = bundle_in_hand_stats_parser.parse_args()
        current_user, current_factory_id, error_response_obj = get_business_request_context(
            query_factory_id=args.get("factory_id"),
            allow_internal_without_factory=True,
        )
        if error_response_obj:
            return error_response_obj

        result = BundleService.get_in_hand_statistics(current_user, current_factory_id, args)
        return ApiResponse.success(result)


@bundle_ns.route("")
class BundleList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_QUERY)
    @bundle_ns.expect(bundle_query_parser)
    @bundle_ns.response(200, "查询成功", bundle_list_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    def get(self):
        """分页查询菲列表接口，平台内部用户可跨工厂读取，外部用户按当前工厂读取。"""
        args = bundle_query_parser.parse_args()
        current_user, current_factory_id, error_response_obj = get_business_request_context(
            query_factory_id=args.get("factory_id"),
            allow_internal_without_factory=True,
        )
        if error_response_obj:
            return error_response_obj

        result = BundleService.get_bundle_list(current_user, current_factory_id, args)
        return success_schema_page(result, bundle_schema)


@bundle_ns.route("/<int:bundle_id>")
class BundleDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_QUERY)
    @bundle_ns.response(200, "查询成功", bundle_item_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def get(self, bundle_id):
        """查询菲详情接口，返回菲基础信息、流转记录和打印快照。"""
        _, _, bundle, error_response_data = get_accessible_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        return ApiResponse.success(serialize_schema(bundle_schema, bundle))


@bundle_ns.route("/<int:bundle_id>/issue")
class BundleIssue(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_ISSUE)
    @bundle_ns.expect(bundle_issue_model)
    @bundle_ns.response(200, "领货成功", bundle_item_response)
    @bundle_ns.response(400, "参数错误", error_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def post(self, bundle_id):
        """菲领货接口，把整张菲挂到指定工序和持有人名下。"""
        current_user, _, bundle, error_response_data = get_writable_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(bundle_issue_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        bundle, error = BundleService.issue_bundle(
            bundle,
            operator_user=current_user,
            process_id=data["process_id"],
            holder_user_id=data.get("holder_user_id"),
            remark=data.get("remark", ""),
        )
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(bundle_schema, bundle), "领货成功")


@bundle_ns.route("/<int:bundle_id>/return")
class BundleReturn(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_RETURN)
    @bundle_ns.expect(bundle_return_model)
    @bundle_ns.response(200, "交货成功", bundle_item_response)
    @bundle_ns.response(400, "参数错误", error_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def post(self, bundle_id):
        """菲交货接口，支持分次交回，全部交回后自动清空当前持有人和工序。"""
        current_user, _, bundle, error_response_data = get_writable_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(bundle_return_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        bundle, error = BundleService.return_bundle(
            bundle,
            operator_user=current_user,
            quantity=data["quantity"],
            remark=data.get("remark", ""),
        )
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(bundle_schema, bundle), "交货成功")


@bundle_ns.route("/<int:bundle_id>/transfer")
class BundleTransfer(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_TRANSFER)
    @bundle_ns.expect(bundle_transfer_model)
    @bundle_ns.response(200, "转交成功", bundle_item_response)
    @bundle_ns.response(400, "参数错误", error_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def post(self, bundle_id):
        """菲转交接口，把当前在手菲转给新的接收人，并同步更新所属工序。"""
        current_user, _, bundle, error_response_data = get_writable_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(bundle_transfer_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        bundle, error = BundleService.transfer_bundle(
            bundle,
            operator_user=current_user,
            to_user_id=data["to_user_id"],
            process_id=data["process_id"],
            remark=data.get("remark", ""),
        )
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(bundle_schema, bundle), "转交成功")


@bundle_ns.route("/<int:bundle_id>/complete")
class BundleComplete(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_COMPLETE)
    @bundle_ns.expect(bundle_complete_model)
    @bundle_ns.response(200, "完工确认成功", bundle_item_response)
    @bundle_ns.response(400, "参数错误", error_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def post(self, bundle_id):
        """菲完工确认接口，要求当前菲已全部交回后才能确认完工。"""
        current_user, _, bundle, error_response_data = get_writable_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(bundle_complete_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        bundle, error = BundleService.complete_bundle(
            bundle,
            operator_user=current_user,
            remark=data.get("remark", ""),
        )
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(bundle_schema, bundle), "完工确认成功")


@bundle_ns.route("/<int:bundle_id>/print-preview")
class BundlePrintPreview(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_QUERY)
    @bundle_ns.response(200, "查询成功", bundle_print_preview_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def get(self, bundle_id):
        """查询菲打印预览接口，返回完整打印文本和按行拆分结果。"""
        _, _, bundle, error_response_data = get_accessible_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        return ApiResponse.success(BundleService.build_print_preview(bundle))


@bundle_ns.route("/<int:bundle_id>/print")
class BundlePrint(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_BUNDLE_PRINT)
    @bundle_ns.expect(bundle_print_model)
    @bundle_ns.response(200, "打印登记成功", bundle_item_response)
    @bundle_ns.response(400, "参数错误", error_response)
    @bundle_ns.response(401, "未登录", unauthorized_response)
    @bundle_ns.response(403, "无权限", forbidden_response)
    @bundle_ns.response(404, "菲不存在", error_response)
    def post(self, bundle_id):
        """菲打印登记接口，更新最近打印时间、打印次数并写入打印流转记录。"""
        current_user, _, bundle, error_response_data = get_writable_bundle_or_error(bundle_id)
        if error_response_data:
            return error_response_data

        data, validation_error = load_json_or_error(bundle_print_schema, request.get_json() or {})
        if validation_error:
            return validation_error

        bundle, error = BundleService.print_bundle(
            bundle,
            operator_user=current_user,
            remark=data.get("remark", ""),
        )
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(serialize_schema(bundle_schema, bundle), "打印登记成功")
