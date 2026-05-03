"""服务监控接口"""
from flask_restx import Namespace, Resource, fields
from app.utils.response import ApiResponse
from app.api.v1.shared_models import get_shared_models
from app.utils.permissions import login_required
from app.services import AuthService, MonitorService

monitor_ns = Namespace('服务监控-monitor', description='服务监控')

shared = get_shared_models(monitor_ns)
base_response = shared['base_response']
unauthorized_response = shared['unauthorized_response']

monitor_response = monitor_ns.clone('MonitorResponse', base_response, {
    'data': fields.Raw()
})


# ========== 辅助函数 ==========
def get_current_user():
    """获取当前登录用户"""
    return AuthService.get_current_user()


@monitor_ns.route('/info')
class MonitorInfo(Resource):
    @login_required
    @monitor_ns.response(200, '成功', monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """完整监控信息"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 权限验证
        has_permission, error = MonitorService.check_admin_permission(current_user)
        if not has_permission:
            return ApiResponse.error(error, 403)

        data = MonitorService.get_full_monitor_info()

        return ApiResponse.success(data)


@monitor_ns.route('/cpu')
class CpuMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """CPU信息"""
        current_user = get_current_user()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        data = MonitorService.get_cpu_info()
        return ApiResponse.success(data)


@monitor_ns.route('/memory')
class MemoryMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """内存信息"""
        current_user = get_current_user()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        data = MonitorService.get_memory_info()
        return ApiResponse.success(data)


@monitor_ns.route('/disk')
class DiskMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """磁盘信息"""
        current_user = get_current_user()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        data = MonitorService.get_disk_info()
        return ApiResponse.success(data)


@monitor_ns.route('/system')
class SystemMonitor(Resource):
    @login_required
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """系统信息"""
        current_user = get_current_user()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        data = MonitorService.get_system_info()
        return ApiResponse.success(data)
