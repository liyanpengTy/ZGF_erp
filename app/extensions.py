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
    """请求中没有携带token"""
    return ApiResponse.unauthorized('未登录或token已过期')


@jwt.invalid_token_loader
def invalid_token_response(callback):
    """token无效（格式错误、签名错误等）"""
    return ApiResponse.unauthorized('无效的token')


@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    """token已过期"""
    return ApiResponse.unauthorized('token已过期')


@jwt.revoked_token_loader
def revoked_token_response(jwt_header, jwt_payload):
    """token已被撤销"""
    return ApiResponse.unauthorized('token已失效')