from flask import jsonify


class ApiResponse:
    """统一API响应格式"""

    @staticmethod
    def success(data=None, message='操作成功', code=200):
        response = {
            'code': code,
            'message': message,
            'data': data,
            'success': True
        }
        return response, code

    @staticmethod
    def error(message='操作失败', code=400, data=None):
        response = {
            'code': code,
            'message': message,
            'data': data,
            'success': False
        }
        return response, code

    @staticmethod
    def unauthorized(message='未登录或token已过期', code=401):
        response = {
            'code': code,
            'message': message,
            'data': None,
            'success': False
        }
        return response, code

    @staticmethod
    def forbidden(message='无权限访问', code=403):
        response = {
            'code': code,
            'message': message,
            'data': None,
            'success': False
        }
        return response, code
