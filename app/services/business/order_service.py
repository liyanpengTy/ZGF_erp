"""订单管理服务"""
from datetime import datetime
from app.extensions import db
from app.models.business.order import Order, OrderDetail
from app.models.business.style import Style
from app.services.base.base_service import BaseService


class OrderService(BaseService):
    """订单管理服务"""

    @staticmethod
    def generate_order_no(factory_id):
        """生成订单号：ORD + 工厂ID + 年月日 + 流水号"""
        today = datetime.now().strftime('%Y%m%d')
        last_order = Order.query.filter(
            Order.order_no.like(f'ORD{factory_id}{today}%'),
            Order.is_deleted == 0
        ).order_by(Order.id.desc()).first()

        if last_order:
            last_seq = int(last_order.order_no[-4:])
            seq = last_seq + 1
        else:
            seq = 1

        return f'ORD{factory_id}{today}{seq:04d}'

    @staticmethod
    def get_order_by_id(order_id):
        """根据ID获取订单"""
        return Order.query.filter_by(id=order_id, is_deleted=0).first()

    @staticmethod
    def get_order_by_no(order_no):
        """根据订单号获取订单"""
        return Order.query.filter_by(order_no=order_no, is_deleted=0).first()

    @staticmethod
    def get_order_list(current_user, filters):
        """获取订单列表"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        order_no = filters.get('order_no', '')
        customer_name = filters.get('customer_name', '')
        status = filters.get('status')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        query = Order.query.filter_by(factory_id=current_user.factory_id, is_deleted=0)

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

        pagination = query.order_by(Order.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def create_order(current_user, data):
        """创建订单"""
        order_no = OrderService.generate_order_no(current_user.factory_id)

        total_amount = 0
        for detail in data['details']:
            total_amount += detail['quantity'] * detail.get('unit_price', 0)

        order = Order(
            order_no=order_no,
            factory_id=current_user.factory_id,
            customer_id=data.get('customer_id'),
            customer_name=data.get('customer_name', ''),
            order_date=datetime.strptime(data['order_date'], '%Y-%m-%d').date(),
            delivery_date=datetime.strptime(data['delivery_date'], '%Y-%m-%d').date() if data.get('delivery_date') else None,
            status='pending',
            total_amount=total_amount,
            remark=data.get('remark', ''),
            create_by=current_user.id
        )
        order.save()

        for item in data['details']:
            style = Style.query.filter_by(id=item['style_id'], is_deleted=0).first()
            amount = item['quantity'] * item.get('unit_price', 0)

            detail = OrderDetail(
                order_id=order.id,
                style_id=item['style_id'],
                style_no=style.style_no if style else '',
                style_name=style.name if style else '',
                quantity=item['quantity'],
                unit_price=item.get('unit_price', 0),
                amount=amount,
                remark=item.get('remark', '')
            )
            detail.save()

        return order

    @staticmethod
    def update_order(order, data):
        """更新订单"""
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
        """更新订单状态"""
        order.status = status
        order.save()
        return order

    @staticmethod
    def delete_order(order):
        """删除订单（软删除）"""
        order.is_deleted = 1
        order.save()
        return True

    @staticmethod
    def check_permission(current_user, order):
        """检查用户是否有权限操作该订单"""
        if not current_user:
            return False, '用户不存在'

        if current_user.is_admin == 1:
            return True, None

        if order.factory_id != current_user.factory_id:
            return False, '无权限操作'

        return True, None
