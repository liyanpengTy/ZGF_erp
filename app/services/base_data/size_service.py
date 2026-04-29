"""尺码管理服务"""
from app.extensions import db
from app.models.base_data.size import Size
from app.services.base.base_service import BaseService


class SizeService(BaseService):
    """尺码管理服务"""

    @staticmethod
    def get_size_by_id(size_id):
        """根据ID获取尺码"""
        return Size.query.filter_by(id=size_id, is_deleted=0).first()

    @staticmethod
    def get_size_by_code(factory_id, code):
        """根据工厂ID和编码获取尺码"""
        return Size.query.filter_by(
            factory_id=factory_id, code=code, is_deleted=0
        ).first()

    @staticmethod
    def get_size_list(current_user, filters):
        """
        获取尺码列表
        filters: page, page_size, name, status, factory_only
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')
        factory_only = filters.get('factory_only', 0)

        query = Size.query.filter_by(is_deleted=0)

        # 权限过滤
        if factory_only:
            query = query.filter(Size.factory_id == current_user.factory_id)
        else:
            query = query.filter(
                (Size.factory_id == 0) | (Size.factory_id == current_user.factory_id)
            )

        if name:
            query = query.filter(Size.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Size.sort_order).paginate(
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
    def create_size(current_user, data):
        """创建尺码"""
        # 检查编码是否已存在
        existing = SizeService.get_size_by_code(current_user.factory_id, data['code'])
        if existing:
            return None, '尺码编码已存在'

        size = Size(
            name=data['name'],
            code=data['code'],
            factory_id=current_user.factory_id,
            sort_order=data.get('sort_order', 0),
            status=1
        )
        size.save()

        return size, None

    @staticmethod
    def update_size(size, data):
        """更新尺码"""
        if 'name' in data:
            size.name = data['name']
        if 'sort_order' in data:
            size.sort_order = data['sort_order']
        if 'status' in data:
            size.status = data['status']

        size.save()
        return size, None

    @staticmethod
    def delete_size(size):
        """删除尺码（软删除）"""
        size.is_deleted = 1
        size.save()
        return True, None

    @staticmethod
    def check_permission(current_user, size):
        """检查用户是否有权限操作该尺码"""
        if not current_user:
            return False, '用户不存在'

        if current_user.is_admin == 1:
            return True, None

        if size.factory_id != 0 and size.factory_id != current_user.factory_id:
            return False, '无权限操作'

        return True, None
