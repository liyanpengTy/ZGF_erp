"""工序主数据与款号工序映射服务。"""

from app.extensions import db
from app.models.business.process import Process, StyleProcessMapping
from app.models.business.style import Style
from app.services.base.base_service import BaseService


class ProcessService(BaseService):
    """封装工序主数据与款号工序映射的业务逻辑。"""

    @staticmethod
    def get_process_by_id(process_id):
        """根据工序 ID 查询工序详情。"""
        return Process.query.filter_by(id=process_id, is_deleted=0).first()

    @staticmethod
    def get_process_by_code(code):
        """根据工序编码查询工序。"""
        return Process.query.filter_by(code=code, is_deleted=0).first()

    @staticmethod
    def _build_process_query():
        """构建工序查询对象，统一过滤软删除数据。"""
        return Process.query.filter_by(is_deleted=0)

    @staticmethod
    def get_process_list(filters):
        """分页查询工序主数据列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        name = filters.get('name', '')
        status = filters.get('status')

        query = ProcessService._build_process_query()
        if name:
            query = query.filter(Process.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)

        pagination = query.order_by(Process.sort_order, Process.id).paginate(
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
    def get_all_enabled_processes():
        """查询全部启用中的工序。"""
        return ProcessService._build_process_query().filter_by(status=1).order_by(Process.sort_order, Process.id).all()

    @staticmethod
    def get_process_options(filters):
        """查询工序轻量选项列表。"""
        name = filters.get('name', '')
        status = filters.get('status')

        query = ProcessService._build_process_query()
        if name:
            query = query.filter(Process.name.like(f'%{name}%'))
        if status is not None:
            query = query.filter_by(status=status)
        return query.order_by(Process.sort_order, Process.id).all()

    @staticmethod
    def create_process(data):
        """创建工序主数据。"""
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
        """更新工序主数据。"""
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
        """删除工序前先校验是否仍被款号工序映射引用。"""
        ref_count = StyleProcessMapping.query.filter_by(process_id=process.id, is_deleted=0).count()
        if ref_count > 0:
            return False, f'当前有 {ref_count} 个款号引用该工序，无法删除'
        process.is_deleted = 1
        process.save()
        return True, None

    @staticmethod
    def get_style_processes(style_id):
        """查询指定款号的工序映射列表。"""
        return StyleProcessMapping.query.filter_by(style_id=style_id, is_deleted=0).order_by(
            StyleProcessMapping.sequence,
        ).all()

    @staticmethod
    def get_style_process_mapping_by_id(mapping_id):
        """根据映射 ID 查询款号工序映射。"""
        return StyleProcessMapping.query.filter_by(id=mapping_id, is_deleted=0).first()

    @staticmethod
    def add_style_process(style_id, data):
        """新增单条款号工序映射。"""
        process = ProcessService.get_process_by_id(data['process_id'])
        if not process:
            return None, '工序不存在'

        existing = StyleProcessMapping.query.filter_by(
            style_id=style_id,
            process_id=data['process_id'],
            is_deleted=0,
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
        """更新款号工序映射。"""
        if 'sequence' in data:
            mapping.sequence = data['sequence']
        if 'remark' in data:
            mapping.remark = data['remark']
        mapping.save()
        return mapping, None

    @staticmethod
    def delete_style_process(mapping):
        """软删除款号工序映射。"""
        mapping.is_deleted = 1
        mapping.save()
        return True, None

    @staticmethod
    def batch_save_style_processes(style_id, mappings_data):
        """覆盖保存指定款号的工序映射列表。"""
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
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def check_style_permission(current_user, current_factory_id, style_id):
        """校验当前用户是否可以访问指定款号。"""
        if current_user and current_user.is_internal_user:
            style = Style.query.filter_by(id=style_id, is_deleted=0).first()
        else:
            if not current_factory_id:
                return None, '请先切换到工厂上下文'
            style = Style.query.filter_by(id=style_id, factory_id=current_factory_id, is_deleted=0).first()
        if not style:
            return None, '款号不存在或无权限'
        return style, None
