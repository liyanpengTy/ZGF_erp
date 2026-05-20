"""Flask CLI 命令。"""

import re
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from app.migration_helpers import get_column_dependencies


@click.command("check-migration")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, dir_okay=False), help="迁移脚本路径")
@with_appcontext
def check_migration_command(file_path):
    """检查迁移脚本中的待删列是否仍挂着索引、唯一约束或外键。"""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    bind = current_app.extensions["migrate"].db.engine

    drop_targets = []
    current_table = None
    current_indent = None

    batch_table_pattern = re.compile(r"with\s+op\.batch_alter_table\((['\"])(?P<table>[^'\"]+)\1")
    batch_drop_pattern = re.compile(r"batch_op\.drop_column\((['\"])(?P<column>[^'\"]+)\1")
    plain_drop_pattern = re.compile(r"op\.drop_column\((['\"])(?P<table>[^'\"]+)\1\s*,\s*(['\"])(?P<column>[^'\"]+)\3")

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        batch_match = batch_table_pattern.search(stripped)
        if batch_match:
            current_table = batch_match.group("table")
            current_indent = len(raw_line) - len(raw_line.lstrip())
            continue

        if current_table is not None:
            indent = len(raw_line) - len(raw_line.lstrip())
            if indent <= (current_indent or 0) and not stripped.startswith("batch_op."):
                current_table = None
                current_indent = None

        if current_table is not None:
            batch_drop_match = batch_drop_pattern.search(stripped)
            if batch_drop_match:
                drop_targets.append((current_table, batch_drop_match.group("column")))

        plain_drop_match = plain_drop_pattern.search(stripped)
        if plain_drop_match:
            drop_targets.append((plain_drop_match.group("table"), plain_drop_match.group("column")))

    drop_targets = sorted(set(drop_targets))
    if not drop_targets:
        click.echo(f"{path.name}: 未发现 drop_column 语句")
        return

    has_issue = False
    for table_name, column_name in drop_targets:
        try:
            dependencies = get_column_dependencies(table_name, column_name, bind)
        except Exception as exc:
            has_issue = True
            click.echo(f"[{table_name}.{column_name}] 无法检查依赖：{exc}")
            continue
        if dependencies:
            has_issue = True
            click.echo(f"[{table_name}.{column_name}] 仍存在依赖：{dependencies}")

    if not has_issue:
        click.echo(f"{path.name}: 未发现列依赖风险")


def register_commands(app):
    """注册 Flask CLI 命令。"""
    app.cli.add_command(check_migration_command)
