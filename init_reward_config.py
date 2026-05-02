"""初始化奖励配置"""
from app import create_app
from app.extensions import db
from app.models.system.reward_config import RewardConfig

app = create_app()

with app.app_context():
    configs = [
        {
            'name': '邀请5人-工厂延期',
            'rule_type': 'invite_count',
            'threshold': 5,
            'reward_object': 'factory',
            'reward_type': 'extend',
            'reward_value': 365,
            'is_active': 1,
            'remark': '邀请满5人，工厂VIP延期一年'
        },
        {
            'name': '邀请5人-现金奖励',
            'rule_type': 'invite_count',
            'threshold': 5,
            'reward_object': 'personal',
            'reward_type': 'cash',
            'reward_value': 400,
            'is_active': 1,
            'remark': '邀请满5人，个人现金奖励400元'
        },
        {
            'name': '邀请10人-工厂延期',
            'rule_type': 'invite_count',
            'threshold': 10,
            'reward_object': 'factory',
            'reward_type': 'extend',
            'reward_value': 730,
            'is_active': 1,
            'remark': '邀请满10人，工厂VIP延期两年'
        }
    ]

    for config_data in configs:
        existing = RewardConfig.query.filter_by(
            rule_type=config_data['rule_type'],
            threshold=config_data['threshold'],
            reward_object=config_data['reward_object'],
            is_deleted=0
        ).first()

        if not existing:
            config = RewardConfig(**config_data)
            db.session.add(config)
            print(f'✅ 添加配置: {config_data["name"]}')
        else:
            print(f'⏭️ 配置已存在: {config_data["name"]}')

    db.session.commit()
    print('🎉 奖励配置初始化完成')
