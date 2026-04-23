# 创建管理员/初始化命令
import click
from flask.cli import with_appcontext
from app.extensions import db, bcrypt
from app.models.auth.user import User
from app.models.system.factory import Factory


@click.command('init-db')
@with_appcontext
def init_db():
    """初始化数据库：创建所有表"""
    db.create_all()
    click.echo('✅ 数据库表创建成功')


@click.command('init-admin')
@with_appcontext
def init_admin():
    """初始化管理员账户"""

    # 检查是否已存在管理员
    admin = User.query.filter_by(username='admin').first()
    if admin:
        click.echo('⚠️ 管理员账户已存在')
        return

    # 创建管理员
    admin = User(
        username='admin',
        password=bcrypt.generate_password_hash('123456').decode('utf-8'),
        nickname='超级管理员',
        email='admin@zgferp.com',
        user_type=1,  # 公司内部人员
        status=1
    )
    admin.save()
    click.echo(f'✅ 管理员账户创建成功 - 用户名: admin, 密码: 123456')


@click.command('init-factory')
@with_appcontext
def init_factory():
    """初始化测试工厂"""

    # 创建测试工厂
    factory = Factory(
        name='测试工厂',
        code='TEST001',
        contact_person='张三',
        contact_phone='13800138000',
        address='广东省深圳市南山区',
        status=1
    )
    factory.save()
    click.echo(f'✅ 测试工厂创建成功 - ID: {factory.id}, 名称: {factory.name}')

    # 创建工厂管理员账号
    factory_admin = User.query.filter_by(username='factory_admin').first()
    if not factory_admin:
        factory_admin = User(
            username='factory_admin',
            password=bcrypt.generate_password_hash('123456').decode('utf-8'),
            nickname='工厂管理员',
            user_type=2,  # 工厂类型
            factory_id=factory.id,
            status=1
        )
        factory_admin.save()
        click.echo(f'✅ 工厂管理员创建成功 - 用户名: factory_admin, 密码: 123456')

    # 创建工厂员工
    employee = User.query.filter_by(username='factory_employee').first()
    if not employee:
        employee = User(
            username='factory_employee',
            password=bcrypt.generate_password_hash('123456').decode('utf-8'),
            nickname='工厂员工',
            user_type=3,  # 工厂员工
            factory_id=factory.id,
            status=1
        )
        employee.save()
        click.echo(f'✅ 工厂员工创建成功 - 用户名: factory_employee, 密码: 123456')


@click.command('init-all')
@with_appcontext
def init_all():
    """初始化所有数据"""
    click.echo('开始初始化数据库...')
    init_db()
    click.echo('开始初始化管理员...')
    init_admin()
    click.echo('开始初始化工厂数据...')
    init_factory()
    click.echo('🎉 所有初始化完成！')


def register_commands(app):
    """注册命令行命令"""
    app.cli.add_command(init_db)
    app.cli.add_command(init_admin)
    app.cli.add_command(init_factory)
    app.cli.add_command(init_all)