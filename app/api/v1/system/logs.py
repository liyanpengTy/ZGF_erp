"""日志管理接口"""
from flask_restx import Namespace, Resource, fields
from app.api.common.auth import get_current_user
from app.utils.response import ApiResponse
from app.api.common.parsers import page_with_date_parser
from app.api.common.models import get_common_models
from app.utils.permissions import login_required
from app.services import LogService
from app.schemas.system.log import OperationLogSchema, LoginLogSchema

log_ns = Namespace('日志管理-logs', description='日志管理')

common = get_common_models(log_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
page_response = common['page_response']

# ========== 操作日志请求解析器 ==========
operation_log_query_parser = page_with_date_parser.copy()
operation_log_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
operation_log_query_parser.add_argument('operation', type=str, location='args', help='操作描述（模糊查询）')
operation_log_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
operation_log_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID（管理员使用）')

# ========== 登录日志请求解析器 ==========
login_log_query_parser = page_with_date_parser.copy()
login_log_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
login_log_query_parser.add_argument('login_type', type=str, location='args', help='登录类型', choices=['pc', 'miniapp'])
login_log_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
login_log_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID（管理员使用）')


# ========== 响应模型 ==========
operation_log_item_model = log_ns.model('OperationLogItem', {
    'id': fields.Integer(),
    'user_id': fields.Integer(),
    'username': fields.String(),
    'factory_id': fields.Integer(),
    'operation': fields.String(),
    'method': fields.String(),
    'url': fields.String(),
    'params': fields.String(),
    'ip': fields.String(),
    'duration': fields.Integer(),
    'status': fields.Integer(),
    'error_msg': fields.String(),
    'create_time': fields.String()
})

login_log_item_model = log_ns.model('LoginLogItem', {
    'id': fields.Integer(),
    'user_id': fields.Integer(),
    'username': fields.String(),
    'login_type': fields.String(),
    'ip': fields.String(),
    'status': fields.Integer(),
    'error_msg': fields.String(),
    'create_time': fields.String()
})

log_list_data = log_ns.model('LogListData', {
    'items': fields.List(fields.Raw),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

stats_data = log_ns.model('StatsData', {
    'today_operation_count': fields.Integer(),
    'today_login_count': fields.Integer(),
    'today_success_login': fields.Integer(),
    'today_fail_login': fields.Integer()
})

log_list_response = log_ns.clone('LogListResponse', base_response, {
    'data': fields.Nested(log_list_data)
})

stats_response = log_ns.clone('StatsResponse', base_response, {
    'data': fields.Nested(stats_data)
})

# ========== Schema 初始化 ==========
operation_log_schema = OperationLogSchema()
operation_logs_schema = OperationLogSchema(many=True)
login_log_schema = LoginLogSchema()
login_logs_schema = LoginLogSchema(many=True)


@log_ns.route('/operation')
class OperationLogList(Resource):
    @login_required
    @log_ns.expect(operation_log_query_parser)
    @log_ns.response(200, '成功', log_list_response)
    @log_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """操作日志列表"""
        args = operation_log_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = LogService.get_operation_log_list(current_user, args)

        return ApiResponse.success({
            'items': operation_logs_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })


@log_ns.route('/operation/<int:log_id>')
class OperationLogDetail(Resource):
    @login_required
    @log_ns.response(200, '成功', base_response)
    @log_ns.response(404, '日志不存在', error_response)
    def get(self, log_id):
        """操作日志详情"""
        current_user = get_current_user()

        log = LogService.get_operation_log_by_id(log_id)
        if not log:
            return ApiResponse.error('日志不存在')

        has_permission, error = LogService.check_operation_log_permission(current_user, log)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(operation_log_schema.dump(log))


@log_ns.route('/login')
class LoginLogList(Resource):
    @login_required
    @log_ns.expect(login_log_query_parser)
    @log_ns.response(200, '成功', log_list_response)
    @log_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """登录日志列表"""
        args = login_log_query_parser.parse_args()
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        result = LogService.get_login_log_list(current_user, args)

        return ApiResponse.success({
            'items': login_logs_schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })


@log_ns.route('/login/<int:log_id>')
class LoginLogDetail(Resource):
    @login_required
    @log_ns.response(200, '成功', base_response)
    @log_ns.response(404, '日志不存在', error_response)
    def get(self, log_id):
        """登录日志详情"""
        current_user = get_current_user()

        log = LogService.get_login_log_by_id(log_id)
        if not log:
            return ApiResponse.error('日志不存在')

        has_permission, error = LogService.check_login_log_permission(current_user, log)
        if not has_permission:
            return ApiResponse.error(error, 403)

        return ApiResponse.success(login_log_schema.dump(log))


@log_ns.route('/stats')
class LogStats(Resource):
    @login_required
    @log_ns.response(200, '成功', stats_response)
    @log_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        """日志统计"""
        current_user = get_current_user()

        if not current_user:
            return ApiResponse.error('用户不存在')

        stats = LogService.get_log_stats(current_user)

        return ApiResponse.success(stats)
