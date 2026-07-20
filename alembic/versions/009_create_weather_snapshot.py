from typing import Sequence

from app.db.migration_sql import run_sql_file

# revision identifiers, used by Alembic.
revision: str = "cf009_weather_snapshot"
down_revision: str | None = "cf008_farm_external_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_sql_file("009_create_weather_snapshot.sql")


def downgrade() -> None:
    raise NotImplementedError("Baseline SQL migrations do not support automatic downgrade.")

