"""款号橡筋管理服务"""
from app.extensions import db
from app.models.business.style import Style
from app.models.business.style_elastic import StyleElastic
from app.models.base_data.size import Size
from app.services.base.base_service import BaseService


class StyleElasticService(BaseService):
    """款号橡筋管理服务"""

    @staticmethod
    def get_elastic_by_id(elastic_id):
        """根据ID获取橡筋记录"""
        return StyleElastic.query.filter_by(id=elastic_id, is_deleted=0).first()

    @staticmethod
    def get_size_name(size_id):
        """获取尺码名称"""
        if size_id:
            size = Size.query.filter_by(id=size_id, is_deleted=0).first()
            return size.name if size else None
        return None

    @staticmethod
    def get_elastic_list(style_id, filters):
        """
        获取橡筋列表
        filters: page, page_size, size_id
        """
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
            'pages': pagination.pages
        }

    @staticmethod
    def get_elastic_grouped(style_id):
        """
        按橡筋种类分组获取橡筋需求（前端展示用）
        返回格式:
        [
            {
                "elastic_type": "2cm宽橡筋",
                "details": [
                    {"size_id": 1, "size_name": "M", "length": 24, "quantity": 2, "id": 1},
                    {"size_id": 2, "size_name": "L", "length": 26, "quantity": 2, "id": 2}
                ]
            }
        ]
        """
        elastics = StyleElastic.query.filter_by(
            style_id=style_id, is_deleted=0
        ).order_by(StyleElastic.elastic_type, StyleElastic.size_id).all()

        if not elastics:
            return []

        grouped = {}
        for elastic in elastics:
            if elastic.elastic_type not in grouped:
                grouped[elastic.elastic_type] = {
                    'elastic_type': elastic.elastic_type,
                    'details': []
                }
            grouped[elastic.elastic_type]['details'].append({
                'id': elastic.id,
                'size_id': elastic.size_id,
                'size_name': StyleElasticService.get_size_name(elastic.size_id),
                'length': float(elastic.elastic_length) if elastic.elastic_length else None,
                'quantity': elastic.quantity,
                'remark': elastic.remark
            })

        return list(grouped.values())

    @staticmethod
    def create_elastic(data):
        """创建单条橡筋记录"""
        elastic = StyleElastic(
            style_id=data['style_id'],
            size_id=data.get('size_id'),
            elastic_type=data['elastic_type'],
            elastic_length=data['elastic_length'],
            quantity=data.get('quantity', 1),
            remark=data.get('remark', '')
        )
        elastic.save()
        return elastic

    @staticmethod
    def create_elastic_batch(style_id, items):
        """
        批量创建橡筋记录
        items 格式:
        [
            {
                "elastic_type": "2cm宽橡筋",
                "details": [
                    {"size_id": 1, "length": 24, "quantity": 2},
                    {"size_id": 2, "length": 26, "quantity": 2}
                ]
            }
        ]
        """
        created = []
        for item in items:
            for detail in item.get('details', []):
                elastic = StyleElastic(
                    style_id=style_id,
                    size_id=detail['size_id'],
                    elastic_type=item['elastic_type'],
                    elastic_length=detail['length'],
                    quantity=detail.get('quantity', 1),
                    remark=detail.get('remark', '')
                )
                elastic.save()
                created.append(elastic)
        return created

    @staticmethod
    def update_elastic(elastic, data):
        """更新单条橡筋记录"""
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
        """删除单条橡筋记录（软删除）"""
        elastic.is_deleted = 1
        elastic.save()
        return True

    @staticmethod
    def delete_by_style_and_type(style_id, elastic_type):
        """删除款号下指定种类的所有橡筋记录"""
        elastics = StyleElastic.query.filter_by(
            style_id=style_id, elastic_type=elastic_type, is_deleted=0
        ).all()
        for elastic in elastics:
            elastic.is_deleted = 1
        db.session.commit()
        return len(elastics)

    @staticmethod
    def delete_by_style(style_id):
        """删除款号下所有橡筋记录"""
        elastics = StyleElastic.query.filter_by(style_id=style_id, is_deleted=0).all()
        for elastic in elastics:
            elastic.is_deleted = 1
        db.session.commit()
        return len(elastics)

    @staticmethod
    def check_style_permission(current_user, style_id):
        """检查用户是否有权限操作该款号"""
        style = Style.query.filter_by(
            id=style_id, factory_id=current_user.factory_id, is_deleted=0
        ).first()

        if not style:
            return None, '款号不存在或无权限'

        return style, None

    @staticmethod
    def check_elastic_permission(current_user, elastic):
        """检查用户是否有权限操作该橡筋记录"""
        style = Style.query.filter_by(
            id=elastic.style_id, factory_id=current_user.factory_id, is_deleted=0
        ).first()

        if not style:
            return False, '无权限操作'

        return True, None

    @staticmethod
    def validate_size(size_id):
        """验证尺码是否存在"""
        if size_id:
            size = Size.query.filter_by(id=size_id, is_deleted=0).first()
            if not size:
                return None, '尺码不存在'
            return size, None
        return None, None
