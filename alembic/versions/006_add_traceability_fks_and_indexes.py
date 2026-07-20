from typing import Sequence

from app.db.migration_sql import run_sql_file

# revision identifiers, used by Alembic.
revision: str = "cf006_traceability_idx"
down_revision: str | None = "cf005_feedback_notice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql_file("006_add_traceability_fks_and_indexes.sql")


def downgrade() -> None:
    raise NotImplementedError("Baseline SQL migrations do not support automatic downgrade.")
