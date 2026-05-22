"""模型基类定义。"""

from datetime import datetime

from flask import has_request_context
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import event

from app.extensions import db


class BaseModel(db.Model):
    """提供通用字典导出与保存能力的抽象模型基类。"""

    __abstract__ = True

    def to_dict(self):
        """把当前模型实例导出为字典。"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def to_dict_exclude(self, exclude_fields=None):
        """导出字典并排除指定字段。"""
        exclude_fields = exclude_fields or []
        data = self.to_dict()
        for field in exclude_fields:
            data.pop(field, None)
        return data

    def save(self):
        """保存当前模型实例。"""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """逻辑删除当前模型实例。"""
        self.is_deleted = 1
        db.session.commit()
        return True

    def restore(self):
        """恢复被逻辑删除的数据。"""
        self.is_deleted = 0
        db.session.commit()
        return True


def get_request_user_id():
    """从当前请求上下文提取登录用户 ID；无上下文时返回 ``None``。"""
    if not has_request_context():
        return None

    try:
        identity = get_jwt_identity()
    except Exception:
        return None

    if isinstance(identity, dict):
        return identity.get('user_id')

    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


def apply_audit_fields(target, is_insert=False):
    """为带审计字段的模型自动填充创建人与更新人。"""
    user_id = get_request_user_id()
    if not user_id:
        return

    if hasattr(target, 'update_by'):
        target.update_by = user_id
    if is_insert and hasattr(target, 'create_by') and not getattr(target, 'create_by', None):
        target.create_by = user_id
    if is_insert and hasattr(target, 'created_by') and not getattr(target, 'created_by', None):
        target.created_by = user_id


@event.listens_for(BaseModel, 'before_insert', propagate=True)
def before_insert_fill_audit_fields(mapper, connection, target):
    """在插入前自动补齐审计字段。"""
    apply_audit_fields(target, is_insert=True)


@event.listens_for(BaseModel, 'before_update', propagate=True)
def before_update_fill_audit_fields(mapper, connection, target):
    """在更新前自动补齐更新人字段。"""
    apply_audit_fields(target, is_insert=False)
