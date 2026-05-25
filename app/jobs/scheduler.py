from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import build_cropflow_plan_orchestrator, build_survey_date_recommendation_service
from app.core.config import Settings
from app.jobs.survey_date_recommendation import SurveyDateRecommendationJob
from app.jobs.task_due_check import TaskDueCheckJob
from app.repositories import EventRecordRepository, PlantingPlanRepository
from app.services import TaskGenerationService

logger = logging.getLogger(__name__)


class BackgroundJobScheduler:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        settings: Settings,
        sleep: Callable[[float], asyncio.Future[None] | asyncio.Task[None] | object] = asyncio.sleep,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.sleep = sleep
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[None]] = []

    def start(self) -> None:
        if not self.settings.background_jobs_enabled:
            logger.info("Background jobs are disabled.")
            return
        if self._tasks:
            return

        self._stop_event.clear()
        self._tasks = [
            asyncio.create_task(
                self._run_loop(
                    "survey_recommendation",
                    self.settings.survey_recommendation_interval_seconds,
                    self._run_survey_recommendation_cycle,
                ),
            ),
            asyncio.create_task(
                self._run_loop(
                    "task_due_check",
                    self.settings.task_due_check_interval_seconds,
                    self._run_task_due_check_cycle,
                ),
            ),
        ]

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks = []

    async def _run_loop(
        self,
        loop_name: str,
        interval_seconds: int,
        cycle: Callable[[], None],
    ) -> None:
        logger.info("Starting background loop %s with interval=%ss.", loop_name, interval_seconds)
        while not self._stop_event.is_set():
            try:
                cycle()
            except Exception:
                logger.exception("Background loop %s failed.", loop_name)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=max(interval_seconds, 1))
            except asyncio.TimeoutError:
                continue

    def _run_survey_recommendation_cycle(self) -> None:
        check_date = _utc_today()
        for planting_plan_id in self._list_target_plan_ids(statuses=["draft", "active"]):
            session = self.session_factory()
            try:
                service = build_survey_date_recommendation_service(session, self.settings)
                if service is None:
                    return
                SurveyDateRecommendationJob(service).run_pre_treatment(planting_plan_id, check_date=check_date)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception(
                    "SurveyDateRecommendationJob failed for planting_plan_id=%s.",
                    planting_plan_id,
                )
            finally:
                session.close()

    def _run_task_due_check_cycle(self) -> None:
        check_date = _utc_today()
        for planting_plan_id in self._list_target_plan_ids(statuses=["active"]):
            session = self.session_factory()
            try:
                orchestrator = build_cropflow_plan_orchestrator(session, self.settings)
                service = TaskGenerationService(
                    planting_plan_repository=PlantingPlanRepository(session),
                    event_record_repository=EventRecordRepository(session),
                    plan_orchestrator=orchestrator,
                )
                TaskDueCheckJob(service).run(planting_plan_id, check_date=check_date)
                session.commit()
            except Exception:
                session.rollback()
                logger.exception("TaskDueCheckJob failed for planting_plan_id=%s.", planting_plan_id)
            finally:
                session.close()

    def _list_target_plan_ids(self, *, statuses: list[str]) -> list[int]:
        session = self.session_factory()
        try:
            return [plan.id for plan in PlantingPlanRepository(session).list_by_statuses(statuses)]
        finally:
            session.close()


def _utc_today() -> date:
    return datetime.now(UTC).date()
