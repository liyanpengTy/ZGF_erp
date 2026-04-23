from marshmallow import Schema, fields


class SystemInfoSchema(Schema):
    """系统信息"""
    hostname = fields.String()
    os_name = fields.String()
    os_version = fields.String()
    python_version = fields.String()
    server_time = fields.String()


class CpuInfoSchema(Schema):
    """CPU信息"""
    percent = fields.Float()
    core_count = fields.Integer()
    per_core_percent = fields.List(fields.Float())


class MemoryInfoSchema(Schema):
    """内存信息"""
    total = fields.Integer()
    used = fields.Integer()
    free = fields.Integer()
    percent = fields.Float()


class DiskInfoSchema(Schema):
    """磁盘信息"""
    total = fields.Integer()
    used = fields.Integer()
    free = fields.Integer()
    percent = fields.Float()


class ServiceInfoSchema(Schema):
    """服务信息"""
    start_time = fields.String()
    uptime_seconds = fields.Integer()
    uptime_display = fields.String()


class MonitorInfoSchema(Schema):
    """监控信息汇总"""
    system = fields.Nested(SystemInfoSchema)
    cpu = fields.Nested(CpuInfoSchema)
    memory = fields.Nested(MemoryInfoSchema)
    disk = fields.Nested(DiskInfoSchema)
    service = fields.Nested(ServiceInfoSchema)
