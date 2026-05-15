"""服务监控接口。"""

from flask_restx import Namespace, Resource, fields

from app.api.common.auth import get_current_user
from app.api.common.models import get_common_models
from app.services import MonitorService
from app.utils.permissions import login_required
from app.utils.response import ApiResponse

monitor_ns = Namespace('服务监控-monitor', description='服务监控')

shared = get_common_models(monitor_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

cpu_monitor_data = monitor_ns.model('CpuMonitorData', {
    'percent': fields.Float(description='CPU 总使用率', example=32.5),
    'core_count': fields.Integer(description='CPU 核心数', example=8),
    'per_core_percent': fields.List(fields.Float, description='各核心使用率', example=[30.0, 28.5, 35.2, 40.1]),
})

memory_monitor_data = monitor_ns.model('MemoryMonitorData', {
    'total': fields.Integer(description='总内存字节数', example=17179869184),
    'total_display': fields.String(description='总内存显示值', example='16.0GB'),
    'used': fields.Integer(description='已使用内存字节数', example=8589934592),
    'used_display': fields.String(description='已使用内存显示值', example='8.0GB'),
    'free': fields.Integer(description='可用内存字节数', example=8589934592),
    'free_display': fields.String(description='可用内存显示值', example='8.0GB'),
    'percent': fields.Float(description='内存使用率', example=50.0),
})

disk_monitor_data = monitor_ns.model('DiskMonitorData', {
    'total': fields.Integer(description='磁盘总容量字节数', example=536870912000),
    'total_display': fields.String(description='磁盘总容量显示值', example='500.0GB'),
    'used': fields.Integer(description='已使用磁盘容量字节数', example=214748364800),
    'used_display': fields.String(description='已使用磁盘容量显示值', example='200.0GB'),
    'free': fields.Integer(description='可用磁盘容量字节数', example=322122547200),
    'free_display': fields.String(description='可用磁盘容量显示值', example='300.0GB'),
    'percent': fields.Float(description='磁盘使用率', example=40.0),
})

system_monitor_data = monitor_ns.model('SystemMonitorData', {
    'hostname': fields.String(description='主机名', example='erp-server'),
    'os_name': fields.String(description='操作系统名称', example='Windows'),
    'os_version': fields.String(description='操作系统版本', example='11'),
    'python_version': fields.String(description='Python 版本', example='3.11.9'),
    'server_time': fields.String(description='服务器当前时间', example='2026-05-15 10:30:00'),
    'service_start_time': fields.String(description='服务启动时间', example='2026-05-15 09:00:00'),
    'uptime_seconds': fields.Integer(description='服务运行秒数', example=5400),
    'uptime_display': fields.String(description='服务运行时长显示值', example='1小时30分钟'),
})

service_monitor_data = monitor_ns.model('ServiceMonitorData', {
    'start_time': fields.String(description='服务启动时间', example='2026-05-15 09:00:00'),
    'uptime_seconds': fields.Integer(description='服务运行秒数', example=5400),
    'uptime_display': fields.String(description='服务运行时长显示值', example='1小时30分钟'),
})

monitor_system_base_data = monitor_ns.model('MonitorSystemBase', {
    'hostname': fields.String(description='主机名', example='erp-server'),
    'os_name': fields.String(description='操作系统名称', example='Windows'),
    'os_version': fields.String(description='操作系统版本', example='11'),
    'python_version': fields.String(description='Python 版本', example='3.11.9'),
    'server_time': fields.String(description='服务器当前时间', example='2026-05-15 10:30:00'),
})

full_monitor_data = monitor_ns.model('FullMonitorData', {
    'system': fields.Nested(monitor_system_base_data, description='系统基础信息'),
    'cpu': fields.Nested(cpu_monitor_data, description='CPU 监控信息'),
    'memory': fields.Nested(memory_monitor_data, description='内存监控信息'),
    'disk': fields.Nested(disk_monitor_data, description='磁盘监控信息'),
    'service': fields.Nested(service_monitor_data, description='服务运行信息'),
})

full_monitor_response = monitor_ns.clone('FullMonitorResponse', base_response, {
    'data': fields.Nested(full_monitor_data, description='完整监控信息', example={
        'system': {
            'hostname': 'erp-server',
            'os_name': 'Windows',
            'os_version': '11',
            'python_version': '3.11.9',
            'server_time': '2026-05-15 10:30:00',
        },
        'cpu': {'percent': 32.5, 'core_count': 8, 'per_core_percent': [30.0, 28.5, 35.2, 40.1]},
        'memory': {
            'total': 17179869184,
            'total_display': '16.0GB',
            'used': 8589934592,
            'used_display': '8.0GB',
            'free': 8589934592,
            'free_display': '8.0GB',
            'percent': 50.0,
        },
        'disk': {
            'total': 536870912000,
            'total_display': '500.0GB',
            'used': 214748364800,
            'used_display': '200.0GB',
            'free': 322122547200,
            'free_display': '300.0GB',
            'percent': 40.0,
        },
        'service': {'start_time': '2026-05-15 09:00:00', 'uptime_seconds': 5400, 'uptime_display': '1小时30分钟'},
    })
})
cpu_monitor_response = monitor_ns.clone('CpuMonitorResponse', base_response, {
    'data': fields.Nested(cpu_monitor_data, description='CPU 监控信息', example={'percent': 32.5, 'core_count': 8, 'per_core_percent': [30.0, 28.5, 35.2, 40.1]})
})
memory_monitor_response = monitor_ns.clone('MemoryMonitorResponse', base_response, {
    'data': fields.Nested(memory_monitor_data, description='内存监控信息', example={'total': 17179869184, 'total_display': '16.0GB', 'used': 8589934592, 'used_display': '8.0GB', 'free': 8589934592, 'free_display': '8.0GB', 'percent': 50.0})
})
disk_monitor_response = monitor_ns.clone('DiskMonitorResponse', base_response, {
    'data': fields.Nested(disk_monitor_data, description='磁盘监控信息', example={'total': 536870912000, 'total_display': '500.0GB', 'used': 214748364800, 'used_display': '200.0GB', 'free': 322122547200, 'free_display': '300.0GB', 'percent': 40.0})
})
system_monitor_response = monitor_ns.clone('SystemMonitorResponse', base_response, {
    'data': fields.Nested(system_monitor_data, description='系统基础信息', example={'hostname': 'erp-server', 'os_name': 'Windows', 'os_version': '11', 'python_version': '3.11.9', 'server_time': '2026-05-15 10:30:00', 'service_start_time': '2026-05-15 09:00:00', 'uptime_seconds': 5400, 'uptime_display': '1小时30分钟'})
})


def check_monitor_permission(current_user):
    """统一校验服务监控接口是否允许访问。"""
    if not current_user:
        return False, '用户不存在'
    return MonitorService.check_admin_permission(current_user)


@monitor_ns.route('/info')
class MonitorInfo(Resource):
    @login_required
    @monitor_ns.response(200, '成功', full_monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    @monitor_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询完整监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_full_monitor_info())


@monitor_ns.route('/cpu')
class CpuMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', cpu_monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    @monitor_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询 CPU 监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_cpu_info())


@monitor_ns.route('/memory')
class MemoryMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', memory_monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    @monitor_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询内存监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_memory_info())


@monitor_ns.route('/disk')
class DiskMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', disk_monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    @monitor_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询磁盘监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_disk_info())


@monitor_ns.route('/system')
class SystemMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', system_monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    @monitor_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """查询系统基础信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_system_info())
