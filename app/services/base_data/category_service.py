"""分类管理服务"""
from app.extensions import db
from app.models.base_data.category import Category
from app.services.base.base_service import BaseService


class CategoryService(BaseService):
    """分类管理服务"""

    @staticmethod
    def get_category_by_id(category_id):
        """根据ID获取分类"""
        return Category.query.filter_by(id=category_id, is_deleted=0).first()

    @staticmethod
    def get_category_by_code(factory_id, code):
        """根据工厂ID和编码获取分类"""
        return Category.query.filter_by(
            factory_id=factory_id, code=code, is_deleted=0
        ).first()

    @staticmethod
    def get_category_list(current_user, filters):
        """
        获取分类列表
        filters: page, page_size, name, parent_id, status, factory_only
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        parent_id = filters.get('parent_id')
        status = filters.get('status')
        factory_only = filters.get('factory_only', 0)

        query = Category.query.filter_by(is_deleted=0)

        # 权限过滤
        if factory_only:
            query = query.filter(Category.factory_id == current_user.factory_id)
        else:
            query = query.filter(
                (Category.factory_id == 0) | (Category.factory_id == current_user.factory_id)
            )

        if name:
            query = query.filter(Category.name.like(f'%{name}%'))
        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Category.sort_order).paginate(
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
    def get_category_tree(current_user, category_type=None):
        """获取分类树"""
        from app.schemas.base_data.category import CategorySchema

        query = Category.query.filter_by(is_deleted=0).filter(
            (Category.factory_id == 0) | (Category.factory_id == current_user.factory_id)
        )

        if category_type:
            query = query.filter_by(category_type=category_type)

        categories = query.order_by(Category.sort_order).all()
        tree = CategoryService.build_tree(categories)

        return CategorySchema(many=True).dump(tree)

    @staticmethod
    def build_tree(categories, parent_id=0):
        """构建分类树（返回原始对象）"""
        tree = []
        for cat in categories:
            if cat.parent_id == parent_id:
                children = CategoryService.build_tree(categories, cat.id)
                cat_dict = {
                    'id': cat.id,
                    'name': cat.name,
                    'parent_id': cat.parent_id,
                    'code': cat.code,
                    'category_type': cat.category_type,
                    'factory_id': cat.factory_id,
                    'sort_order': cat.sort_order,
                    'status': cat.status,
                    'remark': cat.remark,
                    'create_time': cat.create_time.isoformat() if cat.create_time else None,
                    'update_time': cat.update_time.isoformat() if cat.update_time else None
                }
                if children:
                    cat_dict['children'] = children
                tree.append(cat_dict)
        return tree

    @staticmethod
    def create_category(current_user, data):
        """创建分类"""
        # 检查编码是否已存在
        existing = CategoryService.get_category_by_code(current_user.factory_id, data['code'])
        if existing:
            return None, '分类编码已存在'

        # 验证父分类
        if data.get('parent_id', 0) != 0:
            parent = CategoryService.get_category_by_id(data['parent_id'])
            if not parent:
                return None, '父分类不存在'

        category = Category(
            name=data['name'],
            parent_id=data.get('parent_id', 0),
            code=data['code'],
            factory_id=current_user.factory_id,
            sort_order=data.get('sort_order', 0),
            status=1
        )
        category.save()

        return category, None

    @staticmethod
    def update_category(category, data):
        """更新分类"""
        if 'name' in data:
            category.name = data['name']
        if 'parent_id' in data:
            if data['parent_id'] == category.id:
                return None, '不能将父分类设为自己'
            category.parent_id = data['parent_id']
        if 'sort_order' in data:
            category.sort_order = data['sort_order']
        if 'status' in data:
            category.status = data['status']

        category.save()
        return category, None

    @staticmethod
    def delete_category(category):
        """删除分类（软删除）"""
        # 检查是否有子分类
        children_count = Category.query.filter_by(
            parent_id=category.id, is_deleted=0
        ).count()
        if children_count > 0:
            return False, '请先删除子分类'

        category.is_deleted = 1
        category.save()
        return True, None

    @staticmethod
    def check_permission(current_user, category):
        """检查用户是否有权限操作该分类"""
        if not current_user:
            return False, '用户不存在'

        if current_user.is_admin == 1:
            return True, None

        if category.factory_id != 0 and category.factory_id != current_user.factory_id:
            return False, '无权限操作'

        return True, None
