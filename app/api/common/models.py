from flask_restx import fields


def build_page_data_model(ns, name, item_model, extra_fields=None, items_description='列表数据'):
    """构建统一分页数据模型。"""
    payload = {
        'items': fields.List(fields.Nested(item_model), description=items_description),
        'total': fields.Integer(description='总条数', example=1),
        'page': fields.Integer(description='当前页码', example=1),
        'page_size': fields.Integer(description='每页条数', example=10),
        'pages': fields.Integer(description='总页数', example=1)
    }
    if extra_fields:
        payload.update(extra_fields)
    return ns.model(name, payload)


def build_page_response_model(ns, name, base_response, page_data_model, data_description='分页数据'):
    """构建统一分页响应模型。"""
    return ns.clone(name, base_response, {
        'data': fields.Nested(page_data_model, description=data_description)
    })


def get_common_models(ns):
    """获取公共响应模型（v1和v2共用）"""

    base_response = ns.model('BaseResponse', {
        'code': fields.Integer(description='业务状态码', example=200),
        'message': fields.String(description='响应消息', example='操作成功'),
        'data': fields.Raw(description='响应数据'),
        'success': fields.Boolean(description='是否成功', example=True)
    })

    error_response = ns.model('ErrorResponse', {
        'code': fields.Integer(description='业务状态码', example=400),
        'message': fields.String(description='错误消息', example='操作失败'),
        'data': fields.Raw(description='错误上下文数据'),
        'success': fields.Boolean(description='是否成功', example=False)
    })

    unauthorized_response = ns.model('UnauthorizedResponse', {
        'code': fields.Integer(description='业务状态码', example=401),
        'message': fields.String(description='错误消息', example='未登录或 token 已过期'),
        'data': fields.Raw(description='错误上下文数据'),
        'success': fields.Boolean(description='是否成功', example=False)
    })

    forbidden_response = ns.model('ForbiddenResponse', {
        'code': fields.Integer(description='业务状态码', example=403),
        'message': fields.String(description='错误消息', example='无权限访问'),
        'data': fields.Raw(description='错误上下文数据'),
        'success': fields.Boolean(description='是否成功', example=False)
    })

    # 分页数据模型
    page_item_model = ns.model('PageItem', {
        'value': fields.Raw(description='通用分页占位项')
    })
    page_data = build_page_data_model(ns, 'PageData', page_item_model, items_description='通用分页占位列表')

    page_response = build_page_response_model(ns, 'PageResponse', base_response, page_data, data_description='通用分页响应数据')

    return {
        'base_response': base_response,
        'error_response': error_response,
        'unauthorized_response': unauthorized_response,
        'forbidden_response': forbidden_response,
        'page_response': page_response,
        'build_page_data_model': build_page_data_model,
        'build_page_response_model': build_page_response_model
    }
