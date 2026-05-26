"""出货单管理服务。"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.business.bundle import ProductionBundle
from app.models.business.order import Order, OrderDetail, OrderDetailSku
from app.models.business.shipment import Shipment, ShipmentItem
from app.services.base.base_service import BaseService
from app.services.business.data_scope_service import BusinessDataScopeService


class ShipmentService(BaseService):
    """封装出货单的查询、校验与维护逻辑。"""

    ACTIVE_STATUSES = {'created'}

    @staticmethod
    def generate_shipment_no(factory_id):
        """按工厂和日期生成出货单号。"""
        today = datetime.now().strftime('%Y%m%d')
        last_shipment = Shipment.query.filter(
            Shipment.shipment_no.like(f'SHP{factory_id}{today}%'),
            Shipment.is_deleted == 0,
        ).order_by(Shipment.id.desc()).first()
        seq = int(last_shipment.shipment_no[-4:]) + 1 if last_shipment else 1
        return f'SHP{factory_id}{today}{seq:04d}'

    @staticmethod
    def get_shipment_query_options():
        """返回出货单详情查询需要的预加载配置。"""
        return [
            joinedload(Shipment.order),
            selectinload(Shipment.items).joinedload(ShipmentItem.style),
            selectinload(Shipment.items).joinedload(ShipmentItem.color),
            selectinload(Shipment.items).joinedload(ShipmentItem.size),
            selectinload(Shipment.items).joinedload(ShipmentItem.sku),
        ]

    @staticmethod
    def get_shipment_by_id(shipment_id):
        """根据 ID 查询出货单详情。"""
        return Shipment.query.options(*ShipmentService.get_shipment_query_options()).filter_by(
            id=shipment_id,
            is_deleted=0,
        ).first()

    @staticmethod
    def _build_shipment_query(current_user, current_factory_id=None, factory_id=None):
        """构建出货单查询对象，统一处理内部用户与外部用户的工厂范围。"""
        query = Shipment.query.options(*ShipmentService.get_shipment_query_options()).filter_by(is_deleted=0)
        if current_user.is_internal_user:
            if factory_id:
                query = query.filter_by(factory_id=factory_id)
        else:
            if not current_factory_id:
                return None
            query = query.filter_by(factory_id=current_factory_id)

        target_factory_id = factory_id if current_user.is_internal_user else current_factory_id
        return ShipmentService.apply_shipment_data_scope(query, current_user, current_factory_id=target_factory_id)

    @staticmethod
    def apply_shipment_data_scope(query, current_user, current_factory_id=None):
        """按当前用户数据范围收口出货单查询。"""
        own_related_filter = BusinessDataScopeService.build_or_filter(
            Shipment.customer_id == current_user.id,
            Shipment.create_by == current_user.id,
            Shipment.order.has(Order.create_by == current_user.id),
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
    def get_shipment_list(current_user, current_factory_id, filters):
        """分页查询当前可见范围内的出货单列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        shipment_no = filters.get('shipment_no', '')
        order_no = filters.get('order_no', '')
        customer_name = filters.get('customer_name', '')
        status = filters.get('status')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        query = ShipmentService._build_shipment_query(
            current_user,
            current_factory_id=current_factory_id,
            factory_id=filters.get('factory_id'),
        )
        if query is None:
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

        if shipment_no:
            query = query.filter(Shipment.shipment_no.like(f'%{shipment_no}%'))
        if order_no:
            query = query.join(Shipment.order).filter(Order.order_no.like(f'%{order_no}%'))
        if customer_name:
            query = query.filter(Shipment.customer_name.like(f'%{customer_name}%'))
        if status:
            query = query.filter_by(status=status)
        if start_date:
            query = query.filter(Shipment.ship_date >= start_date)
        if end_date:
            query = query.filter(Shipment.ship_date <= end_date)

        pagination = query.order_by(Shipment.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def check_permission(current_user, current_factory_id, shipment):
        """校验当前用户是否可以查看指定出货单。"""
        if not current_user:
            return False, '用户不存在'
        if not shipment:
            return False, '出货单不存在'
        if not current_user.is_internal_user and shipment.factory_id != current_factory_id:
            return False, '无权限操作'

        scoped_query = ShipmentService.apply_shipment_data_scope(
            Shipment.query.filter(
                Shipment.id == shipment.id,
                Shipment.is_deleted == 0,
            ),
            current_user,
            current_factory_id=shipment.factory_id,
        )
        if scoped_query.first():
            return True, None
        return False, '出货单不在当前数据范围内'

    @staticmethod
    def get_completed_quantity_map_for_order(order_id):
        """统计订单下各 SKU 的已完工数量。"""
        rows = (
            db.session.query(
                ProductionBundle.order_detail_sku_id,
                func.coalesce(func.sum(ProductionBundle.bundle_quantity), 0),
            )
            .filter(
                ProductionBundle.order_id == order_id,
                ProductionBundle.is_deleted == 0,
                ProductionBundle.status == 'completed',
            )
            .group_by(ProductionBundle.order_detail_sku_id)
            .all()
        )
        return {sku_id: int(quantity or 0) for sku_id, quantity in rows}

    @staticmethod
    def get_shipped_quantity_map_for_order(order_id, exclude_shipment_id=None):
        """统计订单下各 SKU 的累计已出货数量。"""
        query = ShipmentItem.query.join(Shipment, Shipment.id == ShipmentItem.shipment_id).filter(
            Shipment.order_id == order_id,
            Shipment.is_deleted == 0,
            Shipment.status.in_(ShipmentService.ACTIVE_STATUSES),
            ShipmentItem.is_deleted == 0,
        )
        if exclude_shipment_id is not None:
            query = query.filter(Shipment.id != exclude_shipment_id)

        rows = (
            query.with_entities(
                ShipmentItem.order_detail_sku_id,
                func.coalesce(func.sum(ShipmentItem.quantity), 0),
            )
            .group_by(ShipmentItem.order_detail_sku_id)
            .all()
        )
        return {sku_id: int(quantity or 0) for sku_id, quantity in rows}

    @staticmethod
    def get_shipment_availability(order_id):
        """返回订单下各 SKU 的完工、已出货和可出货数量。"""
        completed_map = ShipmentService.get_completed_quantity_map_for_order(order_id)
        shipped_map = ShipmentService.get_shipped_quantity_map_for_order(order_id)
        sku_ids = set(completed_map.keys()) | set(shipped_map.keys())
        availability = {}
        for sku_id in sku_ids:
            completed_quantity = completed_map.get(sku_id, 0)
            shipped_quantity = shipped_map.get(sku_id, 0)
            availability[sku_id] = {
                'completed_quantity': completed_quantity,
                'shipped_quantity': shipped_quantity,
                'available_quantity': max(completed_quantity - shipped_quantity, 0),
            }
        return availability

    @staticmethod
    def validate_shipment_items(order, items):
        """校验出货明细是否属于订单，且数量不超过可出货范围。"""
        if not items:
            return None, '请至少填写一条出货明细'

        sku_map = {}
        for detail in order.details:
            for sku in detail.skus:
                sku_map[sku.id] = {
                    'sku': sku,
                    'detail': detail,
                }

        request_totals = {}
        for index, item in enumerate(items, start=1):
            sku_id = item['order_detail_sku_id']
            quantity = item['quantity']
            if quantity <= 0:
                return None, f'第 {index} 条出货明细数量必须大于 0'
            if sku_id not in sku_map:
                return None, f'第 {index} 条出货明细中的 SKU 不属于当前订单'
            request_totals[sku_id] = request_totals.get(sku_id, 0) + quantity

        availability = ShipmentService.get_shipment_availability(order.id)
        normalized_items = []
        for sku_id, quantity in request_totals.items():
            available_quantity = availability.get(sku_id, {}).get('available_quantity', 0)
            if quantity > available_quantity:
                sku = sku_map[sku_id]['sku']
                style = sku_map[sku_id]['detail'].style
                style_no = style.style_no if style else sku_id
                return None, f'SKU {style_no}-{sku_id} 可出货数量不足，当前最多可出货 {available_quantity}'

        for item in items:
            mapping = sku_map[item['order_detail_sku_id']]
            normalized_items.append({
                'sku': mapping['sku'],
                'detail': mapping['detail'],
                'quantity': item['quantity'],
                'remark': item.get('remark', ''),
            })
        return normalized_items, None

    @staticmethod
    def create_shipment(current_user, current_factory_id, data):
        """创建出货单，并按订单 SKU 生成出货明细。"""
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        order = Order.query.options(
            selectinload(Order.details).joinedload(OrderDetail.style),
            selectinload(Order.details).selectinload(OrderDetail.skus).joinedload(OrderDetailSku.color),
            selectinload(Order.details).selectinload(OrderDetail.skus).joinedload(OrderDetailSku.size),
        ).filter_by(
            id=data['order_id'],
            factory_id=current_factory_id,
            is_deleted=0,
        ).first()
        if not order:
            return None, '订单不存在或不属于当前工厂'

        has_scope = BusinessDataScopeService.check_creator_customer_scope(
            current_user,
            current_factory_id=current_factory_id,
            creator_user_id=order.create_by,
            customer_user_id=order.customer_id,
        )
        if not has_scope:
            return None, '当前订单不在当前数据范围内，不能创建出货单'

        normalized_items, error = ShipmentService.validate_shipment_items(order, data.get('items') or [])
        if error:
            return None, error

        try:
            shipment = Shipment(
                shipment_no=ShipmentService.generate_shipment_no(current_factory_id),
                factory_id=current_factory_id,
                order_id=order.id,
                customer_id=order.customer_id,
                customer_name=order.customer_name,
                ship_date=datetime.strptime(data['ship_date'], '%Y-%m-%d').date(),
                status='created',
                remark=data.get('remark', ''),
                create_by=current_user.id,
                update_by=current_user.id,
            )
            db.session.add(shipment)
            db.session.flush()

            for item in normalized_items:
                sku = item['sku']
                detail = item['detail']
                db.session.add(ShipmentItem(
                    shipment_id=shipment.id,
                    order_detail_id=detail.id,
                    order_detail_sku_id=sku.id,
                    style_id=detail.style_id,
                    color_id=sku.color_id,
                    size_id=sku.size_id,
                    quantity=item['quantity'],
                    remark=item['remark'],
                ))

            db.session.commit()
            return ShipmentService.get_shipment_by_id(shipment.id), None
        except Exception as exc:
            db.session.rollback()
            return None, f'创建出货单失败: {exc}'

    @staticmethod
    def cancel_shipment(shipment, current_user, remark=''):
        """作废出货单，使其不再参与已出货统计。"""
        if shipment.status == 'cancelled':
            return None, '当前出货单已作废，不能重复作废'

        shipment.status = 'cancelled'
        shipment.update_by = current_user.id
        if remark:
            shipment.remark = f'{shipment.remark}\n作废备注：{remark}'.strip() if shipment.remark else f'作废备注：{remark}'
        db.session.add(shipment)
        db.session.commit()
        return ShipmentService.get_shipment_by_id(shipment.id), None

    @staticmethod
    def build_shipment_list_statistics(shipments):
        """构建出货单列表统计，汇总单数、件数和状态分布。"""
        status_totals = {}
        customer_totals = {}
        total_quantity = 0

        for shipment in shipments:
            shipment_quantity = shipment.total_quantity
            total_quantity += shipment_quantity
            status_key = shipment.status_label
            customer_key = shipment.customer_name or ''
            status_totals[status_key] = status_totals.get(status_key, 0) + shipment_quantity
            customer_totals[customer_key] = customer_totals.get(customer_key, 0) + shipment_quantity

        return {
            'shipment_count': len(shipments),
            'total_quantity': total_quantity,
            'status_totals': [
                {'name': name, 'quantity': quantity}
                for name, quantity in status_totals.items()
            ],
            'customer_totals': [
                {'name': name, 'quantity': quantity}
                for name, quantity in customer_totals.items()
            ],
        }
