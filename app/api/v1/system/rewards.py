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
    'id': fields.Integer(),
    'name': fields.String(),
    'rule_type': fields.String(),
    'threshold': fields.Integer(),
    'reward_object': fields.String(),
    'reward_object_label': fields.String(),
    'reward_type': fields.String(),
    'reward_type_label': fields.String(),
    'reward_value': fields.Float(),
    'is_active': fields.Integer(),
    'remark': fields.String()
})

reward_record_item_model = reward_ns.model('RewardRecordItem', {
    'id': fields.Integer(),
    'reward_object': fields.String(),
    'reward_object_label': fields.String(),
    'user_id': fields.Integer(),
    'username': fields.String(),
    'factory_id': fields.Integer(),
    'factory_name': fields.String(),
    'reward_config_name': fields.String(),
    'reward_type': fields.String(),
    'reward_type_label': fields.String(),
    'reward_value': fields.Float(),
    'trigger_condition': fields.String(),
    'trigger_value': fields.Integer(),
    'status': fields.String(),
    'status_label': fields.String(),
    'distributor_name': fields.String(),
    'distributed_time': fields.String(),
    'create_time': fields.String()
})

reward_stats_model = reward_ns.model('RewardStats', {
    'total_pending': fields.Integer(),
    'total_distributed': fields.Integer(),
    'factory_pending': fields.Integer(),
    'personal_pending': fields.Integer()
})

reward_list_data = reward_ns.model('RewardListData', {
    'items': fields.List(fields.Nested(reward_record_item_model)),
    'total': fields.Integer(),
    'page': fields.Integer(),
    'page_size': fields.Integer(),
    'pages': fields.Integer()
})

reward_config_list_response = reward_ns.clone('RewardConfigListResponse', base_response, {
    'data': fields.List(fields.Nested(reward_config_item_model))
})

reward_list_response = reward_ns.clone('RewardListResponse', base_response, {
    'data': fields.Nested(reward_list_data)
})

reward_stats_response = reward_ns.clone('RewardStatsResponse', base_response, {
    'data': fields.Nested(reward_stats_model)
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
