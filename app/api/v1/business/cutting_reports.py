"""裁床报工接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.factory_context import resolve_read_factory_context, resolve_write_factory_context
from app.api.common.models import get_common_models
from app.api.common.parsers import page_with_date_parser
from app.constants.permissions import (
    PERM_BUSINESS_CUTTING_REPORT_ADD,
    PERM_BUSINESS_CUTTING_REPORT_DELETE,
    PERM_BUSINESS_CUTTING_REPORT_QUERY,
)
from app.schemas.business.cutting_report import CuttingReportCreateSchema, WorkCuttingReportSchema
from app.services import CuttingReportService
from app.utils.business_permissions import button_permission
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

cutting_report_ns = Namespace("裁床报工-cutting-reports", description="裁床报工与菲生成管理")

common = get_common_models(cutting_report_ns)
base_response = common["base_response"]
error_response = common["error_response"]
unauthorized_response = common["unauthorized_response"]
forbidden_response = common["forbidden_response"]
build_page_data_model = common["build_page_data_model"]
build_page_response_model = common["build_page_response_model"]

cutting_report_query_parser = page_with_date_parser.copy()
cutting_report_query_parser.add_argument("factory_id", type=int, location="args", help="工厂 ID；平台内部用户可选传")
cutting_report_query_parser.add_argument("cut_batch_no", type=int, location="args", help="床次")
cutting_report_query_parser.add_argument("order_detail_sku_id", type=int, location="args", help="订单 SKU ID")

cutting_bundle_input_model = cutting_report_ns.model(
    "CuttingBundleInput",
    {
        "bed_no": fields.Integer(description="床号", example=1, default=1),
        "bundle_quantity": fields.Integer(required=True, description="当前菲数量", example=30),
        "priority": fields.String(description="优先级：normal/urgent/top", example="urgent", default="normal"),
        "remark": fields.String(description="备注", example="第一床加急"),
    },
)

cutting_report_create_model = cutting_report_ns.model(
    "CuttingReportCreate",
    {
        "order_detail_sku_id": fields.Integer(required=True, description="订单 SKU ID", example=8),
        "cut_date": fields.String(required=True, description="裁床日期", example="2026-05-15"),
        "cut_quantity": fields.Integer(required=True, description="实裁数量", example=60),
        "template_id": fields.Integer(description="菲模板 ID；不传则按工厂默认模板生成", example=2),
        "remark": fields.String(description="备注", example="按床次 2 开裁"),
        "bundles": fields.List(
            fields.Nested(cutting_bundle_input_model),
            description="生成菲明细；不传则默认生成 1 张菲",
        ),
    },
)

cutting_report_bundle_view_model = cutting_report_ns.model(
    "CuttingReportBundleView",
    {
        "id": fields.Integer(description="菲 ID"),
        "bundle_no": fields.String(description="菲号", example="FEI-4-2-1-1"),
        "cut_batch_no": fields.Integer(description="床次", example=2),
        "bed_no": fields.Integer(description="床号", example=1),
        "bundle_quantity": fields.Integer(description="数量", example=30),
        "priority": fields.String(description="优先级编码", example="urgent"),
        "priority_label": fields.String(description="优先级名称", example="加急"),
        "status": fields.String(description="状态编码", example="created"),
        "status_label": fields.String(description="状态名称", example="已生成"),
        "printed_content": fields.String(description="打印内容快照"),
    },
)

cutting_report_item_model = cutting_report_ns.model(
    "CuttingReportItemView",
    {
        "id": fields.Integer(description="裁床报工 ID"),
        "factory_id": fields.Integer(description="工厂 ID"),
        "template_id": fields.Integer(description="模板 ID", allow_null=True),
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
        "report_user_id": fields.Integer(description="报工人 ID"),
        "report_user_name": fields.String(description="报工人名称"),
        "cut_batch_no": fields.Integer(description="床次", example=2),
        "cut_date": fields.String(description="裁床日期", example="2026-05-15"),
        "cut_quantity": fields.Integer(description="实裁数量", example=60),
        "bundle_count": fields.Integer(description="生成菲数量", example=2),
        "status": fields.String(description="状态编码", example="active"),
        "status_label": fields.String(description="状态名称", example="生效中"),
        "remark": fields.String(description="备注", allow_null=True),
        "create_time": fields.String(description="创建时间"),
        "update_time": fields.String(description="更新时间"),
        "bundles": fields.List(fields.Nested(cutting_report_bundle_view_model), description="本次生成的菲列表"),
    },
)

cutting_report_list_data = build_page_data_model(
    cutting_report_ns,
    "CuttingReportListData",
    cutting_report_item_model,
    items_description="裁床报工列表",
)
cutting_report_list_response = build_page_response_model(
    cutting_report_ns,
    "CuttingReportListResponse",
    base_response,
    cutting_report_list_data,
    "裁床报工分页数据",
)
cutting_report_item_response = cutting_report_ns.clone(
    "CuttingReportItemResponse",
    base_response,
    {"data": fields.Nested(cutting_report_item_model, description="裁床报工详情")},
)

cutting_report_schema = WorkCuttingReportSchema()
cutting_reports_schema = WorkCuttingReportSchema(many=True)
cutting_report_create_schema = CuttingReportCreateSchema()


def get_accessible_cutting_report_or_error(report_id):
    """查询当前上下文可访问的裁床报工，不可访问时返回统一错误响应。"""
    current_user, current_factory_id, error_response_obj = resolve_read_factory_context(
        allow_internal_without_factory=True,
    )
    if error_response_obj:
        return None, None, None, error_response_obj

    report = CuttingReportService.get_cutting_report_by_id(report_id)
    if not report:
        return None, None, None, ApiResponse.error("裁床报工不存在", 404)

    has_permission, error = CuttingReportService.check_permission(current_user, current_factory_id, report)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, report, None


def get_writable_cutting_report_or_error(report_id):
    """查询当前工厂下可撤销的裁床报工，不存在时返回统一错误响应。"""
    current_user, current_factory_id, error_response_obj = resolve_write_factory_context()
    if error_response_obj:
        return None, None, None, error_response_obj

    report = CuttingReportService.get_cutting_report_by_id(report_id)
    if not report or report.factory_id != current_factory_id:
        return None, None, None, ApiResponse.error("裁床报工不存在", 404)
    has_permission, error = CuttingReportService.check_permission(current_user, current_factory_id, report)
    if not has_permission:
        return None, None, None, ApiResponse.error(error, 403)
    return current_user, current_factory_id, report, None


@cutting_report_ns.route("")
class CuttingReportList(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_CUTTING_REPORT_QUERY)
    @cutting_report_ns.expect(cutting_report_query_parser)
    @cutting_report_ns.response(200, "查询成功", cutting_report_list_response)
    @cutting_report_ns.response(401, "未登录", unauthorized_response)
    @cutting_report_ns.response(403, "无权限", forbidden_response)
    def get(self):
        """分页查询裁床报工接口，平台内部用户可跨工厂读取，外部用户按当前工厂读取。"""
        args = cutting_report_query_parser.parse_args()
        current_user, current_factory_id, error_response_obj = resolve_read_factory_context(
            query_factory_id=args.get("factory_id"),
            allow_internal_without_factory=True,
        )
        if error_response_obj:
            return error_response_obj

        result = CuttingReportService.get_cutting_report_list(current_user, current_factory_id, args)
        return ApiResponse.success_page_result(result, cutting_reports_schema.dump(result["items"]))

    @login_required
    @button_permission(PERM_BUSINESS_CUTTING_REPORT_ADD)
    @cutting_report_ns.expect(cutting_report_create_model)
    @cutting_report_ns.response(201, "创建成功", cutting_report_item_response)
    @cutting_report_ns.response(400, "参数错误", error_response)
    @cutting_report_ns.response(401, "未登录", unauthorized_response)
    @cutting_report_ns.response(403, "无权限", forbidden_response)
    def post(self):
        """创建裁床报工接口，并按模板自动生成一张或多张菲。"""
        current_user, current_factory_id, error_response_obj = resolve_write_factory_context()
        if error_response_obj:
            return error_response_obj

        try:
            data = cutting_report_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        report, error = CuttingReportService.create_cutting_report(current_user, current_factory_id, data)
        if error:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(cutting_report_schema.dump(report), "创建成功", 201)


@cutting_report_ns.route("/<int:report_id>")
class CuttingReportDetail(Resource):
    @login_required
    @button_permission(PERM_BUSINESS_CUTTING_REPORT_QUERY)
    @cutting_report_ns.response(200, "查询成功", cutting_report_item_response)
    @cutting_report_ns.response(401, "未登录", unauthorized_response)
    @cutting_report_ns.response(403, "无权限", forbidden_response)
    @cutting_report_ns.response(404, "裁床报工不存在", error_response)
    def get(self, report_id):
        """查询裁床报工详情接口，返回报工主信息及生成的菲列表。"""
        _, _, report, error_response_data = get_accessible_cutting_report_or_error(report_id)
        if error_response_data:
            return error_response_data

        return ApiResponse.success(cutting_report_schema.dump(report))

    @login_required
    @button_permission(PERM_BUSINESS_CUTTING_REPORT_DELETE)
    @cutting_report_ns.response(200, "删除成功", base_response)
    @cutting_report_ns.response(401, "未登录", unauthorized_response)
    @cutting_report_ns.response(403, "无权限", forbidden_response)
    @cutting_report_ns.response(404, "裁床报工不存在", error_response)
    def delete(self, report_id):
        """删除裁床报工接口，仅允许撤销尚未发生后续流转的裁床报工。"""
        _, _, report, error_response_data = get_writable_cutting_report_or_error(report_id)
        if error_response_data:
            return error_response_data

        success, error = CuttingReportService.delete_cutting_report(report)
        if not success:
            return ApiResponse.error(error, 400)

        return ApiResponse.success(message="删除成功")
