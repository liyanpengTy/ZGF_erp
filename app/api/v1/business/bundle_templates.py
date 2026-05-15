"""菲模板与菲规则接口。"""

from flask import request
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.api.common.auth import get_current_claims, get_current_factory_id, get_current_user
from app.api.common.models import get_common_models
from app.schemas.business.bundle import (
    BundleTemplateCreateSchema,
    BundleTemplateSchema,
    BundleTemplateUpdateSchema,
    FactoryBundleRuleSchema,
    FactoryBundleRuleUpdateSchema,
)
from app.services import BundleTemplateService, FactoryService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

bundle_template_ns = Namespace('菲模板管理-bundle-templates', description='菲模板与菲规则管理')

common = get_common_models(bundle_template_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']

bundle_template_item_model = bundle_template_ns.model('BundleTemplateItemView', {
    'id': fields.Integer(description='模板字段项ID'),
    'field_code': fields.String(description='字段编码', example='style_no'),
    'field_label': fields.String(description='字段显示名称', example='款号'),
    'sort_order': fields.Integer(description='排序值', example=1),
    'is_visible': fields.Integer(description='是否显示：1-显示，0-隐藏', example=1),
    'is_bold': fields.Integer(description='是否加粗：1-是，0-否', example=1),
    'is_new_line': fields.Integer(description='是否换行：1-换行，0-同行', example=1),
})

bundle_template_item_input_model = bundle_template_ns.model('BundleTemplateItemInput', {
    'field_code': fields.String(required=True, description='字段编码', example='style_no'),
    'field_label': fields.String(required=True, description='字段显示名称', example='款号'),
    'sort_order': fields.Integer(description='排序值', example=1, default=1),
    'is_visible': fields.Integer(description='是否显示：1-显示，0-隐藏', example=1, default=1),
    'is_bold': fields.Integer(description='是否加粗：1-是，0-否', example=1, default=0),
    'is_new_line': fields.Integer(description='是否换行：1-换行，0-同行', example=1, default=1),
})

bundle_template_model = bundle_template_ns.model('BundleTemplateView', {
    'id': fields.Integer(description='模板ID'),
    'factory_id': fields.Integer(description='工厂ID，系统模板为空', allow_null=True),
    'name': fields.String(description='模板名称', example='系统默认菲模板'),
    'template_scope': fields.String(description='模板范围：system/factory', example='system'),
    'scope_label': fields.String(description='模板范围名称', example='系统模板'),
    'version': fields.Integer(description='模板版本号', example=1),
    'is_default': fields.Integer(description='是否默认模板：1-是，0-否', example=1),
    'status': fields.Integer(description='状态：1-启用，0-停用', example=1),
    'remark': fields.String(description='备注', allow_null=True),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
    'items': fields.List(fields.Nested(bundle_template_item_model), description='模板字段项列表'),
})

bundle_template_create_model = bundle_template_ns.model('BundleTemplateCreate', {
    'name': fields.String(required=True, description='模板名称', example='工厂默认菲模板'),
    'is_default': fields.Integer(description='是否设为默认模板：1-是，0-否', example=1, default=0),
    'remark': fields.String(description='备注', example='适用于裁床打印'),
    'items': fields.List(fields.Nested(bundle_template_item_input_model), required=True, description='模板字段项列表'),
})

bundle_template_update_model = bundle_template_ns.model('BundleTemplateUpdate', {
    'name': fields.String(description='模板名称', example='工厂新版菲模板'),
    'is_default': fields.Integer(description='是否设为默认模板：1-是，0-否', example=0),
    'status': fields.Integer(description='状态：1-启用，0-停用', example=1),
    'remark': fields.String(description='备注', example='移除尺码字段'),
    'items': fields.List(fields.Nested(bundle_template_item_input_model), description='完整模板字段项列表'),
})

bundle_template_list_response = bundle_template_ns.clone('BundleTemplateListResponse', base_response, {
    'data': fields.List(fields.Nested(bundle_template_model), description='模板列表'),
})

bundle_template_item_response = bundle_template_ns.clone('BundleTemplateItemResponse', base_response, {
    'data': fields.Nested(bundle_template_model, description='模板详情'),
})

bundle_field_option_model = bundle_template_ns.model('BundleFieldOption', {
    'field_code': fields.String(description='字段编码', example='style_no'),
    'field_label': fields.String(description='默认字段名称', example='款号'),
})

bundle_field_option_response = bundle_template_ns.clone('BundleFieldOptionResponse', base_response, {
    'data': fields.List(fields.Nested(bundle_field_option_model), description='系统可选字段列表'),
})

bundle_rule_model = bundle_template_ns.model('FactoryBundleRuleView', {
    'id': fields.Integer(description='规则ID'),
    'factory_id': fields.Integer(description='工厂ID'),
    'reset_cycle': fields.String(description='床次重置周期：yearly/monthly', example='yearly'),
    'reset_cycle_label': fields.String(description='床次重置周期名称', example='按年重置'),
    'default_template_id': fields.Integer(description='默认模板ID', allow_null=True),
    'bundle_code_prefix': fields.String(description='菲号前缀', example='FEI'),
    'status': fields.Integer(description='状态：1-启用，0-停用', example=1),
    'remark': fields.String(description='备注', allow_null=True),
    'create_time': fields.String(description='创建时间'),
    'update_time': fields.String(description='更新时间'),
})

bundle_rule_update_model = bundle_template_ns.model('FactoryBundleRuleUpdate', {
    'reset_cycle': fields.String(description='床次重置周期：yearly/monthly', example='monthly'),
    'default_template_id': fields.Integer(description='默认模板ID', example=2),
    'bundle_code_prefix': fields.String(description='菲号前缀', example='CUT'),
    'status': fields.Integer(description='状态：1-启用，0-停用', example=1),
    'remark': fields.String(description='备注', example='每月重置床次'),
})

bundle_rule_response = bundle_template_ns.clone('FactoryBundleRuleResponse', base_response, {
    'data': fields.Nested(bundle_rule_model, description='工厂菲规则'),
})

bundle_template_schema = BundleTemplateSchema()
bundle_templates_schema = BundleTemplateSchema(many=True)
bundle_template_create_schema = BundleTemplateCreateSchema()
bundle_template_update_schema = BundleTemplateUpdateSchema()
bundle_rule_schema = FactoryBundleRuleSchema()
bundle_rule_update_schema = FactoryBundleRuleUpdateSchema()


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


def check_manage_permission(current_user):
    """校验当前用户是否可以维护工厂菲模板与菲规则。"""
    claims = get_current_claims()
    relation_type = claims.get('relation_type')
    if current_user.is_internal_user:
        return True
    return relation_type == 'owner'


@bundle_template_ns.route('/field-options')
class BundleFieldOptions(Resource):
    @login_required
    @bundle_template_ns.response(200, '成功', bundle_field_option_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询系统支持的菲模板字段池。"""
        current_user, _, error_response_obj = resolve_factory_context(require_write=False)
        if error_response_obj:
            return error_response_obj
        options = [
            {'field_code': field_code, 'field_label': config['label']}
            for field_code, config in BundleTemplateService.FIELD_DEFINITIONS.items()
        ]
        return ApiResponse.success(options)


@bundle_template_ns.route('')
class BundleTemplateList(Resource):
    @login_required
    @bundle_template_ns.response(200, '成功', bundle_template_list_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询当前工厂可用的系统模板与工厂模板列表。"""
        _, current_factory_id, error_response_obj = resolve_factory_context(require_write=False)
        if error_response_obj:
            return error_response_obj
        templates = BundleTemplateService.get_template_list(current_factory_id)
        return ApiResponse.success(bundle_templates_schema.dump(templates))

    @login_required
    @bundle_template_ns.expect(bundle_template_create_model)
    @bundle_template_ns.response(201, '创建成功', bundle_template_item_response)
    @bundle_template_ns.response(400, '参数错误', error_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    @bundle_template_ns.response(403, '无权限', forbidden_response)
    def post(self):
        """创建当前工厂的自定义菲模板。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_manage_permission(current_user):
            return ApiResponse.error('只有工厂管理员或平台内部人员可以维护菲模板', 403)
        try:
            data = bundle_template_create_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        template, error = BundleTemplateService.create_factory_template(current_factory_id, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_template_schema.dump(template), '创建成功', 201)


@bundle_template_ns.route('/<int:template_id>')
class BundleTemplateDetail(Resource):
    @login_required
    @bundle_template_ns.response(200, '成功', bundle_template_item_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    @bundle_template_ns.response(404, '模板不存在', error_response)
    def get(self, template_id):
        """查询指定菲模板详情。"""
        _, current_factory_id, error_response_obj = resolve_factory_context(require_write=False)
        if error_response_obj:
            return error_response_obj
        template = BundleTemplateService.get_template_by_id(template_id)
        if not template or (template.template_scope == 'factory' and template.factory_id != current_factory_id):
            return ApiResponse.error('模板不存在', 404)
        return ApiResponse.success(bundle_template_schema.dump(template))

    @login_required
    @bundle_template_ns.expect(bundle_template_update_model)
    @bundle_template_ns.response(200, '更新成功', bundle_template_item_response)
    @bundle_template_ns.response(400, '参数错误', error_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    @bundle_template_ns.response(403, '无权限', forbidden_response)
    @bundle_template_ns.response(404, '模板不存在', error_response)
    def patch(self, template_id):
        """更新当前工厂的自定义菲模板。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_manage_permission(current_user):
            return ApiResponse.error('只有工厂管理员或平台内部人员可以维护菲模板', 403)
        template = BundleTemplateService.get_template_by_id(template_id)
        if not template or template.template_scope != 'factory' or template.factory_id != current_factory_id:
            return ApiResponse.error('模板不存在', 404)
        try:
            data = bundle_template_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        template, error = BundleTemplateService.update_factory_template(template, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_template_schema.dump(template), '更新成功')

    @login_required
    @bundle_template_ns.response(200, '删除成功', base_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    @bundle_template_ns.response(403, '无权限', forbidden_response)
    @bundle_template_ns.response(404, '模板不存在', error_response)
    def delete(self, template_id):
        """删除当前工厂的自定义菲模板。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_manage_permission(current_user):
            return ApiResponse.error('只有工厂管理员或平台内部人员可以维护菲模板', 403)
        template = BundleTemplateService.get_template_by_id(template_id)
        if not template or template.template_scope != 'factory' or template.factory_id != current_factory_id:
            return ApiResponse.error('模板不存在', 404)
        success, error = BundleTemplateService.delete_factory_template(template)
        if not success:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(message='删除成功')


@bundle_template_ns.route('/rule')
class FactoryBundleRuleDetail(Resource):
    @login_required
    @bundle_template_ns.response(200, '成功', bundle_rule_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """查询当前工厂的菲规则配置。"""
        _, current_factory_id, error_response_obj = resolve_factory_context(require_write=False)
        if error_response_obj:
            return error_response_obj
        rule = BundleTemplateService.ensure_factory_rule(current_factory_id)
        return ApiResponse.success(bundle_rule_schema.dump(rule))

    @login_required
    @bundle_template_ns.expect(bundle_rule_update_model)
    @bundle_template_ns.response(200, '更新成功', bundle_rule_response)
    @bundle_template_ns.response(400, '参数错误', error_response)
    @bundle_template_ns.response(401, '未登录', unauthorized_response)
    @bundle_template_ns.response(403, '无权限', forbidden_response)
    def patch(self):
        """更新当前工厂的菲规则配置，如床次重置周期和默认模板。"""
        current_user, current_factory_id, error_response_obj = resolve_factory_context(require_write=True)
        if error_response_obj:
            return error_response_obj
        if not check_manage_permission(current_user):
            return ApiResponse.error('只有工厂管理员或平台内部人员可以维护菲规则', 403)
        try:
            data = bundle_rule_update_schema.load(request.get_json() or {})
        except ValidationError as exc:
            return ApiResponse.error(str(exc.messages), 400)
        rule, error = BundleTemplateService.update_factory_rule(current_factory_id, data)
        if error:
            return ApiResponse.error(error, 400)
        return ApiResponse.success(bundle_rule_schema.dump(rule), '更新成功')
