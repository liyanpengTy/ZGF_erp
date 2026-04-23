from flask_restx import fields


def get_shared_models(ns):
    """为指定命名空间创建共享响应模型"""

    base_response = ns.model('BaseResponse', {
        'code': fields.Integer(example=200),
        'message': fields.String(example='操作成功'),
        'data': fields.Raw(),
        'success': fields.Boolean(example=True)
    })

    error_response = ns.model('ErrorResponse', {
        'code': fields.Integer(example=400),
        'message': fields.String(example='操作失败'),
        'data': fields.Raw(),
        'success': fields.Boolean(example=False)
    })

    unauthorized_response = ns.model('UnauthorizedResponse', {
        'code': fields.Integer(example=401),
        'message': fields.String(example='未登录或token已过期'),
        'data': fields.Raw(),
        'success': fields.Boolean(example=False)
    })

    forbidden_response = ns.model('ForbiddenResponse', {
        'code': fields.Integer(example=403),
        'message': fields.String(example='无权限访问'),
        'data': fields.Raw(),
        'success': fields.Boolean(example=False)
    })

    return {
        'base_response': base_response,
        'error_response': error_response,
        'unauthorized_response': unauthorized_response,
        'forbidden_response': forbidden_response
    }
