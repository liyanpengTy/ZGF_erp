"""款号价格管理服务"""
from datetime import datetime

from app.models.business.style import Style
from app.models.business.style_price import StylePrice
from app.services.base.base_service import BaseService


class StylePriceService(BaseService):
    """款号价格管理服务"""

    PRICE_TYPE_LABELS = {
        'customer': '客户价',
        'internal': '工厂内部价',
        'outsourced': '外发价',
        'button': '钉扣价',
        'other': '其他',
    }

    @staticmethod
    def get_price_by_id(price_id):
        return StylePrice.query.filter_by(id=price_id, is_deleted=0).first()

    @staticmethod
    def get_price_label(price_type):
        return StylePriceService.PRICE_TYPE_LABELS.get(price_type, price_type)

    @staticmethod
    def get_price_list(style_id, filters):
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        price_type = filters.get('price_type')

        query = StylePrice.query.filter_by(style_id=style_id, is_deleted=0)
        if price_type:
            query = query.filter_by(price_type=price_type)

        pagination = query.order_by(StylePrice.effective_date.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def create_price(data):
        effective_date = None
        if data.get('effective_date'):
            effective_date = datetime.strptime(data['effective_date'], '%Y-%m-%d').date()

        price = StylePrice(
            style_id=data['style_id'],
            price_type=data['price_type'],
            price=data['price'],
            effective_date=effective_date,
            remark=data.get('remark', ''),
        )
        price.save()
        return price

    @staticmethod
    def delete_price(price):
        price.is_deleted = 1
        price.save()
        return True

    @staticmethod
    def check_style_permission(current_factory_id, style_id):
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        style = Style.query.filter_by(id=style_id, factory_id=current_factory_id, is_deleted=0).first()
        if not style:
            return None, '款号不存在或无权限'
        return style, None

    @staticmethod
    def check_price_permission(current_factory_id, price):
        if not current_factory_id:
            return False, '请先切换到工厂上下文'

        style = Style.query.filter_by(id=price.style_id, factory_id=current_factory_id, is_deleted=0).first()
        if not style:
            return False, '无权限操作'
        return True, None

    @staticmethod
    def enrich_with_label(price_data, price_obj):
        price_data['price_type_label'] = StylePriceService.get_price_label(price_obj.price_type)
        return price_data
