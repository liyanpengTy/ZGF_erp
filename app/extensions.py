from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from app.utils.response import ApiResponse
import logging

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()
logger = logging.getLogger(__name__)


@jwt.unauthorized_loader
def unauthorized_response(callback):
    """请求中没有携带token时返回"""
    logger.info("JWT invalid_token_response 被触发！")
    return ApiResponse.unauthorized('请先登录获取token')


@jwt.invalid_token_loader
def invalid_token_response(error):
    """token无效时返回（格式错误、签名错误等）"""
    # 针对不同的错误返回不同的提示
    logger.info("JWT invalid_token_response 被触发！")
    if "Not enough segments" in str(error):
        return ApiResponse.unauthorized('Token格式错误，请重新登录')
    return ApiResponse.unauthorized('无效的token，请重新登录')


@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    """token已过期时返回"""
    logger.info("JWT invalid_token_response 被触发！")
    return ApiResponse.unauthorized('登录已过期，请重新登录')


@jwt.revoked_token_loader
def revoked_token_response(jwt_header, jwt_payload):
    """token已被撤销时返回"""
    logger.info("JWT invalid_token_response 被触发！")
    return ApiResponse.unauthorized('token已失效，请重新登录')


@jwt.needs_fresh_token_loader
def needs_fresh_token_response(jwt_header, jwt_payload):
    """需要新鲜token时返回"""
    logger.info("JWT invalid_token_response 被触发！")
    return ApiResponse.unauthorized('需要重新登录以获取新token')


# 可选：添加token刷新时的错误处理
@jwt.revoked_token_loader
def revoked_token_response(jwt_header, jwt_payload):
    """token被撤销时的处理"""
    logger.info("JWT invalid_token_response 被触发！")
    return ApiResponse.unauthorized('token已被撤销，请重新登录')


# 可选：添加额外的claims验证
# @jwt.additional_claims_loader
# def add_claims_to_access_token(identity):
#     """添加自定义claims到token"""
#     # 兼容多种 identity 类型
#     if isinstance(identity, str):
#         # 如果是字符串，直接转换为整数
#         return {'user_id': int(identity)}
#     elif isinstance(identity, dict):
#         # 如果是字典，取出 user_id
#         return {'user_id': identity.get('user_id')}
#     elif isinstance(identity, int):
#         # 如果是整数，直接使用
#         return {'user_id': identity}
#     else:
#         # 其他情况返回空
#         return {}
