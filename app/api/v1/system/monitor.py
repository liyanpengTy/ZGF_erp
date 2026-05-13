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
unauthorized_response = shared['unauthorized_response']

monitor_response = monitor_ns.clone('MonitorResponse', base_response, {
    'data': fields.Raw()
})


def check_monitor_permission(current_user):
    """统一校验服务监控接口是否允许访问。"""
    if not current_user:
        return False, '用户不存在'
    return MonitorService.check_admin_permission(current_user)


@monitor_ns.route('/info')
class MonitorInfo(Resource):
    @login_required
    @monitor_ns.response(200, '成功', monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回完整的服务监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_full_monitor_info())


@monitor_ns.route('/cpu')
class CpuMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回 CPU 监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_cpu_info())


@monitor_ns.route('/memory')
class MemoryMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回内存监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_memory_info())


@monitor_ns.route('/disk')
class DiskMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回磁盘监控信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_disk_info())


@monitor_ns.route('/system')
class SystemMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """返回系统基础信息。"""
        current_user = get_current_user()
        has_permission, error = check_monitor_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)
        return ApiResponse.success(MonitorService.get_system_info())
