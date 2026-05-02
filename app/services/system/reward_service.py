"""奖励服务"""
from datetime import datetime, timedelta
from app.extensions import db
from app.models.auth.user import User
from app.models.system.factory import Factory
from app.models.system.reward_config import RewardConfig
from app.models.system.reward_record import RewardRecord
from app.services.base.base_service import BaseService


class RewardService(BaseService):
    """奖励服务"""

    @staticmethod
    def get_active_reward_configs(rule_type='invite_count'):
        """获取启用的奖励配置"""
        return RewardConfig.query.filter_by(
            rule_type=rule_type,
            is_active=1,
            is_deleted=0
        ).order_by(RewardConfig.threshold).all()

    @staticmethod
    def get_user_factory_id(user_id):
        """获取用户所属工厂ID（owner类型）"""
        from app.models.system.user_factory import UserFactory
        user_factory = UserFactory.query.filter_by(
            user_id=user_id,
            relation_type='owner',
            status=1,
            is_deleted=0
        ).first()
        return user_factory.factory_id if user_factory else None

    @staticmethod
    def check_and_create_rewards(user_id):
        """
        检查用户是否触发奖励，并创建奖励记录
        返回: (created_count, reward_records)
        """
        user = User.query.filter_by(id=user_id, is_deleted=0).first()
        if not user:
            return 0, []

        factory_id = RewardService.get_user_factory_id(user_id)

        configs = RewardService.get_active_reward_configs()
        created_records = []

        for config in configs:
            # 检查是否已存在该配置的奖励记录
            existing = RewardRecord.query.filter_by(
                user_id=user_id,
                reward_config_id=config.id,
                is_deleted=0
            ).first()

            if existing:
                continue

            # 检查是否达标
            is_triggered = False
            trigger_value = None

            if config.rule_type == 'invite_count':
                if user.invited_count >= config.threshold:
                    is_triggered = True
                    trigger_value = user.invited_count

            if not is_triggered:
                continue

            # 根据奖励对象创建记录
            if config.reward_object == 'factory':
                if not factory_id:
                    continue
                reward_record = RewardRecord(
                    reward_object='factory',
                    user_id=user_id,
                    factory_id=factory_id,
                    reward_config_id=config.id,
                    reward_type=config.reward_type,
                    reward_value=config.reward_value,
                    trigger_condition=f'邀请人数 >= {config.threshold}',
                    trigger_value=trigger_value,
                    status='pending',
                    remark=f'邀请{trigger_value}人，触发工厂奖励'
                )
            else:
                # 个人现金奖励
                reward_record = RewardRecord(
                    reward_object='personal',
                    user_id=user_id,
                    factory_id=None,
                    reward_config_id=config.id,
                    reward_type=config.reward_type,
                    reward_value=config.reward_value,
                    trigger_condition=f'邀请人数 >= {config.threshold}',
                    trigger_value=trigger_value,
                    status='pending',
                    remark=f'邀请{trigger_value}人，触发个人现金奖励'
                )

            reward_record.save()
            created_records.append(reward_record)

        return len(created_records), created_records

    @staticmethod
    def distribute_reward(reward_record_id, distributor_id):
        """
        发放奖励
        返回: (success, message)
        """
        reward = RewardRecord.query.filter_by(
            id=reward_record_id,
            is_deleted=0
        ).first()

        if not reward:
            return False, '奖励记录不存在'

        if reward.status != 'pending':
            return False, f'奖励状态为{reward.status}，无法发放'

        # 根据奖励对象和类型执行发放
        if reward.reward_object == 'factory':
            factory = Factory.query.filter_by(id=reward.factory_id, is_deleted=0).first()
            if not factory:
                return False, '工厂不存在'

            if reward.reward_type == 'extend':
                # 工厂VIP延期
                extend_days = int(reward.reward_value)
                if factory.vip_expire_date:
                    new_expire_date = factory.vip_expire_date + timedelta(days=extend_days)
                else:
                    new_expire_date = datetime.now().date() + timedelta(days=extend_days)
                factory.vip_expire_date = new_expire_date
            else:
                return False, f'无效的工厂奖励类型: {reward.reward_type}'

        else:
            # 个人现金奖励
            if reward.reward_type != 'cash':
                return False, f'无效的个人奖励类型: {reward.reward_type}'
            # 现金奖励：记录即可，实际转账由财务处理

        # 更新奖励记录状态
        reward.status = 'distributed'
        reward.distributed_by = distributor_id
        reward.distributed_time = datetime.now()

        reward.save()

        return True, '发放成功'

    @staticmethod
    def get_pending_rewards(filters):
        """获取待发放的奖励列表"""
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 10)
        username = filters.get('username', '')
        reward_object = filters.get('reward_object')

        query = RewardRecord.query.filter_by(status='pending', is_deleted=0)

        if username:
            query = query.join(User).filter(User.username.like(f'%{username}%'))
        if reward_object:
            query = query.filter_by(reward_object=reward_object)

        pagination = query.order_by(RewardRecord.create_time.asc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'pages': pagination.pages
        }

    @staticmethod
    def get_reward_statistics():
        """获取奖励统计"""
        total_pending = RewardRecord.query.filter_by(status='pending', is_deleted=0).count()
        total_distributed = RewardRecord.query.filter_by(status='distributed', is_deleted=0).count()

        factory_pending = RewardRecord.query.filter_by(
            reward_object='factory', status='pending', is_deleted=0
        ).count()
        personal_pending = RewardRecord.query.filter_by(
            reward_object='personal', status='pending', is_deleted=0
        ).count()

        return {
            'total_pending': total_pending,
            'total_distributed': total_distributed,
            'factory_pending': factory_pending,
            'personal_pending': personal_pending
        }
