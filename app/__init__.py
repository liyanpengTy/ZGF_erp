from flask import Flask
from werkzeug.exceptions import NotFound
from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt, cors
from app.commands import register_commands
from app.utils.response import ApiResponse


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

    @app.errorhandler(404)
    def not_found(error):
        """404 接口不存在"""
        return ApiResponse.error('接口不存在', 404)

    @app.errorhandler(Exception)
    def handle_exception(e):
        """全局异常处理（兜底）"""
        # 如果是 404 错误，交给 not_found 处理
        if isinstance(e, NotFound):
            return not_found(e)

        # 记录错误日志
        app.logger.error(f"未处理的异常: {str(e)}", exc_info=True)

        # 返回友好的错误信息
        return ApiResponse.error('服务器内部错误', 500)

    return app
