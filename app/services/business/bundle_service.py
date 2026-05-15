"""菲模板、菲规则与菲查询服务。"""

from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.auth.user import User
from app.models.business.bundle import (
    BundleTemplate,
    BundleTemplateItem,
    FactoryBundleRule,
    FactoryCutBatchCounter,
    ProductionBundle,
    ProductionBundleFlow,
)
from app.models.business.order import Order
from app.models.business.process import Process
from app.models.business.style import Style
from app.models.system.user_factory import UserFactory
from app.services.base.base_service import BaseService


class BundleTemplateService(BaseService):
    """菲模板与菲规则服务。"""

    FIELD_DEFINITIONS = {
        'style_no': {'label': '款号'},
        'cut_batch_no': {'label': '床次'},
        'bed_no': {'label': '床号'},
        'bundle_quantity': {'label': '数量'},
        'color_name': {'label': '颜色'},
        'size_name': {'label': '尺码'},
        'priority_label': {'label': '优先级'},
        'created_time': {'label': '日期'},
    }

    DEFAULT_TEMPLATE_NAME = '系统默认菲模板'
    DEFAULT_TEMPLATE_ITEMS = [
        {'field_code': 'style_no', 'field_label': '款号', 'sort_order': 1, 'is_visible': 1, 'is_bold': 1, 'is_new_line': 1},
        {'field_code': 'cut_batch_no', 'field_label': '床次', 'sort_order': 2, 'is_visible': 1, 'is_bold': 0, 'is_new_line': 1},
        {'field_code': 'bed_no', 'field_label': '床号', 'sort_order': 3, 'is_visible': 1, 'is_bold': 0, 'is_new_line': 1},
        {'field_code': 'bundle_quantity', 'field_label': '数量', 'sort_order': 4, 'is_visible': 1, 'is_bold': 0, 'is_new_line': 1},
        {'field_code': 'color_name', 'field_label': '颜色', 'sort_order': 5, 'is_visible': 1, 'is_bold': 0, 'is_new_line': 1},
        {'field_code': 'priority_label', 'field_label': '优先级', 'sort_order': 6, 'is_visible': 1, 'is_bold': 0, 'is_new_line': 1},
        {'field_code': 'created_time', 'field_label': '日期', 'sort_order': 7, 'is_visible': 1, 'is_bold': 0, 'is_new_line': 1},
    ]

    @staticmethod
    def get_template_query_options():
        """统一封装模板查询时需要预加载的关联项。"""
        return [selectinload(BundleTemplate.items)]

    @staticmethod
    def normalize_template_items(items):
        """标准化模板字段项，并校验字段编码是否在系统字段池内。"""
        normalized = []
        seen_codes = set()
        for index, item in enumerate(items or [], start=1):
            field_code = item['field_code']
            if field_code not in BundleTemplateService.FIELD_DEFINITIONS:
                return None, f'字段编码 {field_code} 不在系统支持范围内'
            if field_code in seen_codes:
                return None, f'字段编码 {field_code} 重复'
            seen_codes.add(field_code)
            normalized.append({
                'field_code': field_code,
                'field_label': item.get('field_label') or BundleTemplateService.FIELD_DEFINITIONS[field_code]['label'],
                'sort_order': item.get('sort_order', index),
                'is_visible': item.get('is_visible', 1),
                'is_bold': item.get('is_bold', 0),
                'is_new_line': item.get('is_new_line', 1),
            })
        return normalized, None

    @staticmethod
    def get_template_by_id(template_id):
        """按主键查询菲模板。"""
        return BundleTemplate.query.options(*BundleTemplateService.get_template_query_options()).filter_by(
            id=template_id,
            is_deleted=0,
        ).first()

    @staticmethod
    def get_system_default_template():
        """查询系统默认模板，不存在时自动初始化一份。"""
        template = BundleTemplate.query.options(*BundleTemplateService.get_template_query_options()).filter_by(
            template_scope='system',
            is_default=1,
            is_deleted=0,
        ).order_by(BundleTemplate.id.asc()).first()
        if template:
            return template
        return BundleTemplateService.ensure_system_default_template()

    @staticmethod
    def ensure_system_default_template():
        """确保系统默认菲模板存在，并同步为标准字段项。"""
        template = BundleTemplate.query.options(*BundleTemplateService.get_template_query_options()).filter_by(
            template_scope='system',
            name=BundleTemplateService.DEFAULT_TEMPLATE_NAME,
            is_deleted=0,
        ).order_by(BundleTemplate.id.asc()).first()

        if not template:
            template = BundleTemplate(
                factory_id=None,
                name=BundleTemplateService.DEFAULT_TEMPLATE_NAME,
                template_scope='system',
                version=1,
                is_default=1,
                status=1,
                remark='系统初始化默认菲模板',
            )
            db.session.add(template)
            db.session.flush()
        else:
            template.is_default = 1
            template.status = 1

        template.items[:] = []
        for item in BundleTemplateService.DEFAULT_TEMPLATE_ITEMS:
            template.items.append(BundleTemplateItem(**item))
        db.session.add(template)
        db.session.commit()
        return template

    @staticmethod
    def get_factory_rule(factory_id):
        """查询工厂当前生效的菲规则。"""
        return FactoryBundleRule.query.options(joinedload(FactoryBundleRule.default_template)).filter_by(
            factory_id=factory_id,
            is_deleted=0,
        ).first()

    @staticmethod
    def ensure_factory_rule(factory_id):
        """确保工厂至少有一条默认菲规则。"""
        rule = BundleTemplateService.get_factory_rule(factory_id)
        if rule:
            return rule
        system_template = BundleTemplateService.get_system_default_template()
        rule = FactoryBundleRule(
            factory_id=factory_id,
            reset_cycle='yearly',
            default_template_id=system_template.id,
            bundle_code_prefix='FEI',
            status=1,
            remark='系统初始化默认菲规则',
        )
        db.session.add(rule)
        db.session.commit()
        return rule

    @staticmethod
    def get_template_list(factory_id):
        """查询当前工厂可用的系统模板与工厂模板。"""
        return BundleTemplate.query.options(*BundleTemplateService.get_template_query_options()).filter(
            BundleTemplate.is_deleted == 0,
            BundleTemplate.status == 1,
            or_(
                BundleTemplate.template_scope == 'system',
                and_(BundleTemplate.template_scope == 'factory', BundleTemplate.factory_id == factory_id),
            ),
        ).order_by(BundleTemplate.template_scope.asc(), BundleTemplate.id.asc()).all()

    @staticmethod
    def create_factory_template(factory_id, data):
        """创建工厂自定义菲模板。"""
        existing = BundleTemplate.query.filter_by(
            factory_id=factory_id,
            template_scope='factory',
            name=data['name'],
            is_deleted=0,
        ).first()
        if existing:
            return None, '模板名称已存在'

        items, error = BundleTemplateService.normalize_template_items(data['items'])
        if error:
            return None, error

        template = BundleTemplate(
            factory_id=factory_id,
            name=data['name'],
            template_scope='factory',
            version=1,
            is_default=data.get('is_default', 0),
            status=1,
            remark=data.get('remark', ''),
        )
        if template.is_default:
            BundleTemplateService.clear_factory_default_templates(factory_id)

        db.session.add(template)
        db.session.flush()
        for item in items:
            template.items.append(BundleTemplateItem(**item))
        db.session.add(template)
        db.session.commit()

        if template.is_default:
            rule = BundleTemplateService.ensure_factory_rule(factory_id)
            rule.default_template_id = template.id
            db.session.add(rule)
            db.session.commit()
        return BundleTemplateService.get_template_by_id(template.id), None

    @staticmethod
    def clear_factory_default_templates(factory_id, exclude_template_id=None):
        """清理当前工厂旧的默认模板标记。"""
        query = BundleTemplate.query.filter_by(
            factory_id=factory_id,
            template_scope='factory',
            is_default=1,
            is_deleted=0,
        )
        if exclude_template_id:
            query = query.filter(BundleTemplate.id != exclude_template_id)
        for template in query.all():
            template.is_default = 0
            db.session.add(template)

    @staticmethod
    def update_factory_template(template, data):
        """更新工厂自定义菲模板，并自动递增模板版本。"""
        if template.template_scope != 'factory':
            return None, '系统模板不允许直接修改'

        if 'name' in data and data['name'] != template.name:
            duplicate = BundleTemplate.query.filter_by(
                factory_id=template.factory_id,
                template_scope='factory',
                name=data['name'],
                is_deleted=0,
            ).filter(BundleTemplate.id != template.id).first()
            if duplicate:
                return None, '模板名称已存在'
            template.name = data['name']

        if 'remark' in data:
            template.remark = data['remark']
        if 'status' in data:
            template.status = data['status']

        if 'items' in data:
            items, error = BundleTemplateService.normalize_template_items(data['items'])
            if error:
                return None, error
            template.items[:] = []
            for item in items:
                template.items.append(BundleTemplateItem(**item))

        if 'is_default' in data:
            template.is_default = data['is_default']
            if template.is_default:
                BundleTemplateService.clear_factory_default_templates(template.factory_id, exclude_template_id=template.id)
                rule = BundleTemplateService.ensure_factory_rule(template.factory_id)
                rule.default_template_id = template.id
                db.session.add(rule)

        template.version += 1
        db.session.add(template)
        db.session.commit()
        return BundleTemplateService.get_template_by_id(template.id), None

    @staticmethod
    def delete_factory_template(template):
        """软删除工厂自定义菲模板；若仍为默认模板则阻止删除。"""
        if template.template_scope != 'factory':
            return False, '系统模板不允许删除'
        if template.is_default:
            return False, '默认模板不允许删除，请先切换默认模板'
        if template.bundles:
            template.status = 0
            template.is_deleted = 1
            db.session.add(template)
            db.session.commit()
            return True, None
        template.is_deleted = 1
        db.session.add(template)
        db.session.commit()
        return True, None

    @staticmethod
    def update_factory_rule(factory_id, data):
        """更新工厂菲规则，并校验默认模板必须在当前工厂可见。"""
        rule = BundleTemplateService.ensure_factory_rule(factory_id)

        if 'default_template_id' in data and data['default_template_id'] is not None:
            template = BundleTemplateService.get_template_by_id(data['default_template_id'])
            if not template:
                return None, '默认模板不存在'
            if template.template_scope == 'factory' and template.factory_id != factory_id:
                return None, '默认模板不属于当前工厂'
            if template.status != 1:
                return None, '默认模板已停用'
            rule.default_template_id = template.id

        if 'reset_cycle' in data:
            rule.reset_cycle = data['reset_cycle']
        if 'bundle_code_prefix' in data:
            rule.bundle_code_prefix = data['bundle_code_prefix']
        if 'status' in data:
            rule.status = data['status']
        if 'remark' in data:
            rule.remark = data['remark']

        db.session.add(rule)
        db.session.commit()
        return BundleTemplateService.get_factory_rule(factory_id), None

    @staticmethod
    def resolve_template(factory_id, template_id=None):
        """按显式模板、工厂默认模板、系统默认模板的顺序解析实际使用模板。"""
        if template_id:
            template = BundleTemplateService.get_template_by_id(template_id)
            if not template:
                return None, '模板不存在'
            if template.template_scope == 'factory' and template.factory_id != factory_id:
                return None, '模板不属于当前工厂'
            if template.status != 1:
                return None, '模板已停用'
            return template, None

        rule = BundleTemplateService.ensure_factory_rule(factory_id)
        if rule.default_template_id:
            template = BundleTemplateService.get_template_by_id(rule.default_template_id)
            if template and template.status == 1:
                return template, None
        return BundleTemplateService.get_system_default_template(), None

    @staticmethod
    def next_cut_batch_no(factory_id, current_date=None):
        """按工厂菲规则生成下一个床次号。"""
        current_date = current_date or datetime.now()
        rule = BundleTemplateService.ensure_factory_rule(factory_id)
        if rule.reset_cycle == 'monthly':
            period_key = current_date.strftime('%Y-%m')
        else:
            period_key = current_date.strftime('%Y')

        counter = FactoryCutBatchCounter.query.filter_by(
            factory_id=factory_id,
            reset_cycle=rule.reset_cycle,
            period_key=period_key,
            is_deleted=0,
        ).first()
        if not counter:
            counter = FactoryCutBatchCounter(
                factory_id=factory_id,
                reset_cycle=rule.reset_cycle,
                period_key=period_key,
                current_no=1,
            )
            db.session.add(counter)
            db.session.flush()
            return 1

        counter.current_no += 1
        db.session.add(counter)
        db.session.flush()
        return counter.current_no


class BundleService(BaseService):
    """菲查询、模板渲染与打印预览服务。"""

    ISSUE_ACTION_TYPES = {'issue', 'rework_issue'}
    RETURN_ACTION_TYPES = {'return', 'rework_return'}

    @staticmethod
    def get_bundle_query_options():
        """统一封装菲查询时需要预加载的关联项。"""
        return [
            joinedload(ProductionBundle.style),
            joinedload(ProductionBundle.color),
            joinedload(ProductionBundle.size),
            joinedload(ProductionBundle.current_holder),
            joinedload(ProductionBundle.current_process),
            joinedload(ProductionBundle.template).selectinload(BundleTemplate.items),
            selectinload(ProductionBundle.flows).joinedload(ProductionBundleFlow.user),
            selectinload(ProductionBundle.flows).joinedload(ProductionBundleFlow.from_user),
            selectinload(ProductionBundle.flows).joinedload(ProductionBundleFlow.to_user),
            selectinload(ProductionBundle.flows).joinedload(ProductionBundleFlow.process),
        ]

    @staticmethod
    def get_bundle_by_id(bundle_id):
        """根据 ID 查询菲详情。"""
        return ProductionBundle.query.options(*BundleService.get_bundle_query_options()).filter_by(
            id=bundle_id,
            is_deleted=0,
        ).first()

    @staticmethod
    def get_bundle_list(factory_id, filters):
        """按订单、款号、床次、状态等维度分页查询菲。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        order_no = filters.get('order_no', '')
        style_no = filters.get('style_no', '')
        cut_batch_no = filters.get('cut_batch_no')
        status = filters.get('status')
        priority = filters.get('priority')

        query = ProductionBundle.query.options(*BundleService.get_bundle_query_options()).filter_by(
            factory_id=factory_id,
            is_deleted=0,
        )
        if order_no:
            query = query.join(ProductionBundle.order).filter(Order.order_no.like(f'%{order_no}%'))
        if style_no:
            query = query.join(ProductionBundle.style).filter(Style.style_no.like(f'%{style_no}%'))
        if cut_batch_no is not None:
            query = query.filter_by(cut_batch_no=cut_batch_no)
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)

        pagination = query.order_by(ProductionBundle.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def build_template_context(bundle):
        """构建模板渲染上下文。"""
        return {
            'style_no': bundle.style.style_no if bundle.style else '',
            'cut_batch_no': str(bundle.cut_batch_no or ''),
            'bed_no': str(bundle.bed_no or ''),
            'bundle_quantity': str(bundle.bundle_quantity or ''),
            'color_name': bundle.color.name if bundle.color else '',
            'size_name': bundle.size.name if bundle.size else '',
            'priority_label': bundle.priority_label,
            'created_time': bundle.create_time.strftime('%Y-%m-%d %H:%M:%S') if bundle.create_time else '',
        }

    @staticmethod
    def render_bundle_content(bundle, template):
        """按模板字段顺序渲染菲打印内容快照。"""
        context = BundleService.build_template_context(bundle)
        lines = []
        for item in sorted(template.items, key=lambda current: (current.sort_order, current.id or 0)):
            if item.is_visible != 1:
                continue
            value = context.get(item.field_code, '')
            lines.append(f'{item.field_label}：{value}')
        return '\n'.join(lines)

    @staticmethod
    def assign_bundle_no(bundle, rule):
        """为新生成的菲分配唯一菲号。"""
        prefix = (rule.bundle_code_prefix or 'FEI').upper()
        bundle.bundle_no = f'{prefix}-{bundle.factory_id}-{bundle.cut_batch_no}-{bundle.bed_no}-{bundle.id}'
        db.session.add(bundle)

    @staticmethod
    def append_flow(bundle, action_type, quantity, user_id=None, process_id=None, from_user_id=None, to_user_id=None, remark=''):
        """为菲补充一条流转日志。"""
        db.session.add(ProductionBundleFlow(
            bundle_id=bundle.id,
            factory_id=bundle.factory_id,
            process_id=process_id,
            user_id=user_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            action_type=action_type,
            quantity=quantity,
            action_time=datetime.now(),
            remark=remark,
        ))

    @staticmethod
    def calculate_flow_metrics(bundle):
        """汇总菲的累计领出、累计交回和当前在手数量。"""
        issued_quantity = 0
        returned_quantity = 0
        for flow in bundle.flows:
            if flow.is_deleted != 0:
                continue
            if flow.action_type in BundleService.ISSUE_ACTION_TYPES:
                issued_quantity += flow.quantity or 0
            if flow.action_type in BundleService.RETURN_ACTION_TYPES:
                returned_quantity += flow.quantity or 0
        in_hand_quantity = max(issued_quantity - returned_quantity, 0)
        return {
            'issued_quantity': issued_quantity,
            'returned_quantity': returned_quantity,
            'in_hand_quantity': in_hand_quantity,
        }

    @staticmethod
    def get_bundle_process(process_id):
        """查询有效工序。"""
        return Process.query.filter_by(id=process_id, is_deleted=0, status=1).first()

    @staticmethod
    def get_factory_active_user(factory_id, user_id):
        """查询当前工厂下具备有效关系的用户。"""
        return User.query.join(UserFactory, UserFactory.user_id == User.id).filter(
            User.id == user_id,
            User.is_deleted == 0,
            User.status == 1,
            UserFactory.factory_id == factory_id,
            UserFactory.status == 1,
            UserFactory.is_deleted == 0,
            UserFactory.relation_type.in_(['owner', 'employee', 'collaborator']),
        ).first()

    @staticmethod
    def issue_bundle(bundle, operator_user, process_id, holder_user_id=None, remark=''):
        """整菲领货：把当前菲发给某个工序和持有人。"""
        metrics = BundleService.calculate_flow_metrics(bundle)
        if bundle.status in {'cancelled', 'completed'}:
            return None, '当前菲已作废或已完工，不能领货'
        if metrics['in_hand_quantity'] > 0 or bundle.current_holder_user_id:
            return None, '当前菲仍有在手数量，不能重复领货'

        process = BundleService.get_bundle_process(process_id)
        if not process:
            return None, '工序不存在或未启用'

        holder_user_id = holder_user_id or operator_user.id
        holder_user = BundleService.get_factory_active_user(bundle.factory_id, holder_user_id)
        if not holder_user:
            return None, '领货人不存在或不属于当前工厂有效用户'

        quantity = bundle.bundle_quantity
        bundle.current_holder_user_id = holder_user.id
        bundle.current_process_id = process.id
        bundle.status = 'issued'
        db.session.add(bundle)
        BundleService.append_flow(
            bundle,
            action_type='issue',
            quantity=quantity,
            user_id=operator_user.id,
            process_id=process.id,
            from_user_id=operator_user.id if operator_user.id != holder_user.id else None,
            to_user_id=holder_user.id,
            remark=remark or '整菲领货',
        )
        db.session.commit()
        return BundleService.get_bundle_by_id(bundle.id), None

    @staticmethod
    def return_bundle(bundle, operator_user, quantity, remark=''):
        """交货：允许分次交回，全部交回后自动清空当前持有人与工序。"""
        if bundle.status in {'cancelled', 'completed'}:
            return None, '当前菲已作废或已完工，不能交货'
        metrics = BundleService.calculate_flow_metrics(bundle)
        current_in_hand = metrics['in_hand_quantity']
        if current_in_hand <= 0 or not bundle.current_holder_user_id:
            return None, '当前菲没有可交回的在手数量'
        if quantity <= 0:
            return None, '交货数量必须大于 0'
        if quantity > current_in_hand:
            return None, '交货数量不能大于当前在手数量'

        current_holder_user_id = bundle.current_holder_user_id
        current_process_id = bundle.current_process_id
        remaining_quantity = current_in_hand - quantity
        if remaining_quantity > 0:
            bundle.status = 'in_progress'
        else:
            bundle.status = 'returned'
            bundle.current_holder_user_id = None
            bundle.current_process_id = None
        db.session.add(bundle)
        BundleService.append_flow(
            bundle,
            action_type='return',
            quantity=quantity,
            user_id=operator_user.id,
            process_id=current_process_id,
            from_user_id=current_holder_user_id or operator_user.id,
            to_user_id=operator_user.id if operator_user.id != current_holder_user_id else None,
            remark=remark or '交货回仓',
        )
        db.session.commit()
        return BundleService.get_bundle_by_id(bundle.id), None

    @staticmethod
    def transfer_bundle(bundle, operator_user, to_user_id, process_id, remark=''):
        """转交：把当前在手菲从一个持有人转给另一个持有人，并可同步调整工序。"""
        if bundle.status in {'cancelled', 'completed'}:
            return None, '当前菲已作废或已完工，不能转交'
        metrics = BundleService.calculate_flow_metrics(bundle)
        if metrics['in_hand_quantity'] <= 0 or not bundle.current_holder_user_id:
            return None, '当前菲没有可转交的在手数量'

        process = BundleService.get_bundle_process(process_id)
        if not process:
            return None, '工序不存在或未启用'

        to_user = BundleService.get_factory_active_user(bundle.factory_id, to_user_id)
        if not to_user:
            return None, '接收人不存在或不属于当前工厂有效用户'

        if to_user.id == bundle.current_holder_user_id and process.id == (bundle.current_process_id or 0):
            return None, '转交目标与当前持有人及工序一致，无需重复转交'

        from_user_id = bundle.current_holder_user_id
        bundle.current_holder_user_id = to_user.id
        bundle.current_process_id = process.id
        bundle.status = 'in_progress'
        db.session.add(bundle)
        BundleService.append_flow(
            bundle,
            action_type='transfer',
            quantity=metrics['in_hand_quantity'],
            user_id=operator_user.id,
            process_id=process.id,
            from_user_id=from_user_id,
            to_user_id=to_user.id,
            remark=remark or '菲转交',
        )
        db.session.commit()
        return BundleService.get_bundle_by_id(bundle.id), None

    @staticmethod
    def complete_bundle(bundle, operator_user, remark=''):
        """完工确认：要求菲已经全部交回，确认后流转状态改为已完工。"""
        if bundle.status == 'completed':
            return None, '当前菲已完工，不能重复确认'
        if bundle.status == 'cancelled':
            return None, '当前菲已作废，不能完工确认'

        metrics = BundleService.calculate_flow_metrics(bundle)
        if metrics['in_hand_quantity'] > 0:
            return None, '当前菲仍有在手数量，不能完工确认'
        if metrics['returned_quantity'] <= 0:
            return None, '当前菲尚未发生交货，不能完工确认'
        if bundle.current_holder_user_id or bundle.current_process_id:
            return None, '当前菲仍挂在持有人或工序上，不能完工确认'

        bundle.status = 'completed'
        db.session.add(bundle)
        BundleService.append_flow(
            bundle,
            action_type='complete',
            quantity=bundle.bundle_quantity,
            user_id=operator_user.id,
            remark=remark or '完工确认',
        )
        db.session.commit()
        return BundleService.get_bundle_by_id(bundle.id), None

    @staticmethod
    def get_in_hand_statistics(factory_id, filters):
        """统计当前工厂的在手菲数量，按持有人、工序和状态分组返回。"""
        holder_user_id = filters.get('holder_user_id')
        process_id = filters.get('process_id')

        bundles = ProductionBundle.query.options(*BundleService.get_bundle_query_options()).filter_by(
            factory_id=factory_id,
            is_deleted=0,
        ).all()

        holder_totals = {}
        process_totals = {}
        status_totals = {}
        total_bundle_count = 0
        total_bundle_quantity = 0
        total_issued_quantity = 0
        total_returned_quantity = 0
        total_in_hand_quantity = 0

        for bundle in bundles:
            metrics = BundleService.calculate_flow_metrics(bundle)
            if metrics['in_hand_quantity'] <= 0:
                continue
            if holder_user_id and bundle.current_holder_user_id != holder_user_id:
                continue
            if process_id and bundle.current_process_id != process_id:
                continue

            total_bundle_count += 1
            total_bundle_quantity += bundle.bundle_quantity or 0
            total_issued_quantity += metrics['issued_quantity']
            total_returned_quantity += metrics['returned_quantity']
            total_in_hand_quantity += metrics['in_hand_quantity']

            holder_key = bundle.current_holder_user_id or 0
            holder_bucket = holder_totals.setdefault(holder_key, {
                'user_id': bundle.current_holder_user_id,
                'user_name': bundle.current_holder.nickname if bundle.current_holder else '未分配',
                'bundle_count': 0,
                'quantity': 0,
            })
            holder_bucket['bundle_count'] += 1
            holder_bucket['quantity'] += metrics['in_hand_quantity']

            process_key = bundle.current_process_id or 0
            process_bucket = process_totals.setdefault(process_key, {
                'process_id': bundle.current_process_id,
                'process_name': bundle.current_process.name if bundle.current_process else '未分配',
                'bundle_count': 0,
                'quantity': 0,
            })
            process_bucket['bundle_count'] += 1
            process_bucket['quantity'] += metrics['in_hand_quantity']

            status_key = bundle.status
            status_bucket = status_totals.setdefault(status_key, {
                'status': bundle.status,
                'status_label': bundle.status_label,
                'bundle_count': 0,
                'quantity': 0,
            })
            status_bucket['bundle_count'] += 1
            status_bucket['quantity'] += metrics['in_hand_quantity']

        return {
            'bundle_count': total_bundle_count,
            'bundle_quantity': total_bundle_quantity,
            'issued_quantity': total_issued_quantity,
            'returned_quantity': total_returned_quantity,
            'in_hand_quantity': total_in_hand_quantity,
            'holder_totals': list(holder_totals.values()),
            'process_totals': list(process_totals.values()),
            'status_totals': list(status_totals.values()),
        }

    @staticmethod
    def build_print_preview(bundle):
        """构建菲打印预览结构，供前端或后续打印机调用。"""
        content = bundle.printed_content or ''
        return {
            'bundle_id': bundle.id,
            'bundle_no': bundle.bundle_no,
            'template_id': bundle.template_id,
            'template_version': bundle.template_version,
            'content': content,
            'lines': [line for line in content.splitlines() if line],
        }

    @staticmethod
    def print_bundle(bundle, operator_user, remark=''):
        """执行一次打印登记，刷新打印时间和次数，并补一条打印流转日志。"""
        if bundle.status == 'cancelled':
            return None, '当前菲已作废，不能打印'

        if not bundle.printed_content:
            template = bundle.template or BundleTemplateService.get_system_default_template()
            bundle.printed_content = BundleService.render_bundle_content(bundle, template)

        bundle.printed_at = datetime.now()
        bundle.print_count = (bundle.print_count or 0) + 1
        db.session.add(bundle)
        BundleService.append_flow(
            bundle,
            action_type='print',
            quantity=0,
            user_id=operator_user.id,
            remark=remark or '打印菲',
        )
        db.session.commit()
        return BundleService.get_bundle_by_id(bundle.id), None
