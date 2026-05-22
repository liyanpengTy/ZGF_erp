"""日志工具与审计日志辅助方法。"""

import json
import sys
from functools import wraps
from pathlib import Path

from flask import request
from loguru import logger

from app.config import get_config

config = get_config()

log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
    level=config.LOG_LEVEL,
    colorize=True,
)

logger.add(
    log_dir / 'zgf_erp_{time:YYYY-MM-DD}.log',
    rotation='1 day',
    retention='30 days',
    format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
    level='INFO',
    encoding='utf-8',
)

logger.add(
    log_dir / 'error_{time:YYYY-MM-DD}.log',
    rotation='1 day',
    retention='30 days',
    level='ERROR',
    format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
    encoding='utf-8',
)

SENSITIVE_FIELD_NAMES = {
    'password',
    'old_password',
    'new_password',
    'confirm_password',
    'access_token',
    'refresh_token',
    'token',
    'authorization',
}


def is_sensitive_field(field_name):
    """判断字段名是否属于需要脱敏的敏感字段。"""
    normalized = str(field_name or '').strip().lower()
    return normalized in SENSITIVE_FIELD_NAMES or normalized.endswith('_token') or 'password' in normalized


def sanitize_payload(payload):
    """递归脱敏请求参数，避免密码、令牌等敏感内容落日志。"""
    if isinstance(payload, dict):
        return {
            key: '***' if is_sensitive_field(key) else sanitize_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return [sanitize_payload(item) for item in payload]
    return payload


def serialize_request_params():
    """序列化当前请求参数，并在序列化前完成脱敏处理。"""
    if request.is_json:
        payload = request.get_json(silent=True)
    else:
        payload = request.args.to_dict(flat=False)
        payload = {
            key: value[0] if len(value) == 1 else value
            for key, value in payload.items()
        }

    sanitized = sanitize_payload(payload)
    return json.dumps(sanitized, ensure_ascii=False, default=str)[:500]


def log_operation(operation_name):
    """操作日志装饰器。"""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            import time

            from app.extensions import db
            from app.models.system.log import OperationLog

            start_time = time.time()

            user_id = None
            username = None
            factory_id = None

            try:
                from flask_jwt_extended import get_jwt, get_jwt_identity

                identity = get_jwt_identity()
                claims = get_jwt()
                user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
                factory_id = claims.get('factory_id')

                if user_id:
                    from app.models.auth.user import User

                    user = User.query.get(int(user_id))
                    if user:
                        username = user.username
            except Exception:
                pass

            try:
                response = fn(*args, **kwargs)
                status = 1
                error_msg = None
            except Exception as exc:
                status = 0
                error_msg = str(exc)
                raise
            finally:
                duration = int((time.time() - start_time) * 1000)

                try:
                    log = OperationLog(
                        user_id=int(user_id) if user_id else None,
                        username=username,
                        factory_id=factory_id,
                        operation=operation_name,
                        method=request.method,
                        url=request.path,
                        params=serialize_request_params(),
                        ip=request.remote_addr,
                        duration=duration,
                        status=status,
                        error_msg=error_msg,
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception as exc:
                    logger.error(f'保存操作日志失败: {exc}')

            return response

        return wrapper

    return decorator


def log_login(username, login_type, status, error_msg=None, user_id=None):
    """记录登录日志。"""
    from app.extensions import db
    from app.models.system.log import LoginLog

    try:
        log = LoginLog(
            user_id=user_id,
            username=username,
            login_type=login_type,
            ip=request.remote_addr,
            status=status,
            error_msg=error_msg,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as exc:
        logger.error(f'保存登录日志失败: {exc}')


app_logger = logger
