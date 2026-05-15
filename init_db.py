"""数据库初始化脚本。"""

from app import create_app
from app.bootstrap import seed_all

app = create_app()

with app.app_context():
    result = seed_all()
    admin = result['admin']
    factory = result['factory']

    print('数据库初始化完成，旧演示数据已清理并重建')
    print(f'平台管理员: {admin.username} / 123456')
    print(f'演示工厂: {factory.name} ({factory.code})')
