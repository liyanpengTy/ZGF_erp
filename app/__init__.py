from flask import Flask
from werkzeug.exceptions import NotFound, MethodNotAllowed, BadRequest
from sqlalchemy.exc import IntegrityError
from marshmallow import ValidationError
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt, cors
from app.commands import register_commands
from app.utils.response import ApiResponse
from app.extensions import (
    BusinessException,
    NotFoundException,
    DuplicateException,
    PermissionDeniedException,
    UnauthorizedException,
    ValidationException
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保中文正常显示
    app.config['JSON_AS_ASCII'] = False

    # 初始化扩展（JWT的错误处理器会在此时自动注册）
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, supports_credentials=True, origins='*')

    # 在 jwt.init_app 之后注册回调
    # 注册蓝图
    from app.api.v1 import bp as v1_bp
    app.register_blueprint(v1_bp)

    # 注册命令行命令
    register_commands(app)

    # ========== 全局异常处理 ==========

    @app.errorhandler(NotFoundException)
    def handle_not_found(e):
        return ApiResponse.not_found(e.message)

    @app.errorhandler(DuplicateException)
    def handle_duplicate(e):
        return ApiResponse.conflict(e.message)

    @app.errorhandler(PermissionDeniedException)
    def handle_permission_denied(e):
        return ApiResponse.forbidden(e.message)

    @app.errorhandler(UnauthorizedException)
    def handle_unauthorized(e):
        return ApiResponse.unauthorized(e.message)

    @app.errorhandler(ValidationException)
    def handle_validation(e):
        return ApiResponse.error(e.message, 400)

    @app.errorhandler(BusinessException)
    def handle_business(e):
        return ApiResponse.error(e.message, getattr(e, 'code', 400))

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(e):
        return ApiResponse.error(str(e.messages), 400)

    @app.errorhandler(IntegrityError)
    def handle_db_integrity_error(e):
        app.logger.error(f"数据库完整性错误: {str(e)}")
        return ApiResponse.conflict('数据重复或关联错误')

    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        return ApiResponse.error('请求参数错误', 400)

    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(e):
        return ApiResponse.error('请求方法不允许', 405)

    @app.errorhandler(404)
    def handle_404(e):
        return ApiResponse.not_found('接口不存在')

    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(e):
        return ApiResponse.unauthorized('登录已过期，请重新登录')

    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token(e):
        return ApiResponse.unauthorized('无效的认证信息')

    @app.errorhandler(Exception)
    def handle_general_exception(e):
        app.logger.error(f"未处理的异常: {type(e).__name__}: {str(e)}", exc_info=True)
        return ApiResponse.error('服务器内部错误', 500)

    return app
