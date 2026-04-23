from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt, cors
from app.commands import register_commands
from app.utils.response import ApiResponse


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

    # 全局错误处理
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"全局错误: {str(e)}")
        return ApiResponse.error(str(e), 500)

    return app
