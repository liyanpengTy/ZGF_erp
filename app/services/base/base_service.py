"""基础服务类。"""
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
    def add(obj):
        """添加对象（不提交，用于批量操作）"""
        db.session.add(obj)
        return obj

    @staticmethod
    def add_all(objs):
        """批量添加对象（不提交）"""
        db.session.add_all(objs)
        return objs

    @staticmethod
    def commit():
        """提交事务"""
        db.session.commit()

    @staticmethod
    def rollback():
        """回滚事务"""
        db.session.rollback()

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
    def build_factory_scope_query(query, model, current_user, current_factory_id=None, factory_only=0):
        """按当前用户与工厂上下文统一构造工厂维度查询范围。"""
        if factory_only:
            if current_factory_id:
                return query.filter(model.factory_id == current_factory_id)
            if current_user and current_user.is_internal_user:
                return query.filter(model.factory_id != 0)
            return query.filter(model.factory_id == -1)

        if current_factory_id:
            return query.filter((model.factory_id == 0) | (model.factory_id == current_factory_id))

        if current_user and current_user.is_internal_user:
            return query

        return query.filter(model.factory_id == 0)

    @staticmethod
    def hard_delete(obj):
        """硬删除"""
        db.session.delete(obj)
        db.session.commit()
        return True
