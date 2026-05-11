"""工序管理服务"""
from app.extensions import db
from app.models.business.process import Process, StyleProcessMapping
from app.models.business.style import Style
from app.services.base.base_service import BaseService


class ProcessService(BaseService):
    """工序管理服务"""

    @staticmethod
    def get_process_by_id(process_id):
        return Process.query.filter_by(id=process_id, is_deleted=0).first()

    @staticmethod
    def get_process_by_code(code):
        return Process.query.filter_by(code=code, is_deleted=0).first()

    @staticmethod
    def get_process_list(filters):
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        query = Process.query.filter_by(is_deleted=0)
        if name:
            query = query.filter(Process.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Process.sort_order).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def get_all_enabled_processes():
        return Process.query.filter_by(status=1, is_deleted=0).order_by(Process.sort_order).all()

    @staticmethod
    def create_process(data):
        existing = ProcessService.get_process_by_code(data['code'])
        if existing:
            return None, '工序编码已存在'

        process = Process(
            name=data['name'],
            code=data['code'],
            description=data.get('description', ''),
            sort_order=data.get('sort_order', 0),
            status=1,
        )
        process.save()
        return process, None

    @staticmethod
    def update_process(process, data):
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
        ref_count = StyleProcessMapping.query.filter_by(process_id=process.id, is_deleted=0).count()
        if ref_count > 0:
            return False, f'有 {ref_count} 个款号引用此工序，无法删除'
        process.is_deleted = 1
        process.save()
        return True, None

    @staticmethod
    def get_style_processes(style_id):
        return StyleProcessMapping.query.filter_by(style_id=style_id, is_deleted=0).order_by(
            StyleProcessMapping.sequence
        ).all()

    @staticmethod
    def get_style_process_mapping_by_id(mapping_id):
        return StyleProcessMapping.query.filter_by(id=mapping_id, is_deleted=0).first()

    @staticmethod
    def add_style_process(style_id, data):
        process = ProcessService.get_process_by_id(data['process_id'])
        if not process:
            return None, '工序不存在'

        existing = StyleProcessMapping.query.filter_by(
            style_id=style_id, process_id=data['process_id'], is_deleted=0
        ).first()
        if existing:
            return None, '该款号已添加此工序'

        mapping = StyleProcessMapping(
            style_id=style_id,
            process_id=data['process_id'],
            sequence=data.get('sequence', 1),
            remark=data.get('remark', ''),
        )
        mapping.save()
        return mapping, None

    @staticmethod
    def update_style_process(mapping, data):
        if 'sequence' in data:
            mapping.sequence = data['sequence']
        if 'remark' in data:
            mapping.remark = data['remark']
        mapping.save()
        return mapping, None

    @staticmethod
    def delete_style_process(mapping):
        mapping.is_deleted = 1
        mapping.save()
        return True, None

    @staticmethod
    def batch_save_style_processes(style_id, mappings_data):
        try:
            StyleProcessMapping.query.filter_by(style_id=style_id, is_deleted=0).update({'is_deleted': 1})

            new_mappings = []
            for idx, item in enumerate(mappings_data):
                process = ProcessService.get_process_by_id(item['process_id'])
                if not process:
                    continue

                mapping = StyleProcessMapping(
                    style_id=style_id,
                    process_id=item['process_id'],
                    sequence=item.get('sequence', idx + 1),
                    remark=item.get('remark', ''),
                )
                new_mappings.append(mapping)

            if new_mappings:
                db.session.add_all(new_mappings)

            BaseService.commit()
            return new_mappings
        except Exception as exc:
            db.session.rollback()
            raise exc

    @staticmethod
    def check_style_permission(current_factory_id, style_id):
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        style = Style.query.filter_by(id=style_id, factory_id=current_factory_id, is_deleted=0).first()
        if not style:
            return None, '款号不存在或无权限'
        return style, None
