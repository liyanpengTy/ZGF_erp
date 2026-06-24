"""裁床报工服务。"""

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.business.bundle import BundleTemplate, ProductionBundle
from app.models.business.cutting_report import WorkCuttingReport
from app.models.business.order import Order, OrderDetail, OrderDetailSku
from app.services.base.base_service import BaseService
from app.services.business.bundle_service import BundleService, BundleTemplateService
from app.services.business.data_scope_service import BusinessDataScopeService


class CuttingReportService(BaseService):
    """封装裁床报工与菲生成逻辑。"""

    @staticmethod
    def get_cutting_report_query_options():
        """返回裁床报工详情查询需要的预加载配置。"""
        return [
            joinedload(WorkCuttingReport.style),
            joinedload(WorkCuttingReport.color),
            joinedload(WorkCuttingReport.size),
            joinedload(WorkCuttingReport.report_user),
            selectinload(WorkCuttingReport.bundles).joinedload(ProductionBundle.style),
            selectinload(WorkCuttingReport.bundles).joinedload(ProductionBundle.color),
            selectinload(WorkCuttingReport.bundles).joinedload(ProductionBundle.size),
            selectinload(WorkCuttingReport.bundles).joinedload(ProductionBundle.template).selectinload(BundleTemplate.items),
        ]

    @staticmethod
    def get_cutting_report_by_id(report_id):
        """根据 ID 查询裁床报工详情。"""
        return WorkCuttingReport.query.options(*CuttingReportService.get_cutting_report_query_options()).filter_by(
            id=report_id,
            is_deleted=0,
        ).first()

    @staticmethod
    def _build_cutting_report_query(current_user, current_factory_id=None, factory_id=None):
        """构建裁床报工查询对象，统一处理内部用户与外部用户的工厂范围。"""
        query = WorkCuttingReport.query.options(*CuttingReportService.get_cutting_report_query_options()).filter_by(
            is_deleted=0,
        )
        if current_user.is_internal_user:
            if factory_id:
                query = query.filter_by(factory_id=factory_id)
            return CuttingReportService.apply_cutting_report_data_scope(
                query,
                current_user,
                current_factory_id=factory_id,
            )

        if not current_factory_id:
            return query.filter(WorkCuttingReport.id == 0)
        query = query.filter_by(factory_id=current_factory_id)
        return CuttingReportService.apply_cutting_report_data_scope(
            query,
            current_user,
            current_factory_id=current_factory_id,
        )

    @staticmethod
    def apply_cutting_report_data_scope(query, current_user, current_factory_id=None):
        """按当前用户数据范围收口裁床报工查询。"""
        own_related_filter = BusinessDataScopeService.build_or_filter(
            WorkCuttingReport.report_user_id == current_user.id,
            WorkCuttingReport.order.has(create_by=current_user.id),
        )
        return BusinessDataScopeService.apply_scope(
            query,
            current_user,
            current_factory_id=current_factory_id,
            assigned_filter=own_related_filter,
            own_related_filter=own_related_filter,
            self_only_filter=own_related_filter,
        )

    @staticmethod
    def get_cutting_report_list(current_user, current_factory_id, filters):
        """分页查询当前可见范围内的裁床报工列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        cut_batch_no = filters.get('cut_batch_no')
        order_detail_sku_id = filters.get('order_detail_sku_id')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        query = CuttingReportService._build_cutting_report_query(
            current_user,
            current_factory_id=current_factory_id,
            factory_id=filters.get('factory_id'),
        )
        if cut_batch_no is not None:
            query = query.filter_by(cut_batch_no=cut_batch_no)
        if order_detail_sku_id:
            query = query.filter_by(order_detail_sku_id=order_detail_sku_id)
        if start_date:
            query = query.filter(WorkCuttingReport.cut_date >= start_date)
        if end_date:
            query = query.filter(WorkCuttingReport.cut_date <= end_date)

        pagination = query.order_by(WorkCuttingReport.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def check_permission(current_user, current_factory_id, report):
        """校验当前用户是否可以查看指定裁床报工。"""
        if not current_user:
            return False, '用户不存在'
        if not report:
            return False, '裁床报工不存在'
        if not current_user.is_internal_user and not current_factory_id:
            return False, '当前缺少工厂上下文，请先切换工厂'
        if not current_user.is_internal_user and report.factory_id != current_factory_id:
            return False, '无权查看当前裁床报工数据'

        scoped_query = CuttingReportService.apply_cutting_report_data_scope(
            WorkCuttingReport.query.filter(
                WorkCuttingReport.id == report.id,
                WorkCuttingReport.is_deleted == 0,
            ),
            current_user,
            current_factory_id=report.factory_id,
        )
        if scoped_query.first():
            return True, None
        return False, '当前裁床报工不在数据范围内'

    @staticmethod
    def get_order_sku(order_detail_sku_id, factory_id):
        """查询当前主体内可用于裁床报工的订单 SKU。"""
        return OrderDetailSku.query.options(
            joinedload(OrderDetailSku.detail).joinedload(OrderDetail.order),
            joinedload(OrderDetailSku.detail).joinedload(OrderDetail.style),
            joinedload(OrderDetailSku.color),
            joinedload(OrderDetailSku.size),
        ).join(OrderDetailSku.detail).join(OrderDetail.order).filter(
            OrderDetailSku.id == order_detail_sku_id,
            OrderDetailSku.is_deleted == 0,
            or_(Order.subject_id == factory_id, Order.factory_id == factory_id),
        ).first()

    @staticmethod
    def normalize_bundles(data):
        """标准化裁床报工中的菲拆分列表。"""
        bundles = data.get('bundles') or []
        if not bundles:
            return [{'bed_no': 1, 'bundle_quantity': data['cut_quantity'], 'priority': 'normal', 'remark': ''}], None

        total_quantity = sum(item['bundle_quantity'] for item in bundles)
        if total_quantity != data['cut_quantity']:
            return None, '菲拆分数量合计必须等于实裁数量'
        return bundles, None

    @staticmethod
    def create_cutting_report(current_user, factory_id, data):
        """创建裁床报工，并按模板自动生成对应的菲。"""
        order_sku = CuttingReportService.get_order_sku(data['order_detail_sku_id'], factory_id)
        if not order_sku:
            return None, '订单 SKU 不存在或不属于当前工厂'

        order = order_sku.detail.order
        has_scope = BusinessDataScopeService.check_creator_customer_scope(
            current_user,
            current_factory_id=factory_id,
            creator_user_id=order.create_by,
        )
        if not has_scope:
            return None, '当前订单不在当前数据范围内，不能创建裁床报工'

        bundles, error = CuttingReportService.normalize_bundles(data)
        if error:
            return None, error

        template, error = BundleTemplateService.resolve_template(factory_id, data.get('template_id'))
        if error:
            return None, error

        cut_date = datetime.strptime(data['cut_date'], '%Y-%m-%d').date()
        cut_batch_no = BundleTemplateService.next_cut_batch_no(
            factory_id,
            datetime.combine(cut_date, datetime.min.time()),
        )
        rule = BundleTemplateService.ensure_factory_rule(factory_id)

        report = WorkCuttingReport(
            factory_id=factory_id,
            template_id=template.id,
            order_id=order_sku.detail.order_id,
            order_detail_id=order_sku.detail_id,
            order_detail_sku_id=order_sku.id,
            style_id=order_sku.detail.style_id,
            color_id=order_sku.color_id,
            size_id=order_sku.size_id,
            report_user_id=current_user.id,
            cut_batch_no=cut_batch_no,
            cut_date=cut_date,
            cut_quantity=data['cut_quantity'],
            bundle_count=len(bundles),
            status='active',
            remark=data.get('remark', ''),
        )
        db.session.add(report)
        db.session.flush()

        for item in bundles:
            bundle = ProductionBundle(
                factory_id=factory_id,
                cutting_report_id=report.id,
                template_id=template.id,
                template_version=template.version,
                bundle_no='',
                order_id=order_sku.detail.order_id,
                order_detail_id=order_sku.detail_id,
                order_detail_sku_id=order_sku.id,
                style_id=order_sku.detail.style_id,
                color_id=order_sku.color_id,
                size_id=order_sku.size_id,
                cut_batch_no=cut_batch_no,
                bed_no=item.get('bed_no', 1),
                bundle_quantity=item['bundle_quantity'],
                priority=item.get('priority', 'normal'),
                status='created',
                remark=item.get('remark', ''),
            )
            db.session.add(bundle)
            db.session.flush()
            BundleService.assign_bundle_no(bundle, rule)
            bundle.printed_content = BundleService.render_bundle_content(bundle, template)
            BundleService.append_flow(
                bundle,
                action_type='create',
                quantity=bundle.bundle_quantity,
                user_id=current_user.id,
                remark='裁床报工自动生成菲',
            )

        db.session.add(report)
        db.session.commit()
        return CuttingReportService.get_cutting_report_by_id(report.id), None

    @staticmethod
    def delete_cutting_report(report):
        """撤销裁床报工，仅允许撤销尚未发生后续流转的菲。"""
        for bundle in report.bundles:
            active_flows = [flow for flow in bundle.flows if flow.is_deleted == 0]
            if len(active_flows) > 1 or bundle.status != 'created':
                return False, '已有菲发生后续流转，当前报工不允许撤销'

        report.status = 'cancelled'
        report.is_deleted = 1
        db.session.add(report)
        for bundle in report.bundles:
            bundle.status = 'cancelled'
            bundle.is_deleted = 1
            db.session.add(bundle)
            for flow in bundle.flows:
                flow.is_deleted = 1
                db.session.add(flow)
        db.session.commit()
        return True, None
