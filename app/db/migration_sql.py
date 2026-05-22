from pathlib import Path

from alembic import context, op

REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_MIGRATION_ROOT = REPO_ROOT / "database" / "sql" / "migrations" / "v1"


def run_sql_file(filename: str) -> None:
    sql_path = SQL_MIGRATION_ROOT / filename
    sql = sql_path.read_text(encoding="utf-8")
    if context.is_offline_mode():
        op.execute(sql)
        return

    raw_connection = op.get_bind().connection
    with raw_connection.cursor() as cursor:
        cursor.execute(sql)
