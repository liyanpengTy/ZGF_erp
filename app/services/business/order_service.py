"""订单管理服务"""
from datetime import datetime

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.business.order import Order, OrderDetail, OrderDetailSku
from app.models.business.style import Style
from app.services.base.base_service import BaseService


class OrderService(BaseService):
    """订单管理服务"""

    @staticmethod
    def generate_order_no(factory_id):
        today = datetime.now().strftime('%Y%m%d')
        last_order = Order.query.filter(
            Order.order_no.like(f'ORD{factory_id}{today}%'),
        ).order_by(Order.id.desc()).first()

        seq = int(last_order.order_no[-4:]) + 1 if last_order else 1
        return f'ORD{factory_id}{today}{seq:04d}'

    @staticmethod
    def get_order_by_id(order_id):
        return Order.query.options(
            joinedload(Order.details).selectinload(OrderDetail.skus),
            joinedload(Order.details).joinedload(OrderDetail.style),
        ).filter_by(id=order_id, is_deleted=0).first()

    @staticmethod
    def get_order_by_no(order_no):
        return Order.query.filter_by(order_no=order_no, is_deleted=0).first()

    @staticmethod
    def get_order_list(current_factory_id, filters):
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        order_no = filters.get('order_no', '')
        customer_name = filters.get('customer_name', '')
        status = filters.get('status')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        if not current_factory_id:
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

        query = Order.query.filter_by(factory_id=current_factory_id, is_deleted=0).options(
            joinedload(Order.details).selectinload(OrderDetail.skus),
            joinedload(Order.details).joinedload(OrderDetail.style),
        )

        if order_no:
            query = query.filter(Order.order_no.like(f'%{order_no}%'))
        if customer_name:
            query = query.filter(Order.customer_name.like(f'%{customer_name}%'))
        if status:
            query = query.filter_by(status=status)
        if start_date:
            query = query.filter(Order.order_date >= start_date)
        if end_date:
            query = query.filter(Order.order_date <= end_date)

        pagination = query.order_by(Order.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def create_order(current_user, current_factory_id, data):
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        details = data.get('details') or []
        if not details:
            return None, '请添加订单明细'

        style_ids = [item.get('style_id') for item in details if item.get('style_id') is not None]
        if not style_ids:
            return None, '订单明细缺少款号'

        styles = Style.query.filter(
            Style.id.in_(style_ids),
            Style.factory_id == current_factory_id,
            Style.is_deleted == 0,
        ).all()
        style_map = {style.id: style for style in styles}
        missing_style_ids = sorted(set(style_ids) - set(style_map.keys()))
        if missing_style_ids:
            return None, f'以下款号不存在或无权限: {missing_style_ids}'

        for index, detail_data in enumerate(details, start=1):
            skus = detail_data.get('skus') or []
            if not skus:
                return None, f'第 {index} 条订单明细缺少 SKU'

        try:
            order_no = OrderService.generate_order_no(current_factory_id)
            order = Order(
                order_no=order_no,
                factory_id=current_factory_id,
                customer_id=data.get('customer_id'),
                customer_name=data.get('customer_name', ''),
                order_date=datetime.strptime(data['order_date'], '%Y-%m-%d').date(),
                delivery_date=datetime.strptime(data['delivery_date'], '%Y-%m-%d').date() if data.get('delivery_date') else None,
                status='pending',
                total_amount=0,
                remark=data.get('remark', ''),
                create_by=current_user.id,
            )
            db.session.add(order)
            db.session.flush()

            for detail_data in details:
                style = style_map[detail_data['style_id']]
                detail = OrderDetail(
                    order_id=order.id,
                    style_id=style.id,
                    snapshot_splice_data=style.splice_data if style.is_splice == 1 else None,
                    snapshot_custom_attributes=style.custom_attributes,
                    remark=detail_data.get('remark', ''),
                )
                db.session.add(detail)
                db.session.flush()

                for sku_data in detail_data['skus']:
                    sku = OrderDetailSku(
                        detail_id=detail.id,
                        splice_config=sku_data['splice_config'],
                        remark=sku_data.get('remark', ''),
                    )
                    db.session.add(sku)

            db.session.commit()
            return OrderService.get_order_by_id(order.id), None
        except Exception as exc:
            db.session.rollback()
            return None, f'创建订单失败: {exc}'

    @staticmethod
    def update_order(order, data):
        if 'customer_id' in data:
            order.customer_id = data['customer_id']
        if 'customer_name' in data:
            order.customer_name = data['customer_name']
        if 'delivery_date' in data and data['delivery_date']:
            order.delivery_date = datetime.strptime(data['delivery_date'], '%Y-%m-%d').date()
        if 'remark' in data:
            order.remark = data['remark']
        order.save()
        return order

    @staticmethod
    def update_order_status(order, status):
        order.status = status
        order.save()
        return order

    @staticmethod
    def delete_order(order):
        order.is_deleted = 1
        order.save()
        return True

    @staticmethod
    def check_permission(current_user, current_factory_id, order):
        if not current_user:
            return False, '用户不存在'
        if current_user.is_admin == 1:
            return True, None
        if order.factory_id != current_factory_id:
            return False, '无权限操作'
        return True, None
