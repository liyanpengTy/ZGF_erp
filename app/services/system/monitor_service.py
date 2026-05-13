"""服务监控服务。"""

from datetime import datetime
import platform

import psutil


class MonitorService:
    """服务监控服务。"""

    service_start_time = datetime.now()

    @staticmethod
    def format_bytes(bytes_value):
        """将字节数格式化成可读文本。"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f'{bytes_value:.1f}{unit}'
            bytes_value /= 1024.0
        return f'{bytes_value:.1f}PB'

    @staticmethod
    def format_uptime(seconds):
        """将运行时长格式化成中文文本。"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if days > 0:
            return f'{days}天{hours}小时{minutes}分钟'
        if hours > 0:
            return f'{hours}小时{minutes}分钟'
        if minutes > 0:
            return f'{minutes}分钟'
        return f'{secs}秒'

    @staticmethod
    def get_cpu_info():
        """获取 CPU 监控信息。"""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        per_cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)
        return {
            'percent': round(cpu_percent, 1),
            'core_count': psutil.cpu_count(),
            'per_core_percent': [round(percent, 1) for percent in per_cpu_percent]
        }

    @staticmethod
    def get_memory_info():
        """获取内存监控信息。"""
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
        """获取磁盘监控信息。"""
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
        """获取系统运行基础信息。"""
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
        """聚合返回完整的监控信息。"""
        uptime_seconds = int((datetime.now() - MonitorService.service_start_time).total_seconds())
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
                'uptime_seconds': uptime_seconds,
                'uptime_display': MonitorService.format_uptime(uptime_seconds)
            }
        }

    @staticmethod
    def check_admin_permission(current_user):
        """校验监控接口访问权限，仅平台管理员可访问。"""
        if not current_user or not current_user.is_platform_admin:
            return False, '无权限查看服务监控'
        return True, None
