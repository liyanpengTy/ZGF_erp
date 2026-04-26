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
    # from app.api.v2 import bp as v2_bp

    app.register_blueprint(v1_bp)
    # app.register_blueprint(v2_bp)

    # 注册命令行命令
    register_commands(app)

    # 404 错误处理（针对 favicon.ico 等不存在的路径）
    @app.errorhandler(404)
    def not_found(error):
        return ApiResponse.error('接口不存在', 404)

    @app.errorhandler(DecodeError)
    @app.errorhandler(PyJWTError)
    @app.errorhandler(NoAuthorizationError)
    @app.errorhandler(JWTExtendedException)
    def handle_jwt_exception(e):
        """处理 JWT 相关异常"""
        app.logger.info(f"JWT 异常: {type(e).__name__}")
        return ApiResponse.unauthorized('无效的token')

    # 全局错误处理（排除 404）
    @app.errorhandler(Exception)
    def handle_exception(e):
        # 如果是 404 错误，交给 not_found 处理
        if isinstance(e, NotFound):
            return not_found(e)
        app.logger.error(f"全局错误: {str(e)}")
        return ApiResponse.error(str(e), 500)

    return app
