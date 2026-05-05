from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()


"""自定义异常类"""


class BusinessException(Exception):
    """业务异常基类"""
    def __init__(self, message, code=400):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundException(BusinessException):
    """资源不存在异常"""
    def __init__(self, message='资源不存在'):
        super().__init__(message, 404)


class DuplicateException(BusinessException):
    """数据重复异常"""
    def __init__(self, message='数据已存在'):
        super().__init__(message, 409)


class PermissionDeniedException(BusinessException):
    """权限不足异常"""
    def __init__(self, message='无权限操作'):
        super().__init__(message, 403)


class UnauthorizedException(BusinessException):
    """未认证异常"""
    def __init__(self, message='请先登录'):
        super().__init__(message, 401)


class ValidationException(BusinessException):
    """参数验证异常"""
    def __init__(self, message='参数错误'):
        super().__init__(message, 400)