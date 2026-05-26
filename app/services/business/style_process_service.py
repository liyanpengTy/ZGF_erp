"""款号工艺管理服务。"""

from app.models.business.style_process import StyleProcess
from app.services.base.base_service import BaseService
from app.services.business.style_service import StyleService


class StyleProcessService(BaseService):
    """封装款号工艺记录的查询与维护逻辑。"""

    PROCESS_TYPE_LABELS = {
        'embroidery': '刺绣',
        'print': '印花',
        'other': '其他',
    }

    @staticmethod
    def get_process_by_id(process_id):
        """根据工艺记录 ID 查询详情。"""
        return StyleProcess.query.filter_by(id=process_id, is_deleted=0).first()

    @staticmethod
    def get_process_label(process_type):
        """返回工艺类型的中文名称。"""
        return StyleProcessService.PROCESS_TYPE_LABELS.get(process_type, process_type)

    @staticmethod
    def get_process_list(style_id, filters):
        """分页查询指定款号下的工艺记录。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        process_type = filters.get('process_type')

        query = StyleProcess.query.filter_by(style_id=style_id, is_deleted=0)
        if process_type:
            query = query.filter_by(process_type=process_type)

        pagination = query.order_by(StyleProcess.id.desc()).paginate(
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
    def create_process(data):
        """创建款号工艺记录。"""
        process = StyleProcess(
            style_id=data['style_id'],
            process_type=data['process_type'],
            process_name=data.get('process_name', ''),
            remark=data.get('remark', ''),
        )
        process.save()
        return process

    @staticmethod
    def update_process(process, data):
        """更新款号工艺记录。"""
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
        """逻辑删除工艺记录。"""
        process.is_deleted = 1
        process.save()
        return True

    @staticmethod
    def check_style_permission(current_user, current_factory_id, style_id):
        """校验当前用户是否可以访问指定款号。"""
        return StyleService.get_accessible_style(current_user, current_factory_id, style_id)

    @staticmethod
    def check_process_permission(current_user, current_factory_id, process):
        """校验当前用户是否可以访问指定工艺记录。"""
        style, error = StyleService.get_accessible_style(current_user, current_factory_id, process.style_id)
        if error or not style:
            return False, error or '无权限操作'
        return True, None

    @staticmethod
    def enrich_with_label(process_data, process_obj):
        """为工艺响应补充工艺类型中文名称。"""
        process_data['process_type_label'] = StyleProcessService.get_process_label(process_obj.process_type)
        return process_data
