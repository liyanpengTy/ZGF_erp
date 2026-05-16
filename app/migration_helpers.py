"""迁移检查辅助函数。"""

from collections import defaultdict

import sqlalchemy as sa


def has_column(table_name, column_name, bind):
    """检查表中是否存在指定列。"""
    inspector = sa.inspect(bind)
    return any(column['name'] == column_name for column in inspector.get_columns(table_name))


def has_index(table_name, column_name, bind):
    """检查指定列是否仍挂着普通索引。"""
    inspector = sa.inspect(bind)
    for index in inspector.get_indexes(table_name):
        if column_name in index.get('column_names', []):
            return True
    return False


def has_unique_constraint(table_name, column_name, bind):
    """检查指定列是否仍挂着唯一约束。"""
    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints(table_name):
        if column_name in constraint.get('column_names', []):
            return True
    return False


def has_foreign_key(table_name, column_name, bind):
    """检查指定列是否仍挂着外键约束。"""
    inspector = sa.inspect(bind)
    for foreign_key in inspector.get_foreign_keys(table_name):
        if column_name in foreign_key.get('constrained_columns', []):
            return True
    return False


def get_column_dependencies(table_name, column_name, bind):
    """汇总指定列当前依赖的索引、唯一约束和外键。"""
    inspector = sa.inspect(bind)
    dependencies = defaultdict(list)

    for index in inspector.get_indexes(table_name):
        if column_name in index.get('column_names', []):
            dependencies['indexes'].append(index.get('name'))

    for constraint in inspector.get_unique_constraints(table_name):
        if column_name in constraint.get('column_names', []):
            dependencies['unique_constraints'].append(constraint.get('name'))

    for foreign_key in inspector.get_foreign_keys(table_name):
        if column_name in foreign_key.get('constrained_columns', []):
            dependencies['foreign_keys'].append(foreign_key.get('name'))

    pk = inspector.get_pk_constraint(table_name) or {}
    if column_name in pk.get('constrained_columns', []):
        dependencies['primary_key'].append(pk.get('name'))

    return dict(dependencies)
