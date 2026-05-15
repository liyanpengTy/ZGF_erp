"""款号管理服务。"""

from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.base_data.category import Category
from app.models.business.style import Style, StyleAttribute, StyleImage, StyleSpliceItem
from app.models.business.style_elastic import StyleElastic
from app.models.business.style_price import StylePrice
from app.models.business.style_process import StyleProcess
from app.models.business.value_codec import encode_dynamic_value, is_scalar_value
from app.services.base.base_service import BaseService


class StyleService(BaseService):
    """款号管理服务。"""

    @staticmethod
    def get_style_by_id(style_id):
        """根据 ID 获取款号。"""
        return Style.query.options(
            joinedload(Style.category),
            selectinload(Style.image_items),
            selectinload(Style.splice_items),
            selectinload(Style.attribute_items),
        ).filter_by(id=style_id, is_deleted=0).first()

    @staticmethod
    def get_style_by_no(factory_id, style_no):
        """根据工厂和款号编码获取款号。"""
        return Style.query.filter_by(factory_id=factory_id, style_no=style_no, is_deleted=0).first()

    @staticmethod
    def get_category_name(category_id):
        """根据分类 ID 返回分类名称。"""
        if not category_id:
            return None
        category = Category.query.filter_by(id=category_id, is_deleted=0).first()
        return category.name if category else None

    @staticmethod
    def validate_splice_data(splice_data):
        """校验拼接配置的基础结构。"""
        if not isinstance(splice_data, list):
            return False
        for item in splice_data:
            if not isinstance(item, dict):
                return False
            if 'sequence' not in item or 'description' not in item:
                return False
            if not isinstance(item['sequence'], int):
                return False
        return True

    @staticmethod
    def validate_custom_attributes(custom_attributes):
        """校验自定义属性结构是否为键值对。"""
        if custom_attributes is None:
            return True
        if not isinstance(custom_attributes, dict):
            return False
        return all(is_scalar_value(value) for value in custom_attributes.values())

    @staticmethod
    def replace_style_images(style, images):
        """重建款号图片明细。"""
        style.image_items[:] = []
        for index, image_url in enumerate(images or [], start=1):
            if not image_url:
                continue
            style.image_items.append(StyleImage(image_url=image_url, sort_order=index))

    @staticmethod
    def replace_style_splice_items(style, splice_data):
        """重建款号拼接结构明细。"""
        style.splice_items[:] = []
        for item in splice_data or []:
            style.splice_items.append(
                StyleSpliceItem(
                    sequence=item['sequence'],
                    description=item['description'],
                )
            )

    @staticmethod
    def replace_style_attributes(style, custom_attributes):
        """重建款号自定义属性明细。"""
        style.attribute_items[:] = []
        for index, (attr_key, attr_value) in enumerate((custom_attributes or {}).items(), start=1):
            value_type, raw_value = encode_dynamic_value(attr_value)
            style.attribute_items.append(
                StyleAttribute(
                    attr_key=attr_key,
                    attr_value=raw_value,
                    value_type=value_type,
                    sort_order=index,
                )
            )

    @staticmethod
    def get_style_list(current_factory_id, filters):
        """分页查询当前工厂的款号列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        style_no = filters.get('style_no', '')
        name = filters.get('name', '')
        category_id = filters.get('category_id')
        gender = filters.get('gender', '')
        season = filters.get('season', '')
        status = filters.get('status')

        if not current_factory_id:
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

        query = Style.query.filter_by(factory_id=current_factory_id, is_deleted=0).options(
            joinedload(Style.category),
            selectinload(Style.image_items),
            selectinload(Style.splice_items),
            selectinload(Style.attribute_items),
        )
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

        pagination = query.order_by(Style.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def create_style(current_factory_id, data, schema=None):
        """创建款号。"""
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        existing = StyleService.get_style_by_no(current_factory_id, data['style_no'])
        if existing:
            return None, '款号已存在'

        if data.get('category_id'):
            category = Category.query.filter_by(id=data['category_id'], is_deleted=0).first()
            if not category:
                return None, '分类不存在'

        if data.get('is_splice') == 1 and data.get('splice_data'):
            if not StyleService.validate_splice_data(data['splice_data']):
                return None, '拼接数据格式错误，需要包含 sequence 和 description 字段'

        if not StyleService.validate_custom_attributes(data.get('custom_attributes')):
            return None, '自定义属性格式错误，仅支持标量值'

        try:
            style = Style(
                factory_id=current_factory_id,
                style_no=data['style_no'],
                customer_style_no=data.get('customer_style_no', ''),
                name=data.get('name', ''),
                category_id=data.get('category_id'),
                gender=data.get('gender', ''),
                season=data.get('season', ''),
                material=data.get('material', ''),
                description=data.get('description', ''),
                status=1,
                need_cutting=data.get('need_cutting', 0),
                cutting_reserve=data.get('cutting_reserve', 0),
                is_splice=data.get('is_splice', 0),
            )
            db.session.add(style)
            db.session.flush()

            StyleService.replace_style_images(style, data.get('images', []))
            StyleService.replace_style_attributes(style, data.get('custom_attributes', {}))
            if style.is_splice == 1:
                StyleService.replace_style_splice_items(style, data.get('splice_data', []))

            db.session.commit()
            return StyleService.get_style_by_id(style.id), None
        except Exception as exc:
            db.session.rollback()
            return None, f'创建款号失败: {exc}'

    @staticmethod
    def update_style(style, data, current_factory_id):
        """更新款号资料。"""
        if 'style_no' in data and data['style_no'] != style.style_no:
            existing = StyleService.get_style_by_no(current_factory_id, data['style_no'])
            if existing:
                return None, '款号已存在'
            style.style_no = data['style_no']

        if 'category_id' in data:
            if data['category_id']:
                category = Category.query.filter_by(id=data['category_id'], is_deleted=0).first()
                if not category:
                    return None, '分类不存在'
            style.category_id = data['category_id']

        if 'custom_attributes' in data and not StyleService.validate_custom_attributes(data['custom_attributes']):
            return None, '自定义属性格式错误，仅支持标量值'

        if 'splice_data' in data and style.is_splice == 1 and data['splice_data']:
            if not StyleService.validate_splice_data(data['splice_data']):
                return None, '拼接数据格式错误'

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
        if 'need_cutting' in data:
            style.need_cutting = data['need_cutting']
        if 'cutting_reserve' in data:
            style.cutting_reserve = data['cutting_reserve']
        if 'is_splice' in data:
            style.is_splice = data['is_splice']

        try:
            if 'images' in data:
                StyleService.replace_style_images(style, data['images'])
            if 'custom_attributes' in data:
                StyleService.replace_style_attributes(style, data['custom_attributes'])
            if 'splice_data' in data:
                if style.is_splice == 1:
                    StyleService.replace_style_splice_items(style, data['splice_data'])
                else:
                    StyleService.replace_style_splice_items(style, [])
            elif 'is_splice' in data and style.is_splice != 1:
                StyleService.replace_style_splice_items(style, [])

            db.session.commit()
            return StyleService.get_style_by_id(style.id), None
        except Exception as exc:
            db.session.rollback()
            return None, f'更新款号失败: {exc}'

    @staticmethod
    def delete_style(style):
        """删除款号前校验关联价格、工艺和松紧数据。"""
        price_count = StylePrice.query.filter_by(style_id=style.id, is_deleted=0).count()
        process_count = StyleProcess.query.filter_by(style_id=style.id, is_deleted=0).count()
        elastic_count = StyleElastic.query.filter_by(style_id=style.id, is_deleted=0).count()

        if price_count > 0 or process_count > 0 or elastic_count > 0:
            return False, '请先删除款号关联的价格、工艺、松紧数据'

        style.is_deleted = 1
        style.save()
        return True, None

    @staticmethod
    def check_permission(current_user, current_factory_id, style):
        """校验款号数据是否属于当前访问范围。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_internal_user:
            return True, None
        if style.factory_id != current_factory_id:
            return False, '无权限操作'
        return True, None
