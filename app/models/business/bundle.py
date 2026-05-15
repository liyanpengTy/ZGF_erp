"""菲模板、菲规则与菲流转模型。"""

from datetime import datetime

from app.extensions import db
from app.models.base import BaseModel


class BundleTemplate(BaseModel):
    """菲模板主表，支持系统模板与工厂自定义模板。"""

    __tablename__ = 'prd_bundle_template'
    __table_args__ = (
        db.Index('idx_prd_bundle_template_factory_id', 'factory_id'),
        db.Index('idx_prd_bundle_template_scope', 'template_scope'),
        {'comment': '菲模板主表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), comment='所属工厂ID，系统模板为空')
    name = db.Column(db.String(100), nullable=False, comment='模板名称')
    template_scope = db.Column(db.String(20), nullable=False, default='factory', comment='模板范围：system/factory')
    version = db.Column(db.Integer, nullable=False, default=1, comment='模板版本号')
    is_default = db.Column(db.SmallInteger, nullable=False, default=0, comment='是否默认模板：1-是，0-否')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态：1-启用，0-停用')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='bundle_templates')
    items = db.relationship(
        'BundleTemplateItem',
        backref='template',
        cascade='all, delete-orphan',
        order_by='BundleTemplateItem.sort_order.asc()'
    )

    @property
    def scope_label(self):
        """返回模板范围中文名称。"""
        return '系统模板' if self.template_scope == 'system' else '工厂模板'


class BundleTemplateItem(BaseModel):
    """菲模板字段明细表。"""

    __tablename__ = 'prd_bundle_template_item'
    __table_args__ = (
        db.Index('idx_prd_bundle_template_item_template_id', 'template_id'),
        {'comment': '菲模板字段明细表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    template_id = db.Column(db.Integer, db.ForeignKey('prd_bundle_template.id'), nullable=False, comment='模板ID')
    field_code = db.Column(db.String(50), nullable=False, comment='字段编码')
    field_label = db.Column(db.String(50), nullable=False, comment='字段显示名称')
    sort_order = db.Column(db.Integer, nullable=False, default=0, comment='排序值')
    is_visible = db.Column(db.SmallInteger, nullable=False, default=1, comment='是否显示：1-显示，0-隐藏')
    is_bold = db.Column(db.SmallInteger, nullable=False, default=0, comment='是否加粗：1-加粗，0-普通')
    is_new_line = db.Column(db.SmallInteger, nullable=False, default=1, comment='是否换行：1-换行，0-同行')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')


class FactoryBundleRule(BaseModel):
    """工厂菲规则表，控制默认模板和床次重置周期。"""

    __tablename__ = 'prd_factory_bundle_rule'
    __table_args__ = {'comment': '工厂菲规则表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, unique=True, comment='工厂ID')
    reset_cycle = db.Column(db.String(20), nullable=False, default='yearly', comment='床次重置周期：yearly/monthly')
    default_template_id = db.Column(db.Integer, db.ForeignKey('prd_bundle_template.id'), comment='默认菲模板ID')
    bundle_code_prefix = db.Column(db.String(20), comment='菲号前缀')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态：1-启用，0-停用')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='bundle_rule')
    default_template = db.relationship('BundleTemplate', foreign_keys=[default_template_id], backref='used_by_factory_rules')

    @property
    def reset_cycle_label(self):
        """返回床次重置周期中文名称。"""
        return {'yearly': '按年重置', 'monthly': '按月重置'}.get(self.reset_cycle, self.reset_cycle)


class FactoryCutBatchCounter(BaseModel):
    """工厂床次计数器，用于按周期生成新的床次编号。"""

    __tablename__ = 'prd_factory_cut_batch_counter'
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'reset_cycle', 'period_key', name='uk_factory_cut_batch_counter'),
        {'comment': '工厂床次计数器'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    reset_cycle = db.Column(db.String(20), nullable=False, comment='床次重置周期：yearly/monthly')
    period_key = db.Column(db.String(20), nullable=False, comment='周期键，例如 2026 或 2026-05')
    current_no = db.Column(db.Integer, nullable=False, default=0, comment='当前已使用床次号')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='cut_batch_counters')


class ProductionBundle(BaseModel):
    """菲主表，记录裁床后生成的可流转生产单元。"""

    __tablename__ = 'prd_production_bundle'
    __table_args__ = (
        db.UniqueConstraint('bundle_no', 'is_deleted', name='uk_bundle_no'),
        db.Index('idx_prd_production_bundle_factory_id', 'factory_id'),
        db.Index('idx_prd_production_bundle_order_id', 'order_id'),
        db.Index('idx_prd_production_bundle_sku_id', 'order_detail_sku_id'),
        db.Index('idx_prd_production_bundle_cut_batch_no', 'cut_batch_no'),
        {'comment': '菲主表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    cutting_report_id = db.Column(db.Integer, db.ForeignKey('prd_work_cutting_report.id'), nullable=False, comment='裁床报工ID')
    template_id = db.Column(db.Integer, db.ForeignKey('prd_bundle_template.id'), comment='模板ID')
    template_version = db.Column(db.Integer, nullable=False, default=1, comment='模板版本号快照')
    bundle_no = db.Column(db.String(100), nullable=False, comment='菲号')
    order_id = db.Column(db.Integer, db.ForeignKey('ord_order.id'), nullable=False, comment='订单ID')
    order_detail_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail.id'), nullable=False, comment='订单明细ID')
    order_detail_sku_id = db.Column(db.Integer, db.ForeignKey('ord_order_detail_sku.id'), nullable=False, comment='订单SKU ID')
    style_id = db.Column(db.Integer, db.ForeignKey('fab_style.id'), nullable=False, comment='款号ID')
    color_id = db.Column(db.Integer, db.ForeignKey('fab_color.id'), comment='颜色ID')
    size_id = db.Column(db.Integer, db.ForeignKey('sys_size.id'), comment='尺码ID')
    cut_batch_no = db.Column(db.Integer, nullable=False, comment='床次')
    bed_no = db.Column(db.Integer, nullable=False, default=1, comment='床号')
    bundle_quantity = db.Column(db.Integer, nullable=False, default=1, comment='当前菲数量')
    priority = db.Column(db.String(20), nullable=False, default='normal', comment='优先级：normal/urgent/top')
    status = db.Column(db.String(20), nullable=False, default='created', comment='状态：created/issued/in_progress/returned/completed/rework/cancelled')
    current_holder_user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='当前持有人ID')
    current_process_id = db.Column(db.Integer, db.ForeignKey('pro_process.id'), comment='当前工序ID')
    printed_content = db.Column(db.Text, comment='打印内容快照')
    printed_at = db.Column(db.DateTime, comment='最近打印时间')
    print_count = db.Column(db.Integer, nullable=False, default=0, comment='打印次数')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='production_bundles')
    cutting_report = db.relationship('WorkCuttingReport', backref='bundles')
    template = db.relationship('BundleTemplate', backref='bundles')
    order = db.relationship('Order', backref='bundles')
    order_detail = db.relationship('OrderDetail', backref='bundles')
    order_detail_sku = db.relationship('OrderDetailSku', backref='bundles')
    style = db.relationship('Style', backref='bundles')
    color = db.relationship('Color', backref='production_bundles')
    size = db.relationship('Size', backref='production_bundles')
    current_holder = db.relationship('User', foreign_keys=[current_holder_user_id], backref='holding_bundles')
    current_process = db.relationship('Process', foreign_keys=[current_process_id], backref='current_bundles')
    flows = db.relationship('ProductionBundleFlow', backref='bundle', cascade='all, delete-orphan')

    @property
    def priority_label(self):
        """返回优先级中文名称。"""
        return {'normal': '普通', 'urgent': '加急', 'top': '特急'}.get(self.priority, self.priority)

    @property
    def status_label(self):
        """返回菲状态中文名称。"""
        return {
            'created': '已生成',
            'issued': '已领出',
            'in_progress': '生产中',
            'returned': '已交回',
            'completed': '已完工',
            'rework': '返工中',
            'cancelled': '已作废',
        }.get(self.status, self.status)


class ProductionBundleFlow(BaseModel):
    """菲流转记录表，记录生成、打印、领货、交货、转交和完工动作。"""

    __tablename__ = 'prd_production_bundle_flow'
    __table_args__ = (
        db.Index('idx_prd_production_bundle_flow_bundle_id', 'bundle_id'),
        db.Index('idx_prd_production_bundle_flow_factory_id', 'factory_id'),
        {'comment': '菲流转记录表'},
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('prd_production_bundle.id'), nullable=False, comment='菲ID')
    factory_id = db.Column(db.Integer, db.ForeignKey('sys_factory.id'), nullable=False, comment='工厂ID')
    process_id = db.Column(db.Integer, db.ForeignKey('pro_process.id'), comment='工序ID')
    user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='操作人ID')
    from_user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='来源人ID')
    to_user_id = db.Column(db.Integer, db.ForeignKey('sys_user.id'), comment='去向人ID')
    action_type = db.Column(db.String(30), nullable=False, comment='动作类型：create/print/issue/return/transfer/complete/rework_issue/rework_return')
    quantity = db.Column(db.Integer, nullable=False, default=0, comment='动作数量')
    action_time = db.Column(db.DateTime, nullable=False, default=datetime.now, comment='动作时间')
    remark = db.Column(db.String(500), comment='备注')
    is_deleted = db.Column(db.SmallInteger, default=0, comment='逻辑删除：0-未删除，1-已删除')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    factory = db.relationship('Factory', backref='bundle_flows')
    process = db.relationship('Process', backref='bundle_flows')
    user = db.relationship('User', foreign_keys=[user_id], backref='bundle_flow_actions')
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='bundle_flow_from_actions')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='bundle_flow_to_actions')

    @property
    def action_type_label(self):
        """返回流转动作中文名称。"""
        return {
            'create': '生成菲',
            'print': '打印菲',
            'issue': '领货',
            'return': '交货',
            'transfer': '转交',
            'complete': '完工确认',
            'rework_issue': '返工领出',
            'rework_return': '返工交回',
        }.get(self.action_type, self.action_type)
