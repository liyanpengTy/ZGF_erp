from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
# from flask_restx import Api
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from app.utils.response import ApiResponse

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()


# JWT 错误处理 - 关键修改：直接返回元组
@jwt.unauthorized_loader
def unauthorized_response(callback):
    return ApiResponse.unauthorized()


@jwt.invalid_token_loader
def invalid_token_response(callback):
    return ApiResponse.unauthorized('无效的token')


@jwt.expired_token_loader
def expired_token_response(callback):
    return ApiResponse.unauthorized('token已过期')


@jwt.revoked_token_loader
def revoked_token_response(callback):
    return ApiResponse.unauthorized('token已失效')
