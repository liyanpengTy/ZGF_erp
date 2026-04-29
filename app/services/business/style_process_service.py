"""款号工艺管理服务"""
from app.extensions import db
from app.models.business.style import Style
from app.models.business.style_process import StyleProcess
from app.services.base.base_service import BaseService


class StyleProcessService(BaseService):
    """款号工艺管理服务"""

    # 工艺类型标签映射
    PROCESS_TYPE_LABELS = {
        'embroidery': '刺绣',
        'print': '印花',
        'other': '其他'
    }

    @staticmethod
    def get_process_by_id(process_id):
        """根据ID获取工艺记录"""
        return StyleProcess.query.filter_by(id=process_id, is_deleted=0).first()

    @staticmethod
    def get_process_label(process_type):
        """获取工艺类型标签"""
        return StyleProcessService.PROCESS_TYPE_LABELS.get(process_type, process_type)

    @staticmethod
    def get_process_list(style_id, filters):
        """
        获取工艺列表
        filters: page, page_size, process_type
        """
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        process_type = filters.get('process_type')

        query = StyleProcess.query.filter_by(style_id=style_id, is_deleted=0)

        if process_type:
            query = query.filter_by(process_type=process_type)

        pagination = query.order_by(StyleProcess.id.desc()).paginate(
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
    def create_process(data):
        """创建工艺记录"""
        process = StyleProcess(
            style_id=data['style_id'],
            process_type=data['process_type'],
            process_name=data.get('process_name', ''),
            remark=data.get('remark', '')
        )
        process.save()
        return process

    @staticmethod
    def update_process(process, data):
        """更新工艺记录"""
        if 'process_type' in data:
            process.process_type = data['process_type']
        if 'process_name' in data:
            process.process_name = data['process_name']
        if 'remark' in data:
            process.remark = data['remark']

        process.save()
        return process

    @staticmethod
    def delete_process(process):
        """删除工艺记录（软删除）"""
        process.is_deleted = 1
        process.save()
        return True

    @staticmethod
    def check_style_permission(current_user, style_id):
        """检查用户是否有权限操作该款号"""
        style = Style.query.filter_by(
            id=style_id, factory_id=current_user.factory_id, is_deleted=0
        ).first()

        if not style:
            return None, '款号不存在或无权限'

        return style, None

    @staticmethod
    def check_process_permission(current_user, process):
        """检查用户是否有权限操作该工艺记录"""
        style = Style.query.filter_by(
            id=process.style_id, factory_id=current_user.factory_id, is_deleted=0
        ).first()

        if not style:
            return False, '无权限操作'

        return True, None

    @staticmethod
    def enrich_with_label(process_data, process_obj):
        """为工艺数据添加类型标签"""
        process_data['process_type_label'] = StyleProcessService.get_process_label(process_obj.process_type)
        return process_data
