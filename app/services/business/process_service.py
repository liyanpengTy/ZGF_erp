"""工序管理服务"""
from app.extensions import db
from app.models.business.process import Process, StyleProcessMapping
from app.models.business.style import Style
from app.services.base.base_service import BaseService


class ProcessService(BaseService):
    """工序管理服务"""

    # ========== 工序定义 CRUD ==========

    @staticmethod
    def get_process_by_id(process_id):
        """根据ID获取工序"""
        return Process.query.filter_by(id=process_id, is_deleted=0).first()

    @staticmethod
    def get_process_by_code(code):
        """根据编码获取工序"""
        return Process.query.filter_by(code=code, is_deleted=0).first()

    @staticmethod
    def get_process_list(filters):
        """获取工序列表"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        query = Process.query.filter_by(is_deleted=0)

        if name:
            query = query.filter(Process.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Process.sort_order).paginate(
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
    def get_all_enabled_processes():
        """获取所有启用的工序（用于下拉选择）"""
        return Process.query.filter_by(status=1, is_deleted=0).order_by(Process.sort_order).all()

    @staticmethod
    def create_process(data):
        """创建工序"""
        existing = ProcessService.get_process_by_code(data['code'])
        if existing:
            return None, '工序编码已存在'

        process = Process(
            name=data['name'],
            code=data['code'],
            description=data.get('description', ''),
            sort_order=data.get('sort_order', 0),
            status=1
        )
        process.save()
        return process, None

    @staticmethod
    def update_process(process, data):
        """更新工序"""
        if 'name' in data:
            process.name = data['name']
        if 'description' in data:
            process.description = data['description']
        if 'sort_order' in data:
            process.sort_order = data['sort_order']
        if 'status' in data:
            process.status = data['status']

        process.save()
        return process, None

    @staticmethod
    def delete_process(process):
        """删除工序（软删除）"""
        # 检查是否有款号引用该工序
        ref_count = StyleProcessMapping.query.filter_by(
            process_id=process.id, is_deleted=0
        ).count()
        if ref_count > 0:
            return False, f'有 {ref_count} 个款号引用此工序，无法删除'

        process.is_deleted = 1
        process.save()
        return True, None

    # ========== 款号工序关联 CRUD ==========

    @staticmethod
    def get_style_processes(style_id):
        """获取款号的工序列表"""
        mappings = StyleProcessMapping.query.filter_by(
            style_id=style_id, is_deleted=0
        ).order_by(StyleProcessMapping.sequence).all()
        return mappings

    @staticmethod
    def get_style_process_mapping_by_id(mapping_id):
        """根据ID获取款号工序关联"""
        return StyleProcessMapping.query.filter_by(id=mapping_id, is_deleted=0).first()

    @staticmethod
    def add_style_process(style_id, data):
        """为款号添加工序"""
        # 检查工序是否存在
        process = ProcessService.get_process_by_id(data['process_id'])
        if not process:
            return None, '工序不存在'

        # 检查是否已添加相同工序
        existing = StyleProcessMapping.query.filter_by(
            style_id=style_id, process_id=data['process_id'], is_deleted=0
        ).first()
        if existing:
            return None, '该款号已添加此工序'

        mapping = StyleProcessMapping(
            style_id=style_id,
            process_id=data['process_id'],
            sequence=data.get('sequence', 1),
            remark=data.get('remark', '')
        )
        mapping.save()
        return mapping, None

    @staticmethod
    def update_style_process(mapping, data):
        """更新款号工序"""
        if 'sequence' in data:
            mapping.sequence = data['sequence']
        if 'remark' in data:
            mapping.remark = data['remark']

        mapping.save()
        return mapping, None

    @staticmethod
    def delete_style_process(mapping):
        """删除款号工序"""
        mapping.is_deleted = 1
        mapping.save()
        return True, None

    @staticmethod
    def batch_save_style_processes(style_id, mappings_data):
        """批量保存款号工序（全量替换）"""
        # 删除原有工序
        StyleProcessMapping.query.filter_by(style_id=style_id, is_deleted=0).update(
            {'is_deleted': 1}
        )

        # 批量创建新工序
        created = []
        for idx, item in enumerate(mappings_data):
            # 验证工序是否存在
            process = ProcessService.get_process_by_id(item['process_id'])
            if not process:
                continue

            mapping = StyleProcessMapping(
                style_id=style_id,
                process_id=item['process_id'],
                sequence=item.get('sequence', idx + 1),
                remark=item.get('remark', '')
            )
            mapping.save()
            created.append(mapping)

        db.session.commit()
        return created

    @staticmethod
    def check_style_permission(current_user, style_id):
        """检查用户是否有权限操作该款号"""
        style = Style.query.filter_by(
            id=style_id, factory_id=current_user.factory_id, is_deleted=0
        ).first()

        if not style:
            return None, '款号不存在或无权限'

        return style, None
