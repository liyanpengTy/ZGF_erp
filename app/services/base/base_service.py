"""基础服务类"""
from app.extensions import db


class BaseService:
    """服务基类，提供通用数据库操作方法"""

    @staticmethod
    def get_by_id(model, id):
        """根据ID获取对象（未删除）"""
        return model.query.filter_by(id=id, is_deleted=0).first()

    @staticmethod
    def get_one(model, **filters):
        """根据条件获取单个对象"""
        return model.query.filter_by(is_deleted=0, **filters).first()

    @staticmethod
    def get_all(model, **filters):
        """获取所有对象"""
        return model.query.filter_by(is_deleted=0, **filters).all()

    @staticmethod
    def paginate(query, page, page_size):
        """分页"""
        return query.paginate(page=page, per_page=page_size, error_out=False)

    @staticmethod
    def save(obj):
        """保存对象"""
        db.session.add(obj)
        db.session.commit()
        return obj

    @staticmethod
    def update(obj, **kwargs):
        """更新对象"""
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        db.session.commit()
        return obj

    @staticmethod
    def soft_delete(obj):
        """软删除"""
        obj.is_deleted = 1
        db.session.commit()
        return True

    @staticmethod
    def hard_delete(obj):
        """硬删除"""
        db.session.delete(obj)
        db.session.commit()
        return True
