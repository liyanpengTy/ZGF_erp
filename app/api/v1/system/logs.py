from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.auth.user import User
from app.models.system.log import OperationLog, LoginLog
from app.models.system.user_factory import UserFactory
from app.utils.response import ApiResponse
from app.schemas.system.log import OperationLogSchema, LoginLogSchema
from app.api.v1.shared_models import get_shared_models

log_ns = Namespace('logs', description='日志管理')

shared = get_shared_models(log_ns)
base_response = shared['base_response']
error_response = shared['error_response']
unauthorized_response = shared['unauthorized_response']
forbidden_response = shared['forbidden_response']

operation_log_query_parser = log_ns.parser()
operation_log_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
operation_log_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
operation_log_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
operation_log_query_parser.add_argument('operation', type=str, location='args', help='操作描述（模糊查询）')
operation_log_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
operation_log_query_parser.add_argument('start_time', type=str, location='args', help='开始时间（YYYY-MM-DD）')
operation_log_query_parser.add_argument('end_time', type=str, location='args', help='结束时间（YYYY-MM-DD）')
operation_log_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID（管理员使用）')

login_log_query_parser = log_ns.parser()
login_log_query_parser.add_argument('page', type=int, default=1, location='args', help='页码')
login_log_query_parser.add_argument('page_size', type=int, default=10, location='args', help='每页数量')
login_log_query_parser.add_argument('username', type=str, location='args', help='用户名（模糊查询）')
login_log_query_parser.add_argument('login_type', type=str, location='args', help='登录类型', choices=['pc', 'miniapp'])
login_log_query_parser.add_argument('status', type=int, location='args', help='状态', choices=[0, 1])
login_log_query_parser.add_argument('start_time', type=str, location='args', help='开始时间（YYYY-MM-DD）')
login_log_query_parser.add_argument('end_time', type=str, location='args', help='结束时间（YYYY-MM-DD）')
login_log_query_parser.add_argument('factory_id', type=int, location='args', help='工厂ID（管理员使用）')

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

operation_log_schema = OperationLogSchema()
operation_logs_schema = OperationLogSchema(many=True)
login_log_schema = LoginLogSchema()
login_logs_schema = LoginLogSchema(many=True)


def get_user_factory_ids(user_id):
    """获取用户关联的工厂ID列表"""
    user_factories = UserFactory.query.filter_by(user_id=user_id, status=1, is_deleted=0).all()
    return [uf.factory_id for uf in user_factories]


@log_ns.route('/operation')
class OperationLogList(Resource):
    @jwt_required()
    @log_ns.expect(operation_log_query_parser)
    @log_ns.response(200, '成功', log_list_response)
    @log_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = operation_log_query_parser.parse_args()

        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        username = args.get('username', '')
        operation = args.get('operation', '')
        status = args.get('status')
        start_time = args.get('start_time', '')
        end_time = args.get('end_time', '')

        query = OperationLog.query

        # 权限过滤
        if current_user.is_admin == 1:
            # 公司内部人员：可以指定工厂ID查看
            factory_id = args.get('factory_id')
            if factory_id:
                query = query.filter_by(factory_id=factory_id)
        else:
            # 普通用户：只能查看自己关联工厂的日志
            factory_ids = get_user_factory_ids(current_user.id)
            if factory_ids:
                query = query.filter(OperationLog.factory_id.in_(factory_ids))
            else:
                query = query.filter(OperationLog.user_id == current_user.id)

        if username:
            query = query.filter(OperationLog.username.like(f'%{username}%'))
        if operation:
            query = query.filter(OperationLog.operation.like(f'%{operation}%'))
        if status is not None:
            query = query.filter_by(status=status)
        if start_time:
            query = query.filter(OperationLog.create_time >= start_time)
        if end_time:
            query = query.filter(OperationLog.create_time <= end_time)

        pagination = query.order_by(OperationLog.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': operation_logs_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })


@log_ns.route('/operation/<int:log_id>')
class OperationLogDetail(Resource):
    @jwt_required()
    @log_ns.response(200, '成功', base_response)
    @log_ns.response(404, '日志不存在', error_response)
    def get(self, log_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        log = OperationLog.query.get(log_id)
        if not log:
            return ApiResponse.error('日志不存在')

        # 权限验证
        if current_user.is_admin == 1:
            pass
        else:
            factory_ids = get_user_factory_ids(current_user.id)
            if log.factory_id not in factory_ids and log.user_id != current_user.id:
                return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(operation_log_schema.dump(log))


@log_ns.route('/login')
class LoginLogList(Resource):
    @jwt_required()
    @log_ns.expect(login_log_query_parser)
    @log_ns.response(200, '成功', log_list_response)
    @log_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        args = login_log_query_parser.parse_args()

        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        page = args['page']
        page_size = args['page_size']
        username = args.get('username', '')
        login_type = args.get('login_type', '')
        status = args.get('status')
        start_time = args.get('start_time', '')
        end_time = args.get('end_time', '')

        query = LoginLog.query

        # 权限过滤
        if current_user.is_admin == 1:
            factory_id = args.get('factory_id')
            if factory_id:
                # 获取该工厂下的用户ID列表
                user_ids = db.session.query(UserFactory.user_id).filter_by(
                    factory_id=factory_id, status=1, is_deleted=0
                ).all()
                user_ids = [u[0] for u in user_ids]
                if user_ids:
                    query = query.filter(LoginLog.user_id.in_(user_ids))
        else:
            query = query.filter_by(user_id=current_user.id)

        if username:
            query = query.filter(LoginLog.username.like(f'%{username}%'))
        if login_type:
            query = query.filter_by(login_type=login_type)
        if status is not None:
            query = query.filter_by(status=status)
        if start_time:
            query = query.filter(LoginLog.create_time >= start_time)
        if end_time:
            query = query.filter(LoginLog.create_time <= end_time)

        pagination = query.order_by(LoginLog.id.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return ApiResponse.success({
            'items': login_logs_schema.dump(pagination.items),
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        })


@log_ns.route('/login/<int:log_id>')
class LoginLogDetail(Resource):
    @jwt_required()
    @log_ns.response(200, '成功', base_response)
    @log_ns.response(404, '日志不存在', error_response)
    def get(self, log_id):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        log = LoginLog.query.get(log_id)
        if not log:
            return ApiResponse.error('日志不存在')

        if current_user.is_admin != 1 and log.user_id != current_user.id:
            return ApiResponse.error('无权限查看', 403)

        return ApiResponse.success(login_log_schema.dump(log))


@log_ns.route('/stats')
class LogStats(Resource):
    @jwt_required()
    @log_ns.response(200, '成功', stats_response)
    @log_ns.response(401, '未登录', unauthorized_response)
    def get(self):
        identity = get_jwt_identity()
        current_user_id = identity.get('user_id') if isinstance(identity, dict) else int(identity)
        current_user = User.query.filter_by(id=current_user_id, is_deleted=0).first()

        if not current_user:
            return ApiResponse.error('用户不存在')

        from sqlalchemy import func

        query_op = OperationLog.query
        query_login = LoginLog.query

        if current_user.is_admin == 1:
            pass
        else:
            factory_ids = get_user_factory_ids(current_user.id)
            if factory_ids:
                query_op = query_op.filter(OperationLog.factory_id.in_(factory_ids))
                query_login = query_login.filter(LoginLog.user_id == current_user.id)
            else:
                query_op = query_op.filter_by(user_id=current_user.id)
                query_login = query_login.filter_by(user_id=current_user.id)

        today = func.date(OperationLog.create_time) == func.current_date()
        today_op_count = query_op.filter(today).count()

        today_login_count = query_login.filter(today).count()
        today_success_login = query_login.filter(today, LoginLog.status == 1).count()
        today_fail_login = query_login.filter(today, LoginLog.status == 0).count()

        return ApiResponse.success({
            'today_operation_count': today_op_count,
            'today_login_count': today_login_count,
            'today_success_login': today_success_login,
            'today_fail_login': today_fail_login
        })
