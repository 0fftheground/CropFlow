from typing import Sequence

from app.db.migration_sql import run_sql_file

# revision identifiers, used by Alembic.
revision: str = "cf003_task_review"
down_revision: str | None = "cf002_plan_stage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql_file("003_create_task_and_review_tables.sql")


def downgrade() -> None:
    raise NotImplementedError("Baseline SQL migrations do not support automatic downgrade.")
