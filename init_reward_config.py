"""奖励配置初始化脚本。"""

from app import create_app
from app.bootstrap import seed_reward_configs

app = create_app()

with app.app_context():
    seed_reward_configs()
    print('奖励配置初始化完成')
