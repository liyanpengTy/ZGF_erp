class ApiResponse:
    """统一 API 响应格式。"""

    @staticmethod
    def success(data=None, message='操作成功', code=200):
        return {
            'code': code,
            'message': message,
            'data': data,
            'success': True
        }, code

    @staticmethod
    def success_list(items, message='操作成功', code=200):
        """返回统一的列表成功响应。"""
        return ApiResponse.success(data=items, message=message, code=code)

    @staticmethod
    def success_page(items, total, page, page_size, pages, message='操作成功', extra=None, code=200):
        """返回统一的分页成功响应，可附带额外统计字段。"""
        data = {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': pages,
        }
        if extra:
            data.update(extra)
        return ApiResponse.success(data=data, message=message, code=code)

    @staticmethod
    def success_page_result(result, items, message='操作成功', extra=None, code=200):
        """根据统一分页结果对象返回成功响应。"""
        return ApiResponse.success_page(
            items=items,
            total=result['total'],
            page=result['page'],
            page_size=result['page_size'],
            pages=result['pages'],
            message=message,
            extra=extra,
            code=code,
        )

    @staticmethod
    def error(message='操作失败', code=400, data=None):
        return {
            'code': code,
            'message': message,
            'data': data,
            'success': False
        }, code

    @staticmethod
    def unauthorized(message='未登录或 token 已过期', code=401):
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
