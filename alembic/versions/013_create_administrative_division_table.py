from typing import Sequence

from app.db.migration_sql import run_sql_file

# revision identifiers, used by Alembic.
revision: str = "cf013_administrative_division"
down_revision: str | None = "cf012_field_external_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql_file("013_create_administrative_division_table.sql")


def downgrade() -> None:
    raise NotImplementedError("Baseline SQL migrations do not support automatic downgrade.")
