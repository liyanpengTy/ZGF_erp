import sys
from pathlib import Path
from functools import wraps
from flask import request
from loguru import logger
from app.config import get_config

config = get_config()

# 创建日志目录
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# 移除默认处理器
logger.remove()

# 添加控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=config.LOG_LEVEL,
    colorize=True
)

# 添加文件输出
logger.add(
    log_dir / 'zgf_erp_{time:YYYY-MM-DD}.log',
    rotation='1 day',
    retention='30 days',
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level='INFO',
    encoding='utf-8'
)

# 添加错误日志单独文件
logger.add(
    log_dir / 'error_{time:YYYY-MM-DD}.log',
    rotation='1 day',
    retention='30 days',
    level='ERROR',
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    encoding='utf-8'
)


def log_operation(operation_name):
    """操作日志装饰器"""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from app.extensions import db
            from app.models.system.log import OperationLog
            import time

            # 记录开始时间
            start_time = time.time()

            # 获取请求信息
            user_id = None
            username = None
            factory_id = None

            try:
                from flask_jwt_extended import get_jwt_identity
                user_id = get_jwt_identity()
                if user_id:
                    from app.models.auth.user import User
                    user = User.query.get(int(user_id))
                    if user:
                        username = user.username
                        factory_id = user.factory_id
            except:
                pass

            # 执行原函数
            try:
                response = fn(*args, **kwargs)
                status = 1
                error_msg = None
            except Exception as e:
                status = 0
                error_msg = str(e)
                raise
            finally:
                # 计算耗时
                duration = int((time.time() - start_time) * 1000)

                # 保存操作日志
                try:
                    log = OperationLog(
                        user_id=int(user_id) if user_id else None,
                        username=username,
                        factory_id=factory_id,
                        operation=operation_name,
                        method=request.method,
                        url=request.path,
                        params=str(request.get_json())[:500] if request.is_json else str(request.args)[:500],
                        ip=request.remote_addr,
                        duration=duration,
                        status=status,
                        error_msg=error_msg
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"保存操作日志失败: {e}")

            return response

        return wrapper

    return decorator


def log_login(username, login_type, status, error_msg=None, user_id=None):
    """记录登录日志"""
    from app.extensions import db
    from app.models.system.log import LoginLog
    from flask import request

    try:
        log = LoginLog(
            user_id=user_id,
            username=username,
            login_type=login_type,
            ip=request.remote_addr,
            status=status,
            error_msg=error_msg
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"保存登录日志失败: {e}")


# 导出logger实例
app_logger = logger
