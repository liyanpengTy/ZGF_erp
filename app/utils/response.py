from flask import jsonify


class ApiResponse:
    """统一API响应格式"""

    @staticmethod
    def success(data=None, message='操作成功', code=200):
        # 不要使用 jsonify，直接返回字典
        return {
            'code': code,
            'message': message,
            'data': data,
            'success': True
        }, code

    @staticmethod
    def error(message='操作失败', code=400, data=None):
        return {
            'code': code,
            'message': message,
            'data': data,
            'success': False
        }, code

    @staticmethod
    def unauthorized(message='未登录或token已过期', code=401):
        return {
            'code': code,
            'message': message,
            'success': False
        }, code

    @staticmethod
    def forbidden(message='无权限访问', code=403):
        return {
            'code': code,
            'message': message,
            'success': False
        }, code

    @staticmethod
    def not_found(message='资源不存在', code=404):
        return {
            'code': code,
            'message': message,
            'success': False
        }, code

    @staticmethod
    def conflict(message='数据冲突', code=409):
        return {
            'code': code,
            'message': message,
            'success': False
        }, code
