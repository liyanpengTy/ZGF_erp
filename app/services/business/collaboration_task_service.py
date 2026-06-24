"""主体协作任务服务。"""

from datetime import datetime

from sqlalchemy import or_

from app.constants.identity import (
    COLLABORATION_STATUS_ACCEPTED,
    COLLABORATION_STATUS_COMPLETED,
    COLLABORATION_STATUS_IN_PROGRESS,
    COLLABORATION_STATUS_PENDING,
)
from app.models.business.collaboration_task import CollaborationTask
from app.models.business.order import Order
from app.models.system.factory import Factory


class CollaborationTaskService:
    """封装主体间协作任务的创建、查询和状态流转。"""

    VALID_STATUSES = {
        COLLABORATION_STATUS_PENDING,
        COLLABORATION_STATUS_ACCEPTED,
        COLLABORATION_STATUS_IN_PROGRESS,
        COLLABORATION_STATUS_COMPLETED,
    }

    @staticmethod
    def serialize_task(task):
        """序列化协作任务基础信息。"""
        data = task.to_safe_dict()
        data.update({
            'from_subject_name': task.from_subject.name if task.from_subject else None,
            'to_subject_name': task.to_subject.name if task.to_subject else None,
            'source_order_no': task.source_order.order_no if task.source_order else None,
        })
        return data

    @staticmethod
    def _build_access_query(current_user, current_subject_id=None, filters=None):
        """构建协作任务查询对象，并按当前主体上下文做数据隔离。"""
        filters = filters or {}
        query = CollaborationTask.query.filter_by(is_deleted=0)
        direction = filters.get('direction') or 'all'

        if current_user.is_internal_user and not current_subject_id:
            pass
        elif current_subject_id:
            if direction == 'inbound':
                query = query.filter(CollaborationTask.to_subject_id == current_subject_id)
            elif direction == 'outbound':
                query = query.filter(CollaborationTask.from_subject_id == current_subject_id)
            else:
                query = query.filter(or_(
                    CollaborationTask.from_subject_id == current_subject_id,
                    CollaborationTask.to_subject_id == current_subject_id,
                ))
        else:
            return None

        status = filters.get('status')
        if status:
            query = query.filter(CollaborationTask.status == status)

        source_order_id = filters.get('source_order_id')
        if source_order_id:
            query = query.filter(CollaborationTask.source_order_id == source_order_id)

        return query

    @staticmethod
    def get_task_list(current_user, current_subject_id, filters):
        """分页查询当前主体可见的协作任务。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        query = CollaborationTaskService._build_access_query(current_user, current_subject_id, filters)
        if query is None:
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

        pagination = query.order_by(CollaborationTask.id.desc()).paginate(
            page=page,
            per_page=page_size,
            error_out=False,
        )
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def get_accessible_task(current_user, current_subject_id, task_id):
        """查询当前主体可访问的协作任务。"""
        query = CollaborationTaskService._build_access_query(current_user, current_subject_id)
        if query is None:
            return None
        return query.filter(CollaborationTask.id == task_id).first()

    @staticmethod
    def create_task(current_user, current_subject_id, data):
        """创建协作任务，发起主体必须拥有原始订单。"""
        if not current_subject_id:
            return None, '请先选择发起主体'

        to_subject = Factory.query.filter_by(id=data['to_subject_id'], is_deleted=0).first()
        if not to_subject:
            return None, '接收主体不存在'
        if data['to_subject_id'] == current_subject_id:
            return None, '接收主体不能与发起主体相同'

        source_order = Order.query.filter(
            Order.id == data['source_order_id'],
            Order.is_deleted == 0,
            or_(Order.subject_id == current_subject_id, Order.factory_id == current_subject_id),
        ).first()
        if not source_order:
            return None, '原始订单不存在或不属于当前主体'

        deliver_at = None
        if data.get('deliver_at'):
            deliver_at = datetime.strptime(data['deliver_at'], '%Y-%m-%d %H:%M:%S')

        task = CollaborationTask(
            from_subject_id=current_subject_id,
            to_subject_id=data['to_subject_id'],
            source_order_id=data['source_order_id'],
            process_name=data['process_name'],
            quantity=data['quantity'],
            deliver_at=deliver_at,
            status=COLLABORATION_STATUS_PENDING,
            remark=data.get('remark', ''),
            create_by=current_user.id,
        )
        task.save()
        return task, None

    @staticmethod
    def update_task_status(task, status):
        """手动更新协作任务状态。"""
        if status not in CollaborationTaskService.VALID_STATUSES:
            return None, '协作任务状态不正确'
        task.status = status
        task.save()
        return task, None

    @staticmethod
    def delete_task(task):
        """逻辑删除协作任务。"""
        task.is_deleted = 1
        task.save()
        return True
