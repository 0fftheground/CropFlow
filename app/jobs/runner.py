from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.jobs.scheduler import BackgroundJobScheduler


async def run_scheduler_forever() -> None:
    settings = get_settings()
    if not settings.background_jobs_enabled:
        logging.getLogger(__name__).warning(
            "Background jobs are disabled. Set CROPFLOW_BACKGROUND_JOBS_ENABLED=true to run the scheduler.",
        )
        return

    scheduler = BackgroundJobScheduler(
        session_factory=get_session_factory(),
        settings=settings,
    )
    scheduler.start()
    try:
        await asyncio.Future()
    finally:
        await scheduler.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_scheduler_forever())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Background scheduler stopped by user.")


if __name__ == "__main__":
    main()
