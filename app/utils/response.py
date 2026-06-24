"""统一 API 响应结构工具。"""


class ApiResponse:
    """封装接口成功与失败的标准返回格式。"""

    @staticmethod
    def success(data=None, message='操作成功', code=200):
        """返回标准成功响应。"""
        return {
            'code': code,
            'message': message,
            'data': data,
            'success': True,
        }, code

    @staticmethod
    def success_list(items, message='操作成功', code=200):
        """返回标准列表成功响应。"""
        return ApiResponse.success(data=items, message=message, code=code)

    @staticmethod
    def success_page(items, total, page, page_size, pages, message='操作成功', extra=None, code=200):
        """返回标准分页成功响应，可附带额外统计字段。"""
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
        """根据统一分页结果对象返回标准分页响应。"""
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
    def success_serialized_page(result, serializer, message='操作成功', extra=None, code=200):
        """序列化分页结果中的 items 后返回标准分页响应。"""
        return ApiResponse.success_page_result(
            result,
            [serializer(item) for item in result['items']],
            message=message,
            extra=extra,
            code=code,
        )

    @staticmethod
    def success_mapped_page(result, items, message='操作成功', extra=None, code=200):
        """使用已转换好的 items 返回标准分页响应。"""
        return ApiResponse.success_page_result(
            result,
            items,
            message=message,
            extra=extra,
            code=code,
        )

    @staticmethod
    def error(message='操作失败', code=400, data=None):
        """返回标准失败响应。"""
        return {
            'code': code,
            'message': message,
            'data': data,
            'success': False,
        }, code

    @staticmethod
    def unauthorized(message='未登录或 token 已过期', code=401):
        """返回未授权响应。"""
        return ApiResponse.error(message=message, code=code)

    @staticmethod
    def forbidden(message='无权限访问', code=403):
        """返回无权限响应。"""
        return ApiResponse.error(message=message, code=code)

    @staticmethod
    def not_found(message='资源不存在', code=404):
        """返回资源不存在响应。"""
        return ApiResponse.error(message=message, code=code)

    @staticmethod
    def conflict(message='数据冲突', code=409):
        """返回数据冲突响应。"""
        return ApiResponse.error(message=message, code=code)
