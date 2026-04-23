from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.auth.user import User
from app.utils.response import ApiResponse
import psutil
import platform
from datetime import datetime
from app.api.v1.shared_models import get_shared_models

monitor_ns = Namespace('monitor', description='服务监控')

shared = get_shared_models(monitor_ns)
base_response = shared['base_response']
unauthorized_response = shared['unauthorized_response']

monitor_response = monitor_ns.clone('MonitorResponse', base_response, {
    'data': fields.Raw()
})

SERVICE_START_TIME = datetime.now()


def format_bytes(bytes_value):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f}PB"


def format_uptime(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if days > 0:
        return f"{days}天{hours}小时{minutes}分钟"
    elif hours > 0:
        return f"{hours}小时{minutes}分钟"
    elif minutes > 0:
        return f"{minutes}分钟"
    else:
        return f"{secs}秒"


@monitor_ns.route('/info')
class MonitorInfo(Resource):
    @jwt_required()
    @monitor_ns.response(200, '成功', monitor_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        # 只有公司内部人员可以查看服务监控
        if current_user.is_admin != 1:
            return ApiResponse.error('无权限查看服务监控', 403)

        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_core_count = psutil.cpu_count()
        per_cpu_percent = psutil.cpu_percent(interval=1, percpu=True)

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        hostname = platform.node()
        os_name = platform.system()
        os_version = platform.release()
        python_version = platform.python_version()

        uptime_seconds = int((datetime.now() - SERVICE_START_TIME).total_seconds())
        uptime_display = format_uptime(uptime_seconds)

        data = {
            'system': {
                'hostname': hostname,
                'os_name': os_name,
                'os_version': os_version,
                'python_version': python_version,
                'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'cpu': {
                'percent': round(cpu_percent, 1),
                'core_count': cpu_core_count,
                'per_core_percent': [round(p, 1) for p in per_cpu_percent]
            },
            'memory': {
                'total': memory.total,
                'total_display': format_bytes(memory.total),
                'used': memory.used,
                'used_display': format_bytes(memory.used),
                'free': memory.free,
                'free_display': format_bytes(memory.free),
                'percent': round(memory.percent, 1)
            },
            'disk': {
                'total': disk.total,
                'total_display': format_bytes(disk.total),
                'used': disk.used,
                'used_display': format_bytes(disk.used),
                'free': disk.free,
                'free_display': format_bytes(disk.free),
                'percent': round(disk.percent, 1)
            },
            'service': {
                'start_time': SERVICE_START_TIME.strftime('%Y-%m-%d %H:%M:%S'),
                'uptime_seconds': uptime_seconds,
                'uptime_display': uptime_display
            }
        }

        return ApiResponse.success(data)


@monitor_ns.route('/cpu')
class CpuMonitor(Resource):
    @jwt_required()
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        cpu_percent = psutil.cpu_percent(interval=1)
        per_cpu_percent = psutil.cpu_percent(interval=1, percpu=True)

        return ApiResponse.success({
            'percent': round(cpu_percent, 1),
            'core_count': psutil.cpu_count(),
            'per_core_percent': [round(p, 1) for p in per_cpu_percent]
        })


@monitor_ns.route('/memory')
class MemoryMonitor(Resource):
    @jwt_required()
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        memory = psutil.virtual_memory()

        return ApiResponse.success({
            'total': memory.total,
            'total_display': format_bytes(memory.total),
            'used': memory.used,
            'used_display': format_bytes(memory.used),
            'free': memory.free,
            'free_display': format_bytes(memory.free),
            'percent': round(memory.percent, 1)
        })


@monitor_ns.route('/disk')
class DiskMonitor(Resource):
    @jwt_required()
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        disk = psutil.disk_usage('/')

        return ApiResponse.success({
            'total': disk.total,
            'total_display': format_bytes(disk.total),
            'used': disk.used,
            'used_display': format_bytes(disk.used),
            'free': disk.free,
            'free_display': format_bytes(disk.free),
            'percent': round(disk.percent, 1)
        })


@monitor_ns.route('/system')
class SystemMonitor(Resource):
    @jwt_required()
    @monitor_ns.response(200, '成功', base_response)
    @monitor_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=user_id, is_deleted=0).first()

        if not current_user or current_user.is_admin != 1:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success({
            'hostname': platform.node(),
            'os_name': platform.system(),
            'os_version': platform.release(),
            'python_version': platform.python_version(),
            'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
