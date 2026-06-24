"""蓝图注册。"""


def register_blueprints(app):
    """注册业务蓝图。"""
    from app.api.v1 import bp as v1_bp

    app.register_blueprint(v1_bp)
