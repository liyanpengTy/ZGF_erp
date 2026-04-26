from flask import Flask
from werkzeug.exceptions import NotFound
from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt, cors
from app.commands import register_commands
from app.utils.response import ApiResponse
from jwt.exceptions import DecodeError, PyJWTError
from flask_jwt_extended.exceptions import NoAuthorizationError, JWTExtendedException


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 确保中文正常显示
    app.config['JSON_AS_ASCII'] = False

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, supports_credentials=True, origins='*')

    # 注册蓝图
    from app.api.v1 import bp as v1_bp
    app.register_blueprint(v1_bp)

    # 注册命令行命令
    register_commands(app)

    # ========== 错误处理器 ==========

    @app.errorhandler(404)
    def not_found(error):
        return ApiResponse.error('接口不存在', 404)

    # JWT: 未提供认证信息（没有token或Authorization头缺失）
    @app.errorhandler(NoAuthorizationError)
    def handle_no_authorization(e):
        app.logger.info(f"未提供认证信息: {str(e)}")
        # 使用 unauthorized 方法返回401
        return ApiResponse.unauthorized('请先登录获取token')

    # JWT: Token解码错误（格式不正确）
    @app.errorhandler(DecodeError)
    def handle_decode_error(e):
        app.logger.info(f"Token解码错误: {str(e)}")
        if "Not enough segments" in str(e):
            return ApiResponse.unauthorized('Token格式错误，请重新登录获取新token')
        return ApiResponse.unauthorized('Token格式无效')

    # JWT: 扩展异常（包括过期等）
    @app.errorhandler(JWTExtendedException)
    def handle_jwt_extended_error(e):
        app.logger.info(f"JWT扩展异常: {type(e).__name__} - {str(e)}")
        error_msg = str(e)
        if "Expired" in error_msg or "过期" in error_msg:
            return ApiResponse.unauthorized('登录已过期，请重新登录')
        elif "Invalid" in error_msg or "无效" in error_msg:
            return ApiResponse.unauthorized('无效的登录凭证')
        return ApiResponse.unauthorized('认证失败')

    # PyJWT 通用错误
    @app.errorhandler(PyJWTError)
    def handle_pyjwt_error(e):
        app.logger.info(f"PyJWT错误: {str(e)}")
        return ApiResponse.unauthorized('登录凭证无效')

    # 全局错误处理
    @app.errorhandler(Exception)
    def handle_exception(e):
        # 如果是 404 错误，交给 not_found 处理
        if isinstance(e, NotFound):
            return not_found(e)
        app.logger.error(f"全局错误: {str(e)}")
        return ApiResponse.error(str(e), 500)

    app.logger.info("=== 错误处理器已注册 ===")
    app.logger.info(f"NoAuthorizationError handler: {app.error_handler_spec.get(None, {}).get(NoAuthorizationError)}")

    return app
