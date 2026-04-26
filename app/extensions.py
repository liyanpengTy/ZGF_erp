from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from app.utils.response import ApiResponse

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()


# JWT 错误处理
@jwt.unauthorized_loader
def unauthorized_response(callback):
    return ApiResponse.unauthorized('未登录或token已过期')


@jwt.invalid_token_loader
def invalid_token_response(callback):
    return ApiResponse.unauthorized('无效的token')


# ✅ 修正：需要2个参数
@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    return ApiResponse.unauthorized('token已过期')


@jwt.revoked_token_loader
def revoked_token_response(jwt_header, jwt_payload):
    return ApiResponse.unauthorized('token已失效')
