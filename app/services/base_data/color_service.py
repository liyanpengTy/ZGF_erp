"""颜色管理服务。"""

from app.models.base_data.color import Color
from app.services.base.base_service import BaseService


class ColorService(BaseService):
    """颜色管理服务。"""

    @staticmethod
    def get_color_by_id(color_id):
        """根据 ID 获取颜色。"""
        return Color.query.filter_by(id=color_id, is_deleted=0).first()

    @staticmethod
    def get_color_by_code(factory_id, code):
        """根据工厂和编码获取颜色。"""
        return Color.query.filter_by(factory_id=factory_id, code=code, is_deleted=0).first()

    @staticmethod
    def get_color_list(current_user, current_factory_id, filters):
        """分页查询颜色列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        actual_name = filters.get('actual_name', '')
        status = filters.get('status')
        factory_only = filters.get('factory_only', 0)

        query = Color.query.filter_by(is_deleted=0)
        if factory_only:
            query = query.filter(Color.factory_id == (current_factory_id or -1))
        elif current_factory_id:
            query = query.filter((Color.factory_id == 0) | (Color.factory_id == current_factory_id))
        else:
            query = query.filter(Color.factory_id == 0)

        if name:
            query = query.filter(Color.name.like(f'%{name}%'))
        if actual_name:
            query = query.filter(Color.actual_name.like(f'%{actual_name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Color.sort_order).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def create_color(current_user, current_factory_id, data):
        """在当前工厂上下文中创建颜色。"""
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        existing = ColorService.get_color_by_code(current_factory_id, data['code'])
        if existing:
            return None, '颜色编码已存在'

        color = Color(
            name=data['name'],
            actual_name=data['actual_name'],
            code=data['code'],
            factory_id=current_factory_id,
            sort_order=data.get('sort_order', 0),
            status=1,
            remark=data.get('remark', ''),
        )
        color.save()
        return color, None

    @staticmethod
    def update_color(color, data):
        """更新颜色资料。"""
        if 'name' in data:
            color.name = data['name']
        if 'actual_name' in data:
            color.actual_name = data['actual_name']
        if 'sort_order' in data:
            color.sort_order = data['sort_order']
        if 'status' in data:
            color.status = data['status']
        if 'remark' in data:
            color.remark = data['remark']
        color.save()
        return color, None

    @staticmethod
    def delete_color(color):
        """软删除颜色。"""
        color.is_deleted = 1
        color.save()
        return True, None

    @staticmethod
    def check_permission(current_user, current_factory_id, color):
        """校验颜色数据是否可被当前用户访问。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_internal_user:
            return True, None
        if color.factory_id != 0 and color.factory_id != current_factory_id:
            return False, '无权限操作'
        return True, None
