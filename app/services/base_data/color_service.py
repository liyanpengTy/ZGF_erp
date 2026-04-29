"""颜色管理服务"""
from app.extensions import db
from app.models.base_data.color import Color
from app.services.base.base_service import BaseService


class ColorService(BaseService):
    """颜色管理服务"""

    @staticmethod
    def get_color_by_id(color_id):
        """根据ID获取颜色"""
        return Color.query.filter_by(id=color_id, is_deleted=0).first()

    @staticmethod
    def get_color_by_code(factory_id, code):
        """根据工厂ID和编码获取颜色"""
        return Color.query.filter_by(
            factory_id=factory_id, code=code, is_deleted=0
        ).first()

    @staticmethod
    def get_color_list(current_user, filters):
        """
        获取颜色列表
        filters: page, page_size, name, actual_name, status, factory_only
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        actual_name = filters.get('actual_name', '')
        status = filters.get('status')
        factory_only = filters.get('factory_only', 0)

        query = Color.query.filter_by(is_deleted=0)

        # 权限过滤
        if factory_only:
            query = query.filter(Color.factory_id == current_user.factory_id)
        else:
            query = query.filter(
                (Color.factory_id == 0) | (Color.factory_id == current_user.factory_id)
            )

        if name:
            query = query.filter(Color.name.like(f'%{name}%'))
        if actual_name:
            query = query.filter(Color.actual_name.like(f'%{actual_name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Color.sort_order).paginate(
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
    def create_color(current_user, data):
        """创建颜色"""
        # 检查编码是否已存在
        existing = ColorService.get_color_by_code(current_user.factory_id, data['code'])
        if existing:
            return None, '颜色编码已存在'

        color = Color(
            name=data['name'],
            actual_name=data['actual_name'],
            code=data['code'],
            factory_id=current_user.factory_id,
            sort_order=data.get('sort_order', 0),
            status=1,
            remark=data.get('remark', '')
        )
        color.save()

        return color, None

    @staticmethod
    def update_color(color, data):
        """更新颜色"""
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
        """删除颜色（软删除）"""
        color.is_deleted = 1
        color.save()
        return True, None

    @staticmethod
    def check_permission(current_user, color):
        """检查用户是否有权限操作该颜色"""
        if not current_user:
            return False, '用户不存在'

        if current_user.is_admin == 1:
            return True, None

        if color.factory_id != 0 and color.factory_id != current_user.factory_id:
            return False, '无权限操作'

        return True, None
