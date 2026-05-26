"""款号价格管理服务。"""

from datetime import datetime

from app.models.business.style_price import StylePrice
from app.services.base.base_service import BaseService
from app.services.business.style_service import StyleService


class StylePriceService(BaseService):
    """封装款号价格记录的查询与维护逻辑。"""

    PRICE_TYPE_LABELS = {
        'customer': '客户价',
        'internal': '工厂内部价',
        'outsourced': '外发价',
        'button': '钉扣价',
        'other': '其他',
    }

    @staticmethod
    def get_price_by_id(price_id):
        """根据价格记录 ID 查询详情。"""
        return StylePrice.query.filter_by(id=price_id, is_deleted=0).first()

    @staticmethod
    def get_price_label(price_type):
        """返回价格类型的中文名称。"""
        return StylePriceService.PRICE_TYPE_LABELS.get(price_type, price_type)

    @staticmethod
    def get_price_list(style_id, filters):
        """分页查询指定款号下的价格记录。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        price_type = filters.get('price_type')

        query = StylePrice.query.filter_by(style_id=style_id, is_deleted=0)
        if price_type:
            query = query.filter_by(price_type=price_type)

        pagination = query.order_by(StylePrice.effective_date.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False,
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
        """创建款号价格记录。"""
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
        """逻辑删除价格记录。"""
        price.is_deleted = 1
        price.save()
        return True

    @staticmethod
    def check_style_permission(current_user, current_factory_id, style_id):
        """校验当前用户是否可以访问指定款号。"""
        return StyleService.get_accessible_style(current_user, current_factory_id, style_id)

    @staticmethod
    def check_price_permission(current_user, current_factory_id, price):
        """校验当前用户是否可以访问指定价格记录。"""
        style, error = StyleService.get_accessible_style(current_user, current_factory_id, price.style_id)
        if error or not style:
            return False, error or '无权限操作'
        return True, None

    @staticmethod
    def enrich_with_label(price_data, price_obj):
        """为价格响应补充价格类型中文名称。"""
        price_data['price_type_label'] = StylePriceService.get_price_label(price_obj.price_type)
        return price_data
