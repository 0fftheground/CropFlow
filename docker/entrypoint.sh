#!/bin/sh
set -eu

mode="${1:-api}"

wait_for_db() {
  python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

url = os.environ.get("CROPFLOW_DATABASE_URL")
if not url:
    raise SystemExit("CROPFLOW_DATABASE_URL is required.")

timeout = float(os.environ.get("CROPFLOW_WAIT_FOR_DB_TIMEOUT_SECONDS", "90"))
deadline = time.time() + timeout
last_error = None

while time.time() < deadline:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as exc:  # pragma: no cover - startup helper
        last_error = exc
        print(f"Waiting for database: {exc}")
        time.sleep(2)
else:
    raise SystemExit(f"Database is not ready within {timeout} seconds: {last_error}")
PY
}

maybe_run_migrations() {
  if [ "${CROPFLOW_RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
    alembic upgrade head
  fi
}

case "$mode" in
  api)
    wait_for_db
    maybe_run_migrations
    exec uvicorn app.main:app --host 0.0.0.0 --port "${CROPFLOW_API_PORT:-8000}"
    ;;
  scheduler)
    wait_for_db
    maybe_run_migrations
    export CROPFLOW_BACKGROUND_JOBS_ENABLED="${CROPFLOW_BACKGROUND_JOBS_ENABLED:-true}"
    exec python -m app.jobs.runner
    ;;
  migrate)
    wait_for_db
    exec alembic upgrade head
    ;;
  seed)
    wait_for_db
    alembic upgrade head
    exec python scripts/seed_local_dev_data.py
    ;;
  seed-reference)
    wait_for_db
    alembic upgrade head
    exec python scripts/seed_reference_data.py
    ;;
  *)
    exec "$@"
    ;;
esac
