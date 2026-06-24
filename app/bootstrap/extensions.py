"""扩展组件注册。"""

from app.extensions import bcrypt, cors, db, jwt, migrate


def register_extensions(app):
    """初始化扩展组件。"""
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True, compare_server_default=False)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS'],
        origins=app.config['CORS_ORIGINS'],
    )
