"""尺码管理服务。"""

from app.models.base_data.size import Size
from app.services.base.base_service import BaseService


class SizeService(BaseService):
    """尺码管理服务。"""

    @staticmethod
    def get_size_by_id(size_id):
        """根据 ID 获取尺码。"""
        return Size.query.filter_by(id=size_id, is_deleted=0).first()

    @staticmethod
    def get_size_by_code(factory_id, code):
        """根据工厂和编码获取尺码。"""
        return Size.query.filter_by(factory_id=factory_id, code=code, is_deleted=0).first()

    @staticmethod
    def get_size_list(current_user, current_factory_id, filters):
        """分页查询尺码列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')
        factory_only = filters.get('factory_only', 0)

        query = Size.query.filter_by(is_deleted=0)
        if factory_only:
            query = query.filter(Size.factory_id == (current_factory_id or -1))
        elif current_factory_id:
            query = query.filter((Size.factory_id == 0) | (Size.factory_id == current_factory_id))
        else:
            query = query.filter(Size.factory_id == 0)

        if name:
            query = query.filter(Size.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Size.sort_order).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def create_size(current_user, current_factory_id, data):
        """在当前工厂上下文中创建尺码。"""
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        existing = SizeService.get_size_by_code(current_factory_id, data['code'])
        if existing:
            return None, '尺码编码已存在'

        size = Size(
            name=data['name'],
            code=data['code'],
            factory_id=current_factory_id,
            sort_order=data.get('sort_order', 0),
            status=1,
        )
        size.save()
        return size, None

    @staticmethod
    def update_size(size, data):
        """更新尺码资料。"""
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
        """软删除尺码。"""
        size.is_deleted = 1
        size.save()
        return True, None

    @staticmethod
    def check_permission(current_user, current_factory_id, size):
        """校验尺码数据是否可被当前用户访问。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_internal_user:
            return True, None
        if size.factory_id != 0 and size.factory_id != current_factory_id:
            return False, '无权限操作'
        return True, None
    @staticmethod
    def check_manage_permission(current_user, current_factory_id, size):
        """校验当前用户是否可以维护尺码，外部用户仅允许维护当前工厂自定义尺码。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_internal_user:
            return True, None
        if not current_factory_id:
            return False, '当前登录态缺少工厂上下文，请先切换工厂'
        if size.factory_id == 0:
            return False, '无权修改系统公共尺码'
        if size.factory_id != current_factory_id:
            return False, '只能修改自己工厂的尺码'
        return True, None
