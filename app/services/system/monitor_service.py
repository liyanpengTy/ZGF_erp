"""服务监控服务"""
import psutil
import platform
from datetime import datetime


class MonitorService:
    """服务监控服务"""

    # 服务启动时间（在类加载时设置）
    service_start_time = datetime.now()

    @staticmethod
    def format_bytes(bytes_value):
        """格式化字节大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"

    @staticmethod
    def format_uptime(seconds):
        """格式化运行时间"""
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

    @staticmethod
    def get_cpu_info():
        """获取CPU信息"""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        per_cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)

        return {
            'percent': round(cpu_percent, 1),
            'core_count': psutil.cpu_count(),
            'per_core_percent': [round(p, 1) for p in per_cpu_percent]
        }

    @staticmethod
    def get_memory_info():
        """获取内存信息"""
        memory = psutil.virtual_memory()

        return {
            'total': memory.total,
            'total_display': MonitorService.format_bytes(memory.total),
            'used': memory.used,
            'used_display': MonitorService.format_bytes(memory.used),
            'free': memory.free,
            'free_display': MonitorService.format_bytes(memory.free),
            'percent': round(memory.percent, 1)
        }

    @staticmethod
    def get_disk_info():
        """获取磁盘信息"""
        disk = psutil.disk_usage('/')

        return {
            'total': disk.total,
            'total_display': MonitorService.format_bytes(disk.total),
            'used': disk.used,
            'used_display': MonitorService.format_bytes(disk.used),
            'free': disk.free,
            'free_display': MonitorService.format_bytes(disk.free),
            'percent': round(disk.percent, 1)
        }

    @staticmethod
    def get_system_info():
        """获取系统信息"""
        uptime_seconds = int((datetime.now() - MonitorService.service_start_time).total_seconds())

        return {
            'hostname': platform.node(),
            'os_name': platform.system(),
            'os_version': platform.release(),
            'python_version': platform.python_version(),
            'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'service_start_time': MonitorService.service_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'uptime_seconds': uptime_seconds,
            'uptime_display': MonitorService.format_uptime(uptime_seconds)
        }

    @staticmethod
    def get_full_monitor_info():
        """获取完整监控信息"""
        return {
            'system': {
                'hostname': platform.node(),
                'os_name': platform.system(),
                'os_version': platform.release(),
                'python_version': platform.python_version(),
                'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'cpu': MonitorService.get_cpu_info(),
            'memory': MonitorService.get_memory_info(),
            'disk': MonitorService.get_disk_info(),
            'service': {
                'start_time': MonitorService.service_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'uptime_seconds': int((datetime.now() - MonitorService.service_start_time).total_seconds()),
                'uptime_display': MonitorService.format_uptime(
                    int((datetime.now() - MonitorService.service_start_time).total_seconds())
                )
            }
        }

    @staticmethod
    def check_admin_permission(current_user):
        """检查管理员权限"""
        if not current_user or current_user.is_admin != 1:
            return False, '无权限查看服务监控'
        return True, None
