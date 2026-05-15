"""奖励管理接口"""
from flask_restx import Namespace, Resource, fields
from app.api.common.auth import get_current_user
from app.utils.response import ApiResponse
from app.api.common.parsers import page_parser
from app.api.common.models import get_common_models
from app.utils.permissions import login_required, permission_required
from app.services import RewardService

reward_ns = Namespace('奖励管理-rewards', description='奖励管理')

# 获取公共模型
common = get_common_models(reward_ns)
base_response = common['base_response']
error_response = common['error_response']
unauthorized_response = common['unauthorized_response']
forbidden_response = common['forbidden_response']
page_response = common['page_response']

# ========== 请求解析器 ==========
reward_query_parser = page_parser.copy()
reward_query_parser.add_argument('username', type=str, location='args', help='用户名')
reward_query_parser.add_argument('reward_object', type=str, location='args', help='奖励对象',
                                 choices=['factory', 'personal'])

# ========== 响应模型 ==========
reward_config_item_model = reward_ns.model('RewardConfigItem', {
    'id': fields.Integer(description='奖励配置ID'),
    'name': fields.String(description='配置名称'),
    'rule_type': fields.String(description='规则类型'),
    'threshold': fields.Integer(description='阈值'),
    'reward_object': fields.String(description='奖励对象'),
    'reward_object_label': fields.String(description='奖励对象名称'),
    'reward_type': fields.String(description='奖励类型'),
    'reward_type_label': fields.String(description='奖励类型名称'),
    'reward_value': fields.Float(description='奖励值'),
    'is_active': fields.Integer(description='是否启用'),
    'remark': fields.String(description='备注')
})

reward_record_item_model = reward_ns.model('RewardRecordItem', {
    'id': fields.Integer(description='奖励记录ID'),
    'reward_object': fields.String(description='奖励对象'),
    'reward_object_label': fields.String(description='奖励对象名称'),
    'user_id': fields.Integer(description='用户ID'),
    'username': fields.String(description='用户名'),
    'factory_id': fields.Integer(description='工厂ID'),
    'factory_name': fields.String(description='工厂名称'),
    'reward_config_name': fields.String(description='奖励配置名称'),
    'reward_type': fields.String(description='奖励类型'),
    'reward_type_label': fields.String(description='奖励类型名称'),
    'reward_value': fields.Float(description='奖励值'),
    'trigger_condition': fields.String(description='触发条件'),
    'trigger_value': fields.Integer(description='触发值'),
    'status': fields.String(description='发放状态'),
    'status_label': fields.String(description='发放状态名称'),
    'distributor_name': fields.String(description='发放人名称'),
    'distributed_time': fields.String(description='发放时间'),
    'create_time': fields.String(description='创建时间')
})

reward_stats_model = reward_ns.model('RewardStats', {
    'total_pending': fields.Integer(description='待发放总数'),
    'total_distributed': fields.Integer(description='已发放总数'),
    'factory_pending': fields.Integer(description='工厂待发放数'),
    'personal_pending': fields.Integer(description='个人待发放数')
})

reward_list_data = reward_ns.model('RewardListData', {
    'items': fields.List(fields.Nested(reward_record_item_model), description='奖励记录列表'),
    'total': fields.Integer(description='总条数'),
    'page': fields.Integer(description='当前页码'),
    'page_size': fields.Integer(description='每页条数'),
    'pages': fields.Integer(description='总页数')
})

reward_config_list_response = reward_ns.clone('RewardConfigListResponse', base_response, {
    'data': fields.List(fields.Nested(reward_config_item_model), description='奖励配置列表')
})

reward_list_response = reward_ns.clone('RewardListResponse', base_response, {
    'data': fields.Nested(reward_list_data, description='奖励记录分页数据')
})

reward_stats_response = reward_ns.clone('RewardStatsResponse', base_response, {
    'data': fields.Nested(reward_stats_model, description='奖励统计数据')
})


@reward_ns.route('/configs')
class RewardConfigList(Resource):
    @login_required
    @permission_required('system:reward:view')
    @reward_ns.response(200, '成功', reward_config_list_response)
    @reward_ns.response(401, '未登录', unauthorized_response)
    @reward_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """获取奖励配置列表"""
        from app.models.system.reward_config import RewardConfig

        configs = RewardConfig.query.filter_by(is_deleted=0).order_by(RewardConfig.threshold).all()

        return ApiResponse.success([c.to_dict() for c in configs])


@reward_ns.route('/pending')
class PendingRewards(Resource):
    @login_required
    @permission_required('system:reward:distribute')
    @reward_ns.expect(reward_query_parser)
    @reward_ns.response(200, '成功', reward_list_response)
    @reward_ns.response(401, '未登录', unauthorized_response)
    @reward_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """获取待发放奖励列表"""
        args = reward_query_parser.parse_args()

        result = RewardService.get_pending_rewards(args)

        return ApiResponse.success({
            'items': [r.to_dict() for r in result['items']],
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'pages': result['pages']
        })


@reward_ns.route('/<int:reward_id>/distribute')
class DistributeReward(Resource):
    @login_required
    @permission_required('system:reward:distribute')
    @reward_ns.response(200, '发放成功', base_response)
    @reward_ns.response(404, '奖励记录不存在', error_response)
    @reward_ns.response(403, '无权限', forbidden_response)
    def post(self, reward_id):
        """发放奖励"""
        current_user = get_current_user()

        success, message = RewardService.distribute_reward(reward_id, current_user.id)

        if not success:
            return ApiResponse.error(message, 404)

        return ApiResponse.success(message=message)


@reward_ns.route('/statistics')
class RewardStatistics(Resource):
    @login_required
    @permission_required('system:reward:view')
    @reward_ns.response(200, '成功', reward_stats_response)
    @reward_ns.response(401, '未登录', unauthorized_response)
    @reward_ns.response(403, '无权限', forbidden_response)
    def get(self):
        """获取奖励统计"""
        stats = RewardService.get_reward_statistics()
        return ApiResponse.success(stats)
