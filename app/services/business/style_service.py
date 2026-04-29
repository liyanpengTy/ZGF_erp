"""款号管理服务"""
from app.extensions import db
from app.models.business.style import Style
from app.models.base_data.category import Category
from app.models.business.style_price import StylePrice
from app.models.business.style_process import StyleProcess
from app.models.business.style_elastic import StyleElastic
from app.services.base.base_service import BaseService


class StyleService(BaseService):
    """款号管理服务"""

    @staticmethod
    def get_style_by_id(style_id):
        """根据ID获取款号"""
        return Style.query.filter_by(id=style_id, is_deleted=0).first()

    @staticmethod
    def get_style_by_no(factory_id, style_no):
        """根据工厂ID和款号获取款号"""
        return Style.query.filter_by(
            factory_id=factory_id, style_no=style_no, is_deleted=0
        ).first()

    @staticmethod
    def get_category_name(category_id):
        """获取分类名称"""
        if category_id:
            category = Category.query.filter_by(id=category_id, is_deleted=0).first()
            return category.name if category else None
        return None

    @staticmethod
    def validate_splice_data(splice_data):
        """验证拼接数据格式"""
        if not isinstance(splice_data, list):
            return False

        for item in splice_data:
            if not isinstance(item, dict):
                return False
            # 必须包含 sequence 和 description
            if 'sequence' not in item:
                return False
            if 'description' not in item:
                return False
            if not isinstance(item['sequence'], int):
                return False
        return True

    @staticmethod
    def get_style_list(current_user, filters):
        """
        获取款号列表
        filters: page, page_size, style_no, name, category_id, gender, season, status
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        style_no = filters.get('style_no', '')
        name = filters.get('name', '')
        category_id = filters.get('category_id')
        gender = filters.get('gender', '')
        season = filters.get('season', '')
        status = filters.get('status')

        query = Style.query.filter_by(factory_id=current_user.factory_id, is_deleted=0)

        if style_no:
            query = query.filter(Style.style_no.like(f'%{style_no}%'))
        if name:
            query = query.filter(Style.name.like(f'%{name}%'))
        if category_id:
            query = query.filter_by(category_id=category_id)
        if gender:
            query = query.filter_by(gender=gender)
        if season:
            query = query.filter_by(season=season)
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Style.id.desc()).paginate(
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
    def create_style(current_user, data, schema=None):
        """创建款号"""
        # 检查款号是否已存在
        existing = StyleService.get_style_by_no(current_user.factory_id, data['style_no'])
        if existing:
            return None, '款号已存在'

        # 验证分类
        if data.get('category_id'):
            category = Category.query.filter_by(id=data['category_id'], is_deleted=0).first()
            if not category:
                return None, '分类不存在'

        # 验证拼接数据
        if data.get('is_splice') == 1 and data.get('splice_data'):
            if not StyleService.validate_splice_data(data['splice_data']):
                return None, '拼接数据格式错误'

        style = Style(
            factory_id=current_user.factory_id,
            style_no=data['style_no'],
            customer_style_no=data.get('customer_style_no', ''),
            name=data.get('name', ''),
            category_id=data.get('category_id'),
            gender=data.get('gender', ''),
            season=data.get('season', ''),
            material=data.get('material', ''),
            description=data.get('description', ''),
            status=1,
            images=data.get('images', []),
            need_cutting=data.get('need_cutting', 0),
            cutting_reserve=data.get('cutting_reserve', 0),
            custom_attributes=data.get('custom_attributes', {}),
            is_splice=data.get('is_splice', 0),
            splice_data=data.get('splice_data', [])
        )
        style.save()

        return style, None

    @staticmethod
    def update_style(style, data, current_user):
        """更新款号"""
        # 检查款号是否重复
        if 'style_no' in data and data['style_no'] != style.style_no:
            existing = StyleService.get_style_by_no(current_user.factory_id, data['style_no'])
            if existing:
                return None, '款号已存在'
            style.style_no = data['style_no']

        # 验证分类
        if 'category_id' in data:
            if data['category_id']:
                category = Category.query.filter_by(id=data['category_id'], is_deleted=0).first()
                if not category:
                    return None, '分类不存在'
            style.category_id = data['category_id']

        # 验证拼接数据
        if 'is_splice' in data:
            style.is_splice = data['is_splice']

        if 'splice_data' in data:
            if style.is_splice == 1 and data['splice_data']:
                if not StyleService.validate_splice_data(data['splice_data']):
                    return None, '拼接数据格式错误，需要包含 sequence 和 color 字段'
            style.splice_data = data['splice_data']

        # 更新其他字段
        if 'customer_style_no' in data:
            style.customer_style_no = data['customer_style_no']
        if 'name' in data:
            style.name = data['name']
        if 'gender' in data:
            style.gender = data['gender']
        if 'season' in data:
            style.season = data['season']
        if 'material' in data:
            style.material = data['material']
        if 'description' in data:
            style.description = data['description']
        if 'status' in data:
            style.status = data['status']
        if 'images' in data:
            style.images = data['images']
        if 'need_cutting' in data:
            style.need_cutting = data['need_cutting']
        if 'cutting_reserve' in data:
            style.cutting_reserve = data['cutting_reserve']
        if 'custom_attributes' in data:
            style.custom_attributes = data['custom_attributes']

        style.save()
        return style, None

    @staticmethod
    def delete_style(style):
        """删除款号（软删除）"""
        # 检查是否有子表数据
        price_count = StylePrice.query.filter_by(style_id=style.id, is_deleted=0).count()
        process_count = StyleProcess.query.filter_by(style_id=style.id, is_deleted=0).count()
        elastic_count = StyleElastic.query.filter_by(style_id=style.id, is_deleted=0).count()

        if price_count > 0 or process_count > 0 or elastic_count > 0:
            return False, '请先删除款号关联的价格、工艺、橡筋'

        style.is_deleted = 1
        style.save()
        return True, None

    @staticmethod
    def check_permission(current_user, style):
        """检查用户是否有权限操作该款号"""
        if not current_user:
            return False, '用户不存在'

        if current_user.is_admin == 1:
            return True, None

        if style.factory_id != current_user.factory_id:
            return False, '无权限操作'

        return True, None

    @staticmethod
    def enrich_with_category_name(style_data, style_obj):
        """为款号数据添加分类名称"""
        style_data['category_name'] = StyleService.get_category_name(style_obj.category_id)
        return style_data
