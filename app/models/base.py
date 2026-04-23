# 模型基类
from app.extensions import db
from datetime import datetime


class BaseModel(db.Model):
    """模型基类"""
    __abstract__ = True

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def to_dict_exclude(self, exclude_fields=None):
        if exclude_fields is None:
            exclude_fields = []
        data = self.to_dict()
        for field in exclude_fields:
            data.pop(field, None)
        return data

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        self.is_deleted = 1
        db.session.commit()
        return True

    def restore(self):
        self.is_deleted = 0
        db.session.commit()
        return True
