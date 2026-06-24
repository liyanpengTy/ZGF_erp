"""全局异常处理注册。"""

from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from app.core.exceptions import (
    BusinessException,
    DuplicateException,
    NotFoundException,
    PermissionDeniedException,
    UnauthorizedException,
    ValidationException,
)
from app.utils.response import ApiResponse


def register_error_handlers(app):
    """注册全局异常处理器。"""

    @app.errorhandler(NotFoundException)
    def handle_not_found(error):
        return ApiResponse.not_found(error.message)

    @app.errorhandler(DuplicateException)
    def handle_duplicate(error):
        return ApiResponse.conflict(error.message)

    @app.errorhandler(PermissionDeniedException)
    def handle_permission_denied(error):
        return ApiResponse.forbidden(error.message)

    @app.errorhandler(UnauthorizedException)
    def handle_unauthorized(error):
        return ApiResponse.unauthorized(error.message)

    @app.errorhandler(ValidationException)
    def handle_validation(error):
        return ApiResponse.error(error.message, 400)

    @app.errorhandler(BusinessException)
    def handle_business(error):
        return ApiResponse.error(error.message, getattr(error, 'code', 400))

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(error):
        return ApiResponse.error(str(error.messages), 400)

    @app.errorhandler(IntegrityError)
    def handle_db_integrity_error(error):
        app.logger.error(f'数据库完整性错误: {error}')
        return ApiResponse.conflict('数据重复或关联错误')

    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        return ApiResponse.error('请求参数错误', 400)

    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(error):
        return ApiResponse.error('请求方法不允许', 405)

    @app.errorhandler(404)
    def handle_404(error):
        return ApiResponse.not_found('接口不存在')

    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(error):
        return ApiResponse.unauthorized('登录已过期，请重新登录')

    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(error):
        return ApiResponse.unauthorized('无效的认证信息')

    @app.errorhandler(Exception)
    def handle_general_exception(error):
        app.logger.error(f'未处理异常: {type(error).__name__}: {error}', exc_info=True)
        return ApiResponse.error('服务器内部错误', 500)
