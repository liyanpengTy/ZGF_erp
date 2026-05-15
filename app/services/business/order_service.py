"""订单管理服务。"""

from datetime import datetime

from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.business.bundle import ProductionBundle
from app.models.business.cutting_report import WorkCuttingReport
from app.models.business.order import (
    Order,
    OrderDetail,
    OrderDetailAttributeSnapshot,
    OrderDetailSku,
    OrderDetailSkuAttribute,
    OrderDetailSkuSpliceItem,
    OrderDetailSpliceSnapshot,
)
from app.models.business.style import Style
from app.models.business.value_codec import encode_dynamic_value, is_scalar_value
from app.services.base.base_service import BaseService
from app.services.business.bundle_service import BundleService
from app.services.business.shipment_service import ShipmentService


class OrderService(BaseService):
    """订单管理服务。"""

    @staticmethod
    def _sorted_dimension_items(counter):
        """将统计字典转换为保持录入顺序的列表结构。"""
        return [
            {'name': name, 'quantity': quantity}
            for name, quantity in counter.items()
        ]

    @staticmethod
    def _build_table_payload(key, title, headers, rows, summary_row):
        """构建统一的表格统计结构，便于前端按同一协议渲染。"""
        return {
            'key': key,
            'title': title,
            'headers': headers,
            'rows': rows,
            'summary_row': summary_row,
        }

    @staticmethod
    def build_detail_statistics(detail):
        """构建订单明细统计，包含颜色、尺码、矩阵和拼接维度汇总。"""
        color_totals = {}
        size_totals = {}
        matrix = {}
        splice_sections = {}
        splice_sequence_labels = {}
        splice_table_rows = []
        tables = []
        matrix_columns = []
        matrix_rows = []
        column_totals = {}
        total_quantity = 0

        for item in detail.snapshot_splice_data:
            splice_sequence_labels[item['sequence']] = item['description']

        for sku in detail.skus:
            config = sku.splice_config
            quantity = config.get('quantity', 0) or 0
            color_name = config.get('color_name')
            size_name = config.get('size_name')
            total_quantity += quantity

            if color_name:
                color_totals[color_name] = color_totals.get(color_name, 0) + quantity
            if size_name:
                size_totals[size_name] = size_totals.get(size_name, 0) + quantity

            if color_name and size_name:
                color_bucket = matrix.setdefault(color_name, {})
                color_bucket[size_name] = color_bucket.get(size_name, 0) + quantity
                if size_name not in matrix_columns:
                    matrix_columns.append(size_name)
                if color_name not in matrix_rows:
                    matrix_rows.append(color_name)
                column_totals[size_name] = column_totals.get(size_name, 0) + quantity

            for splice_item in config.get('splice_data', []) or []:
                section_bucket = splice_sections.setdefault(splice_item['sequence'], {})
                description = splice_item['description']
                section_bucket[description] = section_bucket.get(description, 0) + quantity

            if config.get('splice_data'):
                current_row = {}
                for splice_item in config.get('splice_data', []):
                    current_row[splice_item['sequence']] = splice_item['description']
                splice_table_rows.append({
                    'remark': sku.remark,
                    'values': current_row,
                    'total': quantity,
                })

        color_size_matrix = None
        if matrix_columns or matrix_rows:
            rows = []
            table_rows = []
            for color_name in matrix_rows:
                values = {size_name: matrix.get(color_name, {}).get(size_name, 0) for size_name in matrix_columns}
                row_total = sum(values.values())
                rows.append({
                    'name': color_name,
                    'values': values,
                    'total': row_total,
                })
                table_rows.append({
                    'label': color_name,
                    'cells': [values.get(size_name, 0) for size_name in matrix_columns],
                    'total': row_total,
                })
            color_size_matrix = {
                'columns': matrix_columns,
                'rows': rows,
                'column_totals': {size_name: column_totals.get(size_name, 0) for size_name in matrix_columns},
                'grand_total': sum(column_totals.values()),
                'table_headers': ['颜色', *matrix_columns, '合计'],
                'table_rows': table_rows,
                'summary_row': {
                    'label': '合计',
                    'cells': [column_totals.get(size_name, 0) for size_name in matrix_columns],
                    'total': sum(column_totals.values()),
                },
            }
            tables.append(OrderService._build_table_payload(
                key='color_size_matrix',
                title='颜色尺码统计',
                headers=color_size_matrix['table_headers'],
                rows=color_size_matrix['table_rows'],
                summary_row=color_size_matrix['summary_row'],
            ))

        splice_section_items = []
        for sequence in sorted(splice_sections):
            values = [
                {'name': name, 'quantity': quantity}
                for name, quantity in splice_sections[sequence].items()
            ]
            splice_section_items.append({
                'sequence': sequence,
                'values': values,
                'total': sum(item['quantity'] for item in values),
            })

        splice_item_table = None
        if splice_sequence_labels and splice_table_rows:
            ordered_sequences = sorted(splice_sequence_labels)
            splice_item_table = {
                'headers': [splice_sequence_labels[sequence] for sequence in ordered_sequences] + ['数量'],
                'rows': [
                    {
                        'remark': row['remark'],
                        'cells': [row['values'].get(sequence) for sequence in ordered_sequences],
                        'total': row['total'],
                    }
                    for row in splice_table_rows
                ],
                'summary_row': {
                    'label': '合计',
                    'cells': [''] * len(ordered_sequences),
                    'total': sum(row['total'] for row in splice_table_rows),
                },
            }
            tables.append(OrderService._build_table_payload(
                key='splice_item_table',
                title='拼接组合统计',
                headers=splice_item_table['headers'],
                rows=[
                    {
                        'label': row['remark'],
                        'cells': row['cells'],
                        'total': row['total'],
                    }
                    for row in splice_item_table['rows']
                ],
                summary_row=splice_item_table['summary_row'],
            ))

        return {
            'sku_count': len(detail.skus),
            'total_quantity': total_quantity,
            'color_totals': OrderService._sorted_dimension_items(color_totals),
            'size_totals': OrderService._sorted_dimension_items(size_totals),
            'color_size_matrix': color_size_matrix,
            'splice_sections': splice_section_items,
            'splice_item_table': splice_item_table,
            'tables': tables,
        }

    @staticmethod
    def build_order_statistics(order):
        """构建订单级统计汇总，整合各明细件数与行数。"""
        detail_items = []
        total_quantity = 0
        total_sku_count = 0

        for detail in order.details:
            detail_statistics = OrderService.build_detail_statistics(detail)
            total_quantity += detail_statistics['total_quantity']
            total_sku_count += detail_statistics['sku_count']
            detail_items.append({
                'detail_id': detail.id,
                'style_id': detail.style_id,
                'style_no': detail.style.style_no if detail.style else None,
                'style_name': detail.style.name if detail.style else None,
                'sku_count': detail_statistics['sku_count'],
                'total_quantity': detail_statistics['total_quantity'],
            })

        return {
            'detail_count': len(order.details),
            'sku_count': total_sku_count,
            'total_quantity': total_quantity,
            'details': detail_items,
        }

    @staticmethod
    def _build_sku_display_name(sku):
        """构建订单 SKU 的展示名称，便于生产统计按行展示。"""
        config = sku.splice_config
        color_name = config.get('color_name')
        size_name = config.get('size_name')
        if color_name and size_name:
            return f'{color_name}-{size_name}'
        if color_name:
            return color_name
        if size_name:
            return size_name
        if config.get('variant_name'):
            return config['variant_name']
        if config.get('tag'):
            return config['tag']
        return sku.remark or f'SKU-{sku.id}'

    @staticmethod
    def build_order_production_statistics(order):
        """构建订单生产统计，汇总下单、实裁、领货、交货、在手、完工与已出货数量。"""
        sku_items = {}
        detail_groups = {}

        for detail in order.details:
            detail_groups[detail.id] = {
                'detail_id': detail.id,
                'style_id': detail.style_id,
                'style_no': detail.style.style_no if detail.style else None,
                'style_name': detail.style.name if detail.style else None,
                'ordered_quantity': 0,
                'cut_quantity': 0,
                'bundle_quantity': 0,
                'issued_quantity': 0,
                'returned_quantity': 0,
                'in_hand_quantity': 0,
                'completed_quantity': 0,
                'shipped_quantity': 0,
                'cutting_report_count': 0,
                'bundle_count': 0,
                'sku_items': [],
            }
            for sku in detail.skus:
                config = sku.splice_config
                ordered_quantity = config.get('quantity', 0) or 0
                item = {
                    'order_detail_sku_id': sku.id,
                    'sku_name': OrderService._build_sku_display_name(sku),
                    'color_id': config.get('color_id'),
                    'color_name': config.get('color_name'),
                    'size_id': config.get('size_id'),
                    'size_name': config.get('size_name'),
                    'ordered_quantity': ordered_quantity,
                    'cut_quantity': 0,
                    'bundle_quantity': 0,
                    'issued_quantity': 0,
                    'returned_quantity': 0,
                    'in_hand_quantity': 0,
                    'completed_quantity': 0,
                    'shipped_quantity': 0,
                    'cutting_report_count': 0,
                    'bundle_count': 0,
                }
                sku_items[sku.id] = item
                detail_groups[detail.id]['sku_items'].append(item)
                detail_groups[detail.id]['ordered_quantity'] += ordered_quantity

        cutting_reports = WorkCuttingReport.query.filter_by(order_id=order.id, is_deleted=0).all()
        for report in cutting_reports:
            item = sku_items.get(report.order_detail_sku_id)
            if not item:
                continue
            item['cut_quantity'] += report.cut_quantity or 0
            item['cutting_report_count'] += 1

        bundles = ProductionBundle.query.options(
            selectinload(ProductionBundle.flows)
        ).filter_by(order_id=order.id, is_deleted=0).all()
        for bundle in bundles:
            item = sku_items.get(bundle.order_detail_sku_id)
            if not item:
                continue
            metrics = BundleService.calculate_flow_metrics(bundle)
            item['bundle_quantity'] += bundle.bundle_quantity or 0
            item['bundle_count'] += 1
            item['issued_quantity'] += metrics['issued_quantity']
            item['returned_quantity'] += metrics['returned_quantity']
            item['in_hand_quantity'] += metrics['in_hand_quantity']
            if bundle.status == 'completed':
                item['completed_quantity'] += bundle.bundle_quantity or 0

        shipped_map = ShipmentService.get_shipped_quantity_map_for_order(order.id)
        for sku_id, shipped_quantity in shipped_map.items():
            item = sku_items.get(sku_id)
            if not item:
                continue
            item['shipped_quantity'] += shipped_quantity

        for detail_id, detail_group in detail_groups.items():
            for item in detail_group['sku_items']:
                detail_group['cut_quantity'] += item['cut_quantity']
                detail_group['bundle_quantity'] += item['bundle_quantity']
                detail_group['issued_quantity'] += item['issued_quantity']
                detail_group['returned_quantity'] += item['returned_quantity']
                detail_group['in_hand_quantity'] += item['in_hand_quantity']
                detail_group['completed_quantity'] += item['completed_quantity']
                detail_group['shipped_quantity'] += item['shipped_quantity']
                detail_group['cutting_report_count'] += item['cutting_report_count']
                detail_group['bundle_count'] += item['bundle_count']

        detail_items = list(detail_groups.values())
        summary = {
            'detail_count': len(detail_items),
            'sku_count': len(sku_items),
            'ordered_quantity': sum(item['ordered_quantity'] for item in detail_items),
            'cut_quantity': sum(item['cut_quantity'] for item in detail_items),
            'bundle_quantity': sum(item['bundle_quantity'] for item in detail_items),
            'issued_quantity': sum(item['issued_quantity'] for item in detail_items),
            'returned_quantity': sum(item['returned_quantity'] for item in detail_items),
            'in_hand_quantity': sum(item['in_hand_quantity'] for item in detail_items),
            'completed_quantity': sum(item['completed_quantity'] for item in detail_items),
            'shipped_quantity': sum(item['shipped_quantity'] for item in detail_items),
            'cutting_report_count': sum(item['cutting_report_count'] for item in detail_items),
            'bundle_count': sum(item['bundle_count'] for item in detail_items),
        }
        return {
            'summary': summary,
            'details': detail_items,
        }

    @staticmethod
    def build_order_shipment_availability(order):
        """构建订单可出货统计，汇总各 SKU 的已完工、已出货与可出货数量。"""
        completed_map = ShipmentService.get_completed_quantity_map_for_order(order.id)
        shipped_map = ShipmentService.get_shipped_quantity_map_for_order(order.id)
        detail_groups = {}

        for detail in order.details:
            detail_group = {
                'detail_id': detail.id,
                'style_id': detail.style_id,
                'style_no': detail.style.style_no if detail.style else None,
                'style_name': detail.style.name if detail.style else None,
                'ordered_quantity': 0,
                'completed_quantity': 0,
                'shipped_quantity': 0,
                'available_quantity': 0,
                'sku_items': [],
            }

            for sku in detail.skus:
                config = sku.splice_config
                ordered_quantity = config.get('quantity', 0) or 0
                completed_quantity = completed_map.get(sku.id, 0)
                shipped_quantity = shipped_map.get(sku.id, 0)
                available_quantity = max(completed_quantity - shipped_quantity, 0)
                sku_item = {
                    'order_detail_sku_id': sku.id,
                    'sku_name': OrderService._build_sku_display_name(sku),
                    'color_id': config.get('color_id'),
                    'color_name': config.get('color_name'),
                    'size_id': config.get('size_id'),
                    'size_name': config.get('size_name'),
                    'ordered_quantity': ordered_quantity,
                    'completed_quantity': completed_quantity,
                    'shipped_quantity': shipped_quantity,
                    'available_quantity': available_quantity,
                }
                detail_group['sku_items'].append(sku_item)
                detail_group['ordered_quantity'] += ordered_quantity
                detail_group['completed_quantity'] += completed_quantity
                detail_group['shipped_quantity'] += shipped_quantity
                detail_group['available_quantity'] += available_quantity

            detail_groups[detail.id] = detail_group

        detail_items = list(detail_groups.values())
        summary = {
            'detail_count': len(detail_items),
            'sku_count': sum(len(item['sku_items']) for item in detail_items),
            'ordered_quantity': sum(item['ordered_quantity'] for item in detail_items),
            'completed_quantity': sum(item['completed_quantity'] for item in detail_items),
            'shipped_quantity': sum(item['shipped_quantity'] for item in detail_items),
            'available_quantity': sum(item['available_quantity'] for item in detail_items),
        }
        return {
            'summary': summary,
            'details': detail_items,
        }

    @staticmethod
    def build_order_list_statistics(orders):
        """构建订单列表级统计，汇总整页订单的件数、行数和常用维度。"""
        status_totals = {}
        customer_totals = {}
        delivery_date_totals = {}
        total_quantity = 0
        total_sku_count = 0
        total_detail_count = 0

        for order in orders:
            order_statistics = OrderService.build_order_statistics(order)
            order_quantity = order_statistics['total_quantity']
            total_quantity += order_quantity
            total_sku_count += order_statistics['sku_count']
            total_detail_count += order_statistics['detail_count']

            status_key = order.status or ''
            customer_key = order.customer_name or ''
            delivery_date_key = order.delivery_date.isoformat() if order.delivery_date else ''

            status_totals[status_key] = status_totals.get(status_key, 0) + order_quantity
            customer_totals[customer_key] = customer_totals.get(customer_key, 0) + order_quantity
            delivery_date_totals[delivery_date_key] = delivery_date_totals.get(delivery_date_key, 0) + order_quantity

        return {
            'order_count': len(orders),
            'detail_count': total_detail_count,
            'sku_count': total_sku_count,
            'total_quantity': total_quantity,
            'status_totals': OrderService._sorted_dimension_items(status_totals),
            'customer_totals': OrderService._sorted_dimension_items(customer_totals),
            'delivery_date_totals': OrderService._sorted_dimension_items(delivery_date_totals),
        }

    @staticmethod
    def generate_order_no(factory_id):
        """按工厂和日期生成订单编号。"""
        today = datetime.now().strftime('%Y%m%d')
        last_order = Order.query.filter(
            Order.order_no.like(f'ORD{factory_id}{today}%'),
        ).order_by(Order.id.desc()).first()

        seq = int(last_order.order_no[-4:]) + 1 if last_order else 1
        return f'ORD{factory_id}{today}{seq:04d}'

    @staticmethod
    def get_order_query_options():
        """统一封装订单查询时需要预加载的关联项。"""
        return [
            selectinload(Order.details).joinedload(OrderDetail.style),
            selectinload(Order.details).selectinload(OrderDetail.snapshot_splice_items),
            selectinload(Order.details).selectinload(OrderDetail.snapshot_attribute_items),
            selectinload(Order.details).selectinload(OrderDetail.skus).joinedload(OrderDetailSku.color),
            selectinload(Order.details).selectinload(OrderDetail.skus).joinedload(OrderDetailSku.size),
            selectinload(Order.details).selectinload(OrderDetail.skus).selectinload(OrderDetailSku.splice_items),
            selectinload(Order.details).selectinload(OrderDetail.skus).selectinload(OrderDetailSku.attribute_items),
        ]

    @staticmethod
    def get_order_by_id(order_id):
        """根据 ID 获取订单及其明细。"""
        return Order.query.options(*OrderService.get_order_query_options()).filter_by(id=order_id, is_deleted=0).first()

    @staticmethod
    def get_order_by_no(order_no):
        """根据订单编号获取订单。"""
        return Order.query.filter_by(order_no=order_no, is_deleted=0).first()

    @staticmethod
    def get_order_list(current_factory_id, filters):
        """分页查询当前工厂的订单列表。"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        order_no = filters.get('order_no', '')
        customer_name = filters.get('customer_name', '')
        status = filters.get('status')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        if not current_factory_id:
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}

        query = Order.query.filter_by(factory_id=current_factory_id, is_deleted=0).options(
            *OrderService.get_order_query_options()
        )

        if order_no:
            query = query.filter(Order.order_no.like(f'%{order_no}%'))
        if customer_name:
            query = query.filter(Order.customer_name.like(f'%{customer_name}%'))
        if status:
            query = query.filter_by(status=status)
        if start_date:
            query = query.filter(Order.order_date >= start_date)
        if end_date:
            query = query.filter(Order.order_date <= end_date)

        pagination = query.order_by(Order.id.desc()).paginate(page=page, per_page=page_size, error_out=False)
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages,
        }

    @staticmethod
    def validate_splice_items(splice_items):
        """校验 SKU 拼接结构列表。"""
        if not isinstance(splice_items, list):
            return False
        for item in splice_items:
            if not isinstance(item, dict):
                return False
            if 'sequence' not in item or 'description' not in item:
                return False
            if not isinstance(item['sequence'], int):
                return False
        return True

    @staticmethod
    def split_sku_config(splice_config):
        """拆分 SKU 配置为结构化字段、拼接明细和扩展属性。"""
        if not isinstance(splice_config, dict):
            return None, 'SKU 配置必须是对象'

        splice_items = splice_config.get('splice_data', splice_config.get('splice_items', []))
        if splice_items and not OrderService.validate_splice_items(splice_items):
            return None, 'SKU 拼接数据格式错误'

        data = {
            'color_id': splice_config.get('color_id'),
            'size_id': splice_config.get('size_id'),
            'quantity': splice_config.get('quantity', 1),
            'unit_price': splice_config.get('unit_price', 0),
            'priority': splice_config.get('priority', 0),
            'splice_items': splice_items or [],
            'attributes': [],
        }

        ignored_keys = {
            'color_id', 'size_id', 'quantity', 'unit_price', 'priority',
            'splice_data', 'splice_items', 'color_name', 'size_name',
        }
        for index, (key, value) in enumerate(splice_config.items(), start=1):
            if key in ignored_keys:
                continue
            if not is_scalar_value(value):
                return None, f'SKU 字段 {key} 只支持标量值'
            value_type, raw_value = encode_dynamic_value(value)
            data['attributes'].append({
                'attr_key': key,
                'attr_value': raw_value,
                'value_type': value_type,
                'sort_order': index,
            })
        return data, None

    @staticmethod
    def replace_detail_snapshots(detail, style):
        """按款号当前结构重建订单明细快照。"""
        detail.snapshot_splice_items[:] = []
        detail.snapshot_attribute_items[:] = []

        for item in style.splice_data:
            detail.snapshot_splice_items.append(
                OrderDetailSpliceSnapshot(
                    sequence=item['sequence'],
                    description=item['description'],
                )
            )

        for index, (attr_key, attr_value) in enumerate(style.custom_attributes.items(), start=1):
            value_type, raw_value = encode_dynamic_value(attr_value)
            detail.snapshot_attribute_items.append(
                OrderDetailAttributeSnapshot(
                    attr_key=attr_key,
                    attr_value=raw_value,
                    value_type=value_type,
                    sort_order=index,
                )
            )

    @staticmethod
    def build_sku(detail, sku_data):
        """根据接口参数创建结构化 SKU 对象。"""
        parsed_config, error = OrderService.split_sku_config(sku_data['splice_config'])
        if error:
            return None, error

        sku = OrderDetailSku(
            detail_id=detail.id,
            color_id=parsed_config['color_id'],
            size_id=parsed_config['size_id'],
            quantity=parsed_config['quantity'] or 1,
            unit_price=parsed_config['unit_price'] or 0,
            priority=parsed_config['priority'] or 0,
            remark=sku_data.get('remark', ''),
        )
        db.session.add(sku)
        db.session.flush()

        for item in parsed_config['splice_items']:
            sku.splice_items.append(
                OrderDetailSkuSpliceItem(
                    sequence=item['sequence'],
                    description=item['description'],
                )
            )

        for attr in parsed_config['attributes']:
            sku.attribute_items.append(
                OrderDetailSkuAttribute(
                    attr_key=attr['attr_key'],
                    attr_value=attr['attr_value'],
                    value_type=attr['value_type'],
                    sort_order=attr['sort_order'],
                )
            )
        return sku, None

    @staticmethod
    def create_order(current_user, current_factory_id, data):
        """创建订单及其明细快照。"""
        if not current_factory_id:
            return None, '请先切换到工厂上下文'

        details = data.get('details') or []
        if not details:
            return None, '请添加订单明细'

        style_ids = [item.get('style_id') for item in details if item.get('style_id') is not None]
        if not style_ids:
            return None, '订单明细缺少款号'

        styles = Style.query.options(
            selectinload(Style.splice_items),
            selectinload(Style.attribute_items),
        ).filter(
            Style.id.in_(style_ids),
            Style.factory_id == current_factory_id,
            Style.is_deleted == 0,
        ).all()
        style_map = {style.id: style for style in styles}
        missing_style_ids = sorted(set(style_ids) - set(style_map.keys()))
        if missing_style_ids:
            return None, f'以下款号不存在或无权限: {missing_style_ids}'

        for index, detail_data in enumerate(details, start=1):
            skus = detail_data.get('skus') or []
            if not skus:
                return None, f'第 {index} 条订单明细缺少 SKU'

        try:
            order_no = OrderService.generate_order_no(current_factory_id)
            order = Order(
                order_no=order_no,
                factory_id=current_factory_id,
                customer_id=data.get('customer_id'),
                customer_name=data.get('customer_name', ''),
                order_date=datetime.strptime(data['order_date'], '%Y-%m-%d').date(),
                delivery_date=datetime.strptime(data['delivery_date'], '%Y-%m-%d').date()
                if data.get('delivery_date') else None,
                status='pending',
                total_amount=0,
                remark=data.get('remark', ''),
                create_by=current_user.id,
            )
            db.session.add(order)
            db.session.flush()

            for detail_data in details:
                style = style_map[detail_data['style_id']]
                detail = OrderDetail(
                    order_id=order.id,
                    style_id=style.id,
                    remark=detail_data.get('remark', ''),
                )
                db.session.add(detail)
                db.session.flush()

                OrderService.replace_detail_snapshots(detail, style)

                for sku_data in detail_data['skus']:
                    _, error = OrderService.build_sku(detail, sku_data)
                    if error:
                        raise ValueError(error)

            db.session.commit()
            return OrderService.get_order_by_id(order.id), None
        except Exception as exc:
            db.session.rollback()
            return None, f'创建订单失败: {exc}'

    @staticmethod
    def update_order(order, data):
        """更新订单基础资料。"""
        if 'customer_id' in data:
            order.customer_id = data['customer_id']
        if 'customer_name' in data:
            order.customer_name = data['customer_name']
        if 'delivery_date' in data and data['delivery_date']:
            order.delivery_date = datetime.strptime(data['delivery_date'], '%Y-%m-%d').date()
        if 'remark' in data:
            order.remark = data['remark']
        order.save()
        return order

    @staticmethod
    def update_order_status(order, status):
        """更新订单状态。"""
        order.status = status
        order.save()
        return order

    @staticmethod
    def delete_order(order):
        """软删除订单。"""
        order.is_deleted = 1
        order.save()
        return True

    @staticmethod
    def check_permission(current_user, current_factory_id, order):
        """校验订单数据是否属于当前访问范围。"""
        if not current_user:
            return False, '用户不存在'
        if current_user.is_internal_user:
            return True, None
        if order.factory_id != current_factory_id:
            return False, '无权限操作'
        return True, None
