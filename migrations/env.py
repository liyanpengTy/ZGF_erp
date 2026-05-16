import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
from app.migration_helpers import get_column_dependencies

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def iter_column_change_ops(operation, current_table=None):
    """递归提取迁移操作中的删列/改列目标。"""
    table_name = getattr(operation, 'table_name', current_table)
    if hasattr(operation, 'ops'):
        for child in operation.ops:
            yield from iter_column_change_ops(child, table_name)
        return

    op_name = operation.__class__.__name__
    if op_name == 'DropColumnOp':
        yield table_name, getattr(operation, 'column_name', None), 'drop'
    elif op_name == 'AlterColumnOp':
        yield table_name, getattr(operation, 'column_name', None), 'alter'


def warn_sensitive_column_ops(connection, upgrade_ops):
    """在生成迁移时提示依赖索引、唯一约束或外键的敏感列操作。"""
    warnings = []
    for operation in upgrade_ops.ops:
        for table_name, column_name, op_type in iter_column_change_ops(operation):
            if not table_name or not column_name:
                continue
            try:
                dependencies = get_column_dependencies(table_name, column_name, connection)
            except Exception as exc:
                logger.warning(
                    'Unable to inspect dependencies for %s.%s (%s): %s',
                    table_name,
                    column_name,
                    op_type,
                    exc,
                )
                continue
            if not dependencies:
                continue
            warnings.append((table_name, column_name, op_type, dependencies))

    for table_name, column_name, op_type, dependencies in warnings:
        logger.warning(
            'Sensitive migration op detected: %s.%s (%s) still has dependencies %s',
            table_name,
            column_name,
            op_type,
            dependencies,
        )


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')
            else:
                warn_sensitive_column_ops(context.connection, script.upgrade_ops)

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives
    conf_args.setdefault('compare_type', True)
    conf_args.setdefault('compare_server_default', False)

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
