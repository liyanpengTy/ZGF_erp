"""分类管理服务。"""

from app.models.base_data.category import Category
from app.services.base.base_service import BaseService


class CategoryService(BaseService):
    """分类管理服务。"""

    @staticmethod
    def get_category_by_id(category_id):
        """根据 ID 获取分类。"""
        return Category.query.filter_by(id=category_id, is_deleted=0).first()

    @staticmethod
    def get_category_by_code(factory_id, code):
        """根据工厂和编码获取分类。"""
        return Category.query.filter_by(factory_id=factory_id, code=code, is_deleted=0).first()

    @staticmethod
    def get_category_list(current_user, current_factory_id, filters):
        """分页查询分类列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        parent_id = filters.get('parent_id')
        status = filters.get('status')
        factory_only = filters.get('factory_only', 0)
        category_type = filters.get('category_type')

        query = Category.query.filter_by(is_deleted=0)
        if factory_only:
            query = query.filter(Category.factory_id == (current_factory_id or -1))
        elif current_factory_id:
            query = query.filter((Category.factory_id == 0) | (Category.factory_id == current_factory_id))
        else:
            query = query.filter(Category.factory_id == 0)

        if name:
            query = query.filter(Category.name.like(f'%{name}%'))
        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)
        if status is not None:
            query = query.filter_by(status=status)
        if category_type:
            query = query.filter_by(category_type=category_type)

        pagination = query.order_by(Category.sort_order).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def get_category_tree(current_user, current_factory_id, category_type=None):
        """查询分类树。"""
        query = Category.query.filter_by(is_deleted=0)
        if current_factory_id:
            query = query.filter((Category.factory_id == 0) | (Category.factory_id == current_factory_id))
        else:
            query = query.filter(Category.factory_id == 0)

        if category_type:
            query = query.filter_by(category_type=category_type)

        categories = query.order_by(Category.sort_order).all()
        return CategoryService.build_tree(categories)

    @staticmethod
    def build_tree(categories, parent_id=0):
        """将平铺分类转换为树形结构。"""
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                children = CategoryService.build_tree(categories, category.id)
                category_dict = {
                    'id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id,
                    'code': category.code,
                    'category_type': category.category_type,
                    'factory_id': category.factory_id,
                    'sort_order': category.sort_order,
                    'status': category.status,
                    'remark': category.remark,
                    'create_time': category.create_time.isoformat() if category.create_time else None,
                    'update_time': category.update_time.isoformat() if category.update_time else None,
                }
                if children:
                    category_dict['children'] = children
                tree.append(category_dict)
        return tree

    @staticmethod
    def create_category(current_user, current_factory_id, data):
        """在当前工厂上下文中创建分类。"""
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        existing = CategoryService.get_category_by_code(current_factory_id, data['code'])
        if existing:
            return None, '分类编码已存在'

        if data.get('parent_id', 0) != 0:
            parent = CategoryService.get_category_by_id(data['parent_id'])
            if not parent:
                return None, '父分类不存在'

        category = Category(
            name=data['name'],
            parent_id=data.get('parent_id', 0),
            code=data['code'],
            category_type=data.get('category_type', 'style'),
            factory_id=current_factory_id,
            sort_order=data.get('sort_order', 0),
            status=1,
            remark=data.get('remark', ''),
        )
        category.save()
        return category, None

    @staticmethod
    def update_category(category, data):
        """更新分类资料。"""
        if 'name' in data:
            category.name = data['name']
        if 'parent_id' in data:
            if data['parent_id'] == category.id:
                return None, '不能将父分类设为自己'
            category.parent_id = data['parent_id']
        if 'category_type' in data:
            category.category_type = data['category_type']
        if 'sort_order' in data:
            category.sort_order = data['sort_order']
        if 'status' in data:
            category.status = data['status']
        if 'remark' in data:
            category.remark = data['remark']
        category.save()
        return category, None

    @staticmethod
    def delete_category(category):
        """删除分类前校验是否存在子分类。"""
        children_count = Category.query.filter_by(parent_id=category.id, is_deleted=0).count()
        if children_count > 0:
            return False, '请先删除子分类'
        category.is_deleted = 1
        category.save()
        return True, None

    @staticmethod
    def check_permission(current_user, current_factory_id, category):
        """校验分类数据是否可被当前用户访问。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_internal_user:
            return True, None
        if category.factory_id != 0 and category.factory_id != current_factory_id:
            return False, '无权限操作'
        return True, None
