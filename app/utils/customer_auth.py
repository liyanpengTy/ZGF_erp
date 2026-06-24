"""客户端 JWT 认证工具。"""

from functools import wraps

from flask_jwt_extended import get_jwt, verify_jwt_in_request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.models.customer.customer import CustomerUser
from app.utils.response import ApiResponse


def get_current_customer():
    """从当前 JWT claims 中解析客户账号。"""
    try:
        claims = get_jwt()
        if claims.get('account_type') != 'customer':
            return None
        customer_id = claims.get('customer_id')
        if not customer_id:
            return None
        return CustomerUser.query.filter_by(id=customer_id, status='active', is_deleted=0).first()
    except Exception:
        return None


def customer_login_required(fn):
    """客户端登录验证装饰器，仅允许 customer_user 账号访问。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            customer = get_current_customer()
            if not customer:
                return ApiResponse.unauthorized('客户账号不存在或已被禁用')
            return fn(*args, **kwargs)
        except ExpiredSignatureError:
            return ApiResponse.unauthorized('登录已过期，请重新登录')
        except InvalidTokenError:
            return ApiResponse.unauthorized('无效的认证信息，请重新登录')
        except Exception as exc:
            error_text = str(exc)
            if 'Missing' in error_text:
                return ApiResponse.unauthorized('请登录')
            return ApiResponse.unauthorized(f'认证失败: {error_text}')

    return wrapper
