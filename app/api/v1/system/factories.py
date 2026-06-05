"""工厂管理接口。"""

from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import require_current_user
from app.api.common.models import get_common_models
from app.api.common.parsers import new_query_parser, page_parser
from app.schemas.system.factory import FactoryAddUserSchema, FactoryBindSchema, FactoryCreateSchema, FactorySchema, FactoryUpdateSchema
from app.services import FactoryService
from app.utils.permissions import login_required, permission_required
from app.utils.response import ApiResponse

factory_ns = Namespace("工厂管理-factories", description="工厂管理")

common = get_common_models(factory_ns)
base_response = common["base_response"]
error_response = common["error_response"]
unauthorized_response = common["unauthorized_response"]
forbidden_response = common["forbidden_response"]

factory_query_parser = page_parser.copy()
factory_query_parser.add_argument("name", type=str, location="args", help="工厂名称（模糊查询）")
factory_query_parser.add_argument("status", type=int, location="args", help="状态", choices=[0, 1])

factory_filter_parser = new_query_parser()
factory_filter_parser.add_argument("name", type=str, location="args", help="工厂名称（模糊查询）")
factory_filter_parser.add_argument("status", type=int, location="args", help="状态", choices=[0, 1])

factory_user_query_parser = page_parser.copy()
factory_user_query_parser.add_argument("username", type=str, location="args", help="用户名（模糊查询）")
factory_user_query_parser.add_argument("status", type=int, location="args", help="状态", choices=[0, 1])
factory_user_query_parser.add_argument(
    "relation_type",
    type=str,
    location="args",
    help="关联关系类型",
    choices=["owner", "employee", "customer", "collaborator"],
)
factory_user_query_parser.add_argument(
    "collaborator_type",
    type=str,
    location="args",
    help="协作方类型",
    choices=["button_partner", "shrink_partner", "print_partner", "other_partner"],
)

factory_create_model = factory_ns.model(
    "FactoryCreate",
    {
        "name": fields.String(required=True, description="工厂名称", example="测试工厂"),
        "contact_person": fields.String(description="联系人", example="张三"),
        "contact_phone": fields.String(description="联系电话", example="13800138000"),
        "address": fields.String(description="地址", example="广东省深圳市南山区"),
        "service_expire_date": fields.String(description="服务到期日期", example="2026-12-31"),
        "remark": fields.String(description="备注"),
    },
)

factory_update_model = factory_ns.model(
    "FactoryUpdate",
    {
        "name": fields.String(description="工厂名称"),
        "contact_person": fields.String(description="联系人"),
        "contact_phone": fields.String(description="联系电话"),
        "address": fields.String(description="地址"),
        "service_expire_date": fields.String(description="服务到期日期", example="2026-12-31"),
        "status": fields.Integer(description="状态", choices=[0, 1]),
        "remark": fields.String(description="备注"),
    },
)

add_user_model = factory_ns.model(
    "AddUser",
    {
        "user_id": fields.Integer(required=True, description="用户 ID", example=1),
        "relation_type": fields.String(
            required=True,
            description="关联关系类型",
            choices=["owner", "employee", "customer", "collaborator"],
        ),
        "collaborator_type": fields.String(
            description="协作方类型，仅在 relation_type=collaborator 时使用",
            choices=["button_partner", "shrink_partner", "print_partner", "other_partner"],
        ),
    },
)

qrcode_response_data = factory_ns.model(
    "QRCodeResponseData",
    {
        "qrcode": fields.String(description="二维码内容或地址", example="factory-bind://TEST001?key=abc123"),
        "qrcode_key": fields.String(description="二维码绑定键值", example="abc123"),
    },
)
qrcode_response = factory_ns.clone(
    "QRCodeResponse",
    base_response,
    {"data": fields.Nested(qrcode_response_data, description="二维码数据")},
)

bind_factory_model = factory_ns.model(
    "BindFactory",
    {"key": fields.String(required=True, description="二维码标识")},
)
bind_response_data = factory_ns.model(
    "BindResponseData",
    {
        "factory_id": fields.Integer(description="工厂 ID", example=1),
        "factory_name": fields.String(description="工厂名称", example="测试工厂"),
        "factory_code": fields.String(description="工厂编码", example="TEST001"),
    },
)
bind_response = factory_ns.clone(
    "BindResponse",
    base_response,
    {"data": fields.Nested(bind_response_data, description="绑定结果数据")},
)

factory_item_model = factory_ns.model(
    "FactoryItem",
    {
        "id": fields.Integer(description="工厂 ID", example=1),
        "name": fields.String(description="工厂名称", example="测试工厂"),
        "code": fields.String(description="工厂编码", example="TEST001"),
        "contact_person": fields.String(description="联系人", example="张三"),
        "contact_phone": fields.String(description="联系电话", example="13800138000"),
        "address": fields.String(description="地址", example="广东省深圳市南山区"),
        "status": fields.Integer(description="状态", example=1),
        "qrcode": fields.String(description="工厂二维码", example=None),
        "remark": fields.String(description="备注", example=None),
        "service_expire_date": fields.String(description="服务到期日期", example=None),
        "service_status": fields.String(description="服务状态", example="active"),
        "create_time": fields.String(description="创建时间", example="2026-04-21 01:17:24"),
        "update_time": fields.String(description="更新时间", example="2026-04-21 01:17:24"),
    },
)

factory_list_data = factory_ns.model(
    "FactoryListData",
    {
        "items": fields.List(fields.Nested(factory_item_model), description="工厂列表"),
        "total": fields.Integer(description="总条数"),
        "page": fields.Integer(description="当前页码"),
        "page_size": fields.Integer(description="每页条数"),
        "pages": fields.Integer(description="总页数"),
    },
)

factory_option_model = factory_ns.model(
    "FactoryOptionItem",
    {
        "id": fields.Integer(description="工厂 ID", example=1),
        "name": fields.String(description="工厂名称", example="测试工厂"),
        "code": fields.String(description="工厂编码", example="TEST001"),
    },
)

factory_create_response_data = factory_ns.model(
    "FactoryCreateResponseData",
    {
        "id": fields.Integer(description="工厂 ID", example=1),
        "name": fields.String(description="工厂名称", example="测试工厂"),
        "code": fields.String(description="工厂编码", example="TEST001"),
        "contact_person": fields.String(description="联系人", example="张三"),
        "contact_phone": fields.String(description="联系电话", example="13800138000"),
        "address": fields.String(description="地址", example="广东省深圳市南山区"),
        "status": fields.Integer(description="状态", example=1),
        "remark": fields.String(description="备注", example=None),
        "service_expire_date": fields.String(description="服务到期日期", example="2026-12-31"),
        "service_status": fields.String(description="服务状态", example="active"),
        "create_time": fields.String(description="创建时间", example="2026-04-21 01:17:24"),
        "update_time": fields.String(description="更新时间", example="2026-04-21 01:17:24"),
        "admin_username": fields.String(description="默认管理员账号", example="FAC202605280001"),
        "admin_password": fields.String(description="默认管理员密码", example="123456"),
    },
)

user_item_model = factory_ns.model(
    "FactoryUserItem",
    {
        "id": fields.Integer(description="用户 ID", example=2),
        "username": fields.String(description="用户名", example="factory_admin"),
        "nickname": fields.String(description="昵称", example="工厂管理员"),
        "phone": fields.String(description="手机号", example="18370601281"),
        "status": fields.Integer(description="状态", example=1),
        "platform_identity": fields.String(description="平台身份", example="external_user"),
        "platform_identity_label": fields.String(description="平台身份名称", example="外部人员"),
        "subject_type": fields.String(description="主体类型", example="individual_subject"),
        "subject_type_label": fields.String(description="主体类型名称", example="个人主体"),
        "relation_type": fields.String(description="关联关系类型", example="employee"),
        "relation_type_label": fields.String(description="关联关系名称", example="工厂员工"),
        "collaborator_type": fields.String(description="协作方类型", example=None),
        "collaborator_type_label": fields.String(description="协作方类型名称", example=None),
        "entry_date": fields.String(description="入厂日期", example="2026-04-21"),
        "leave_date": fields.String(description="离厂日期", example=None),
    },
)

user_list_data = factory_ns.model(
    "FactoryUserListData",
    {
        "items": fields.List(fields.Nested(user_item_model), description="工厂用户列表"),
        "total": fields.Integer(description="总条数"),
        "page": fields.Integer(description="当前页码"),
        "page_size": fields.Integer(description="每页条数"),
        "pages": fields.Integer(description="总页数"),
    },
)

factory_list_response = factory_ns.clone(
    "FactoryListResponse",
    base_response,
    {"data": fields.Nested(factory_list_data, description="工厂分页数据")},
)
factory_item_response = factory_ns.clone(
    "FactoryItemResponse",
    base_response,
    {"data": fields.Nested(factory_item_model, description="工厂详情数据")},
)
factory_create_response = factory_ns.clone(
    "FactoryCreateResponse",
    base_response,
    {"data": fields.Nested(factory_create_response_data, description="工厂创建结果数据")},
)
user_list_response = factory_ns.clone(
    "FactoryUserListResponse",
    base_response,
    {"data": fields.Nested(user_list_data, description="工厂用户分页数据")},
)
user_item_response = factory_ns.clone(
    "FactoryUserItemResponse",
    base_response,
    {"data": fields.Nested(user_item_model, description="工厂用户详情数据")},
)
factory_options_response = factory_ns.clone(
    "FactoryOptionsResponse",
    base_response,
    {"data": fields.List(fields.Nested(factory_option_model), description="工厂下拉选项列表")},
)

factory_schema = FactorySchema()
factories_schema = FactorySchema(many=True)
factory_create_schema = FactoryCreateSchema()
factory_update_schema = FactoryUpdateSchema()
factory_add_user_schema = FactoryAddUserSchema()
factory_bind_schema = FactoryBindSchema()


def get_factory_module_user_or_error():
    """获取允许访问工厂管理模块的当前用户。"""
    current_user, error_response_data = require_current_user()
    if error_response_data:
        return None, error_response_data
    has_permission, error = check_factory_module_permission(current_user)
    if not has_permission:
        return None, ApiResponse.error(error, 403)
    return current_user, None


def get_factory_or_error(factory_id):
    """根据工厂 ID 查询工厂，不存在时返回统一错误响应。"""
    factory = FactoryService.get_factory_by_id(factory_id)
    if not factory:
        return None, ApiResponse.error("工厂不存在", 404)
    return factory, None


def serialize_factory_option(factory):
    """序列化工厂下拉选项。"""
    return {"id": factory.id, "name": factory.name, "code": factory.code}


def build_factory_create_payload(factory, factory_admin):
    """构造工厂创建成功后的返回数据。"""
    result = factory_schema.dump(factory)
    result["admin_username"] = factory_admin.username
    result["admin_password"] = "123456"
    return result


def parse_factory_filter_args():
    """解析工厂筛选参数，空字符串按未传处理。"""
    name = (request.args.get("name") or "").strip()
    raw_status = request.args.get("status")

    if raw_status in (None, ""):
        status = None
    else:
        try:
            status = int(raw_status)
        except ValueError:
            return None, "status 必须为 0 或 1"
        if status not in (0, 1):
            return None, "status 必须为 0 或 1"

    return {"name": name, "status": status}, None


def parse_factory_list_args():
    """解析工厂列表查询参数；全部为空时返回全量工厂。"""
    filters, error = parse_factory_filter_args()
    if error:
        return None, error

    raw_page = request.args.get("page")
    raw_page_size = request.args.get("page_size")
    try:
        page = int(raw_page or 1)
        page_size = int(raw_page_size or 10)
    except ValueError:
        return None, "page 和 page_size 必须为整数"

    if page < 1:
        return None, "page 必须大于等于 1"
    if page_size < 1 or page_size > 100:
        return None, "page_size 必须在 1 到 100 之间"

    is_empty_query = all(
        value in (None, "")
        for value in [raw_page, raw_page_size, request.args.get("name"), request.args.get("status")]
    )
    filters.update({"page": page, "page_size": page_size, "return_all": is_empty_query})
    return filters, None


def check_factory_module_permission(current_user):
    """校验当前用户是否允许访问工厂管理模块。"""
    if not current_user:
        return False, "用户不存在"
    if not current_user.is_internal_user:
        return False, "外部用户无权访问工厂管理模块"
    return True, None


def build_factory_user_view(
    user,
    relation_type,
    relation_type_label,
    collaborator_type=None,
    collaborator_type_label=None,
    entry_date=None,
    leave_date=None,
):
    """构造工厂用户展示数据。"""
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "phone": user.phone,
        "status": user.status,
        "platform_identity": user.platform_identity,
        "platform_identity_label": user.platform_identity_label,
        "subject_type": user.get_subject_type([relation_type]),
        "subject_type_label": user.get_subject_type_label([relation_type]),
        "relation_type": relation_type,
        "relation_type_label": relation_type_label,
        "collaborator_type": collaborator_type,
        "collaborator_type_label": collaborator_type_label,
        "entry_date": entry_date.isoformat() if entry_date else None,
        "leave_date": leave_date.isoformat() if leave_date else None,
    }


@factory_ns.route("")
class FactoryList(Resource):
    @login_required
    @permission_required("system.factories.browse")
    @factory_ns.expect(factory_query_parser)
    @factory_ns.response(200, "成功", factory_list_response)
    @factory_ns.response(401, "未登录", unauthorized_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    def get(self):
        """查询工厂列表接口；当筛选参数全部为空时返回所有工厂。"""
        args, parse_error = parse_factory_list_args()
        if parse_error:
            return ApiResponse.error(parse_error, 400)

        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        result = FactoryService.get_factory_list(args)
        return ApiResponse.success_page_result(result, factories_schema.dump(result["items"]))

    @login_required
    @permission_required("system.factories.create")
    @factory_ns.expect(factory_create_model)
    @factory_ns.response(201, "创建成功", factory_create_response)
    @factory_ns.response(400, "参数错误", error_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(409, "工厂编码生成冲突", error_response)
    def post(self):
        """创建工厂接口，工厂编码由系统自动生成，并同时创建默认工厂管理员账号。"""
        current_user, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        try:
            data = factory_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        factory, factory_admin, create_error = FactoryService.create_factory(data, current_user.id)
        if create_error:
            return ApiResponse.error(create_error, 409)

        return ApiResponse.success(build_factory_create_payload(factory, factory_admin), "创建成功", 201)


@factory_ns.route("/options")
class FactoryOptions(Resource):
    @login_required
    @permission_required("system.factories.browse")
    @factory_ns.expect(factory_filter_parser)
    @factory_ns.response(200, "成功", factory_options_response)
    @factory_ns.response(401, "未登录", unauthorized_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    def get(self):
        """查询工厂下拉选项接口，仅返回工厂 ID、名称和编码。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        filters, parse_error = parse_factory_filter_args()
        if parse_error:
            return ApiResponse.error(parse_error, 400)

        factories = FactoryService.get_factory_options(name=filters["name"], status=filters["status"])
        return ApiResponse.success_list([serialize_factory_option(factory) for factory in factories])


@factory_ns.route("/<int:factory_id>")
class FactoryDetail(Resource):
    @login_required
    @permission_required("system.factories.browse")
    @factory_ns.response(200, "成功", factory_item_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    def get(self, factory_id):
        """查询单个工厂详情接口。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        factory, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data
        return ApiResponse.success(factory_schema.dump(factory))

    @login_required
    @permission_required("system.factories.update")
    @factory_ns.expect(factory_update_model)
    @factory_ns.response(200, "更新成功", factory_item_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    def patch(self, factory_id):
        """更新工厂基础信息和服务到期信息接口。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        factory, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        try:
            data = factory_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        factory = FactoryService.update_factory(factory, data)
        return ApiResponse.success(factory_schema.dump(factory), "更新成功")

    @login_required
    @permission_required("system.factories.delete")
    @factory_ns.response(200, "删除成功", base_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    @factory_ns.response(409, "存在关联用户无法删除", error_response)
    def delete(self, factory_id):
        """删除工厂接口；删除前会校验是否仍存在关联用户。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        factory, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        success, delete_error = FactoryService.delete_factory(factory)
        if not success:
            return ApiResponse.error(delete_error, 409)
        return ApiResponse.success(message="删除成功")


@factory_ns.route("/<int:factory_id>/users")
class FactoryUsers(Resource):
    @login_required
    @permission_required("system.factories.browse")
    @factory_ns.expect(factory_user_query_parser)
    @factory_ns.response(200, "成功", user_list_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    def get(self, factory_id):
        """查询工厂用户列表接口，支持关系类型和协作方类型过滤。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        _, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        args = factory_user_query_parser.parse_args()
        result = FactoryService.get_factory_users(factory_id, args)
        return ApiResponse.success_page_result(result, result["items"])

    @login_required
    @permission_required("system.factories.update")
    @factory_ns.expect(add_user_model)
    @factory_ns.response(200, "添加成功", user_item_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "用户不存在", error_response)
    @factory_ns.response(409, "用户已关联", error_response)
    def post(self, factory_id):
        """为工厂新增用户关系接口，支持 owner、employee、customer、collaborator。"""
        current_user, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        _, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        try:
            data = factory_add_user_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        if data["relation_type"] == "owner":
            user_factory, add_error = FactoryService.update_factory_owner(factory_id, data["user_id"])
        else:
            user_factory, add_error = FactoryService.add_user_to_factory(
                factory_id,
                data["user_id"],
                data["relation_type"],
                collaborator_type=data.get("collaborator_type"),
            )

        if add_error:
            status_code = 409 if "已关联" in add_error or "已经是" in add_error else 404
            return ApiResponse.error(add_error, status_code)

        user = user_factory.user
        return ApiResponse.success(
            build_factory_user_view(
                user=user,
                relation_type=user_factory.relation_type,
                relation_type_label=user_factory.relation_type_label,
                collaborator_type=user_factory.collaborator_type,
                collaborator_type_label=user_factory.collaborator_type_label,
                entry_date=user_factory.entry_date or datetime.now().date(),
                leave_date=user_factory.leave_date,
            ),
            "添加成功",
        )


@factory_ns.route("/<int:factory_id>/users/<int:user_id>")
class FactoryUserDetail(Resource):
    @login_required
    @permission_required("system.factories.delete")
    @factory_ns.response(200, "移除成功", base_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "关联不存在", error_response)
    def delete(self, factory_id, user_id):
        """移除工厂用户关系接口。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        success, delete_error = FactoryService.remove_user_from_factory(factory_id, user_id)
        if not success:
            return ApiResponse.error(delete_error, 404)
        return ApiResponse.success(message="移除成功")


@factory_ns.route("/<int:factory_id>/owner")
class FactoryOwner(Resource):
    @login_required
    @permission_required("system.factories.browse")
    @factory_ns.response(200, "成功", user_item_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    def get(self, factory_id):
        """查询工厂当前管理员账号接口。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        _, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        owner = FactoryService.get_factory_owner(factory_id)
        if not owner:
            return ApiResponse.error("工厂管理员账号不存在", 404)

        return ApiResponse.success(
            build_factory_user_view(
                user=owner,
                relation_type="owner",
                relation_type_label="工厂管理员",
            )
        )


@factory_ns.route("/<int:factory_id>/owner/reset-password")
class FactoryOwnerResetPassword(Resource):
    @login_required
    @permission_required("system.factories.update")
    @factory_ns.response(200, "重置成功", base_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    def post(self, factory_id):
        """重置工厂管理员密码接口。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        _, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        success, reset_error = FactoryService.reset_owner_password(factory_id)
        if not success:
            return ApiResponse.error(reset_error, 404)
        return ApiResponse.success(message="密码已重置为 123456")


@factory_ns.route("/<int:factory_id>/qrcode")
class FactoryQRCode(Resource):
    @login_required
    @permission_required("system.factories.update")
    @factory_ns.response(200, "成功", qrcode_response)
    @factory_ns.response(403, "无权限", forbidden_response)
    @factory_ns.response(404, "工厂不存在", error_response)
    def post(self, factory_id):
        """生成工厂绑定二维码接口。"""
        _, error_response_data = get_factory_module_user_or_error()
        if error_response_data:
            return error_response_data

        factory, error_response_data = get_factory_or_error(factory_id)
        if error_response_data:
            return error_response_data

        result = FactoryService.generate_qrcode(factory)
        return ApiResponse.success(result, "二维码生成成功")


@factory_ns.route("/bind")
class BindFactory(Resource):
    @factory_ns.expect(bind_factory_model)
    @factory_ns.response(200, "绑定成功", bind_response)
    @factory_ns.response(400, "参数错误", error_response)
    @factory_ns.response(401, "未登录", unauthorized_response)
    @factory_ns.response(404, "二维码无效", error_response)
    def post(self):
        """扫码绑定工厂接口，默认建立 employee 关系。"""
        try:
            data = factory_bind_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)

        current_user, error_response_data = require_current_user(message="请先登录", code=401)
        if error_response_data:
            return error_response_data

        result, bind_error = FactoryService.bind_user_to_factory(current_user.id, data["key"])
        if bind_error:
            return ApiResponse.error(bind_error, 404)
        return ApiResponse.success(result, "绑定成功")
