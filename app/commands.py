"""Flask CLI 命令。"""

import click
from flask.cli import with_appcontext

from app.bootstrap import (
    create_tables,
    seed_admin_user,
    seed_all,
    seed_demo_factory,
    seed_demo_role_menus,
    seed_menus,
    seed_reward_configs,
)


@click.command('init-db')
@with_appcontext
def init_db():
    """初始化数据库表。"""
    create_tables()
    click.echo('数据库表创建成功')


@click.command('seed-admin')
@with_appcontext
def seed_admin():
    """初始化平台管理员账号。"""
    user, created = seed_admin_user()
    if created:
        click.echo(f'平台管理员已创建: {user.username} / 123456')
    else:
        click.echo(f'平台管理员已存在: {user.username}')


@click.command('seed-menus')
@with_appcontext
def seed_menu_command():
    """初始化系统菜单。"""
    seed_menus()
    click.echo('系统菜单初始化完成')


@click.command('seed-reward-config')
@with_appcontext
def seed_reward_config_command():
    """初始化奖励配置。"""
    seed_reward_configs()
    click.echo('奖励配置初始化完成')


@click.command('seed-demo-factory')
@with_appcontext
def seed_demo_factory_command():
    """初始化演示工厂与演示账号。"""
    factory = seed_demo_factory()
    seed_demo_role_menus()
    click.echo(f'演示工厂初始化完成: {factory.name} ({factory.code})')


@click.command('seed-all')
@with_appcontext
def seed_all_command():
    """清理旧演示数据后，重建标准初始化数据。"""
    result = seed_all()
    factory = result['factory']
    click.echo(f'完整初始化完成: {factory.name} ({factory.code})')


@click.command('reset-demo-data')
@with_appcontext
def reset_demo_data_command():
    """显式重置演示数据，并重建标准初始化数据。"""
    result = seed_all()
    factory = result['factory']
    click.echo(f'演示数据已重置: {factory.name} ({factory.code})')


def register_commands(app):
    """注册 Flask CLI 命令。"""
    app.cli.add_command(init_db)
    app.cli.add_command(seed_admin)
    app.cli.add_command(seed_menu_command)
    app.cli.add_command(seed_reward_config_command)
    app.cli.add_command(seed_demo_factory_command)
    app.cli.add_command(seed_all_command)
    app.cli.add_command(reset_demo_data_command)
