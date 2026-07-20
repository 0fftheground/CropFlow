from typing import Sequence

from app.db.migration_sql import run_sql_file

# revision identifiers, used by Alembic.
revision: str = "cf007_farm_region"
down_revision: str | None = "cf006_traceability_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql_file("007_add_farm_region_columns.sql")


def downgrade() -> None:
    raise NotImplementedError("Baseline SQL migrations do not support automatic downgrade.")
