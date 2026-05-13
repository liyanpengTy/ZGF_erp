"""菜单初始化脚本。"""

from app import create_app
from app.bootstrap import seed_demo_role_menus, seed_menus

app = create_app()

with app.app_context():
    seed_menus()
    seed_demo_role_menus()
    print('菜单初始化完成')
