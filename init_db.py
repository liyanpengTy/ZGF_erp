"""数据库初始化脚本。"""

from app import create_app
from app.bootstrap import create_tables, seed_admin_user, seed_demo_factory, seed_demo_role_menus

app = create_app()

with app.app_context():
    create_tables()
    admin, _ = seed_admin_user()
    factory = seed_demo_factory()
    seed_demo_role_menus()

    print('数据库初始化完成')
    print(f'平台管理员: {admin.username} / 123456')
    print(f'演示工厂: {factory.name} ({factory.code})')
