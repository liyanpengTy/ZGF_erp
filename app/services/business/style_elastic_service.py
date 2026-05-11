"""款号橡筋管理服务"""
from app.extensions import db
from app.models.base_data.size import Size
from app.models.business.style import Style
from app.models.business.style_elastic import StyleElastic
from app.services.base.base_service import BaseService


class StyleElasticService(BaseService):
    """款号橡筋管理服务"""

    @staticmethod
    def get_elastic_by_id(elastic_id):
        return StyleElastic.query.filter_by(id=elastic_id, is_deleted=0).first()

    @staticmethod
    def get_size_name(size_id):
        if size_id:
            size = Size.query.filter_by(id=size_id, is_deleted=0).first()
            return size.name if size else None
        return None

    @staticmethod
    def get_elastic_list(style_id, filters):
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        size_id = filters.get('size_id')

        query = StyleElastic.query.filter_by(style_id=style_id, is_deleted=0)
        if size_id:
            query = query.filter_by(size_id=size_id)

        pagination = query.order_by(StyleElastic.elastic_type, StyleElastic.size_id).paginate(
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
    def get_elastic_grouped(style_id):
        elastics = StyleElastic.query.filter_by(style_id=style_id, is_deleted=0).order_by(
            StyleElastic.elastic_type, StyleElastic.size_id
        ).all()
        if not elastics:
            return []

        grouped = {}
        for elastic in elastics:
            grouped.setdefault(elastic.elastic_type, {'elastic_type': elastic.elastic_type, 'details': []})
            grouped[elastic.elastic_type]['details'].append({
                'id': elastic.id,
                'size_id': elastic.size_id,
                'size_name': StyleElasticService.get_size_name(elastic.size_id),
                'length': float(elastic.elastic_length) if elastic.elastic_length else None,
                'quantity': elastic.quantity,
                'remark': elastic.remark,
            })

        return list(grouped.values())

    @staticmethod
    def create_elastic(data):
        elastic = StyleElastic(
            style_id=data['style_id'],
            size_id=data.get('size_id'),
            elastic_type=data['elastic_type'],
            elastic_length=data['elastic_length'],
            quantity=data.get('quantity', 1),
            remark=data.get('remark', ''),
        )
        elastic.save()
        return elastic

    @staticmethod
    def create_elastic_batch(style_id, items):
        created = []
        for item in items:
            for detail in item.get('details', []):
                elastic = StyleElastic(
                    style_id=style_id,
                    size_id=detail['size_id'],
                    elastic_type=item['elastic_type'],
                    elastic_length=detail['length'],
                    quantity=detail.get('quantity', 1),
                    remark=detail.get('remark', ''),
                )
                elastic.save()
                created.append(elastic)
        return created

    @staticmethod
    def update_elastic(elastic, data):
        if 'size_id' in data:
            elastic.size_id = data['size_id']
        if 'elastic_type' in data:
            elastic.elastic_type = data['elastic_type']
        if 'elastic_length' in data:
            elastic.elastic_length = data['elastic_length']
        if 'quantity' in data:
            elastic.quantity = data['quantity']
        if 'remark' in data:
            elastic.remark = data['remark']
        elastic.save()
        return elastic

    @staticmethod
    def delete_elastic(elastic):
        elastic.is_deleted = 1
        elastic.save()
        return True

    @staticmethod
    def delete_by_style_and_type(style_id, elastic_type):
        elastics = StyleElastic.query.filter_by(style_id=style_id, elastic_type=elastic_type, is_deleted=0).all()
        for elastic in elastics:
            elastic.is_deleted = 1
        db.session.commit()
        return len(elastics)

    @staticmethod
    def delete_by_style(style_id):
        elastics = StyleElastic.query.filter_by(style_id=style_id, is_deleted=0).all()
        for elastic in elastics:
            elastic.is_deleted = 1
        db.session.commit()
        return len(elastics)

    @staticmethod
    def check_style_permission(current_factory_id, style_id):
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        style = Style.query.filter_by(id=style_id, factory_id=current_factory_id, is_deleted=0).first()
        if not style:
            return None, '款号不存在或无权限'
        return style, None

    @staticmethod
    def check_elastic_permission(current_factory_id, elastic):
        if not current_factory_id:
            return False, '请先切换到工厂上下文'

        style = Style.query.filter_by(id=elastic.style_id, factory_id=current_factory_id, is_deleted=0).first()
        if not style:
            return False, '无权限操作'
        return True, None

    @staticmethod
    def validate_size(size_id):
        if size_id:
            size = Size.query.filter_by(id=size_id, is_deleted=0).first()
            if not size:
                return None, '尺码不存在'
            return size, None
        return None, None
