from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

from app.core.config import Settings
from app.jobs.runner import run_scheduler_forever
from app.jobs.scheduler import BackgroundJobScheduler


@dataclass
class FakeSession:
    plan_ids: list[int]
    commit_count: int = 0
    rollback_count: int = 0
    closed: bool = False

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True


class FakeSessionFactory:
    def __init__(self, plan_ids: list[int]) -> None:
        self.plan_ids = plan_ids
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession(plan_ids=self.plan_ids)
        self.sessions.append(session)
        return session


class FakePlantingPlanRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def list_by_statuses(self, statuses: list[str] | None = None) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=plan_id) for plan_id in self.session.plan_ids]


class FakeSurveyService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, object]] = []

    def recommend_pre_treatment_survey(self, planting_plan_id: int, *, check_date) -> None:
        self.calls.append((planting_plan_id, check_date))


class FakeSurveyJob:
    instances: list["FakeSurveyJob"] = []

    def __init__(self, service: FakeSurveyService) -> None:
        self.service = service
        self.calls: list[tuple[int, object]] = []
        self.__class__.instances.append(self)

    def run_pre_treatment(self, planting_plan_id: int, *, check_date) -> None:
        self.calls.append((planting_plan_id, check_date))
        self.service.recommend_pre_treatment_survey(planting_plan_id, check_date=check_date)


class FakeTaskGenerationService:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple[int, object]] = []

    def generate_due_tasks(self, planting_plan_id: int, *, check_date) -> list[object]:
        self.calls.append((planting_plan_id, check_date))
        return []


class FakeTaskDueCheckJob:
    instances: list["FakeTaskDueCheckJob"] = []

    def __init__(self, service: FakeTaskGenerationService) -> None:
        self.service = service
        self.calls: list[tuple[int, object]] = []
        self.__class__.instances.append(self)

    def run(self, planting_plan_id: int, *, check_date) -> list[object]:
        self.calls.append((planting_plan_id, check_date))
        return self.service.generate_due_tasks(planting_plan_id, check_date=check_date)


class FakeWeatherUpdateService:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple[int, object]] = []

    def generate_weather_updates(self, planting_plan_id: int, *, check_date) -> list[object]:
        self.calls.append((planting_plan_id, check_date))
        return []


class FakeDailyWeatherCheckJob:
    instances: list["FakeDailyWeatherCheckJob"] = []

    def __init__(self, service: FakeWeatherUpdateService) -> None:
        self.service = service
        self.calls: list[tuple[int, object]] = []
        self.__class__.instances.append(self)

    def run(self, planting_plan_id: int, *, check_date) -> list[object]:
        self.calls.append((planting_plan_id, check_date))
        return self.service.generate_weather_updates(planting_plan_id, check_date=check_date)


def test_scheduler_runs_survey_recommendation_cycle_for_draft_and_active_plans(monkeypatch) -> None:
    factory = FakeSessionFactory([1, 2])
    survey_service = FakeSurveyService()
    FakeSurveyJob.instances.clear()
    settings = Settings(
        background_jobs_enabled=True,
        survey_recommendation_interval_seconds=5,
        task_due_check_interval_seconds=5,
    )

    monkeypatch.setattr("app.jobs.scheduler.PlantingPlanRepository", FakePlantingPlanRepository)
    monkeypatch.setattr("app.jobs.scheduler.build_survey_date_recommendation_service", lambda session, settings: survey_service)
    monkeypatch.setattr("app.jobs.scheduler.SurveyDateRecommendationJob", FakeSurveyJob)

    scheduler = BackgroundJobScheduler(session_factory=factory, settings=settings)
    scheduler._run_survey_recommendation_cycle()

    assert survey_service.calls
    assert [call[0] for call in survey_service.calls] == [1, 2]
    worker_sessions = factory.sessions[1:]
    assert all(session.commit_count == 1 for session in worker_sessions)
    assert all(session.rollback_count == 0 for session in worker_sessions)


def test_scheduler_runs_daily_weather_check_cycle_for_active_plans(monkeypatch) -> None:
    factory = FakeSessionFactory([3, 4])
    FakeDailyWeatherCheckJob.instances.clear()
    settings = Settings(
        background_jobs_enabled=True,
        weather_check_interval_seconds=5,
        survey_recommendation_interval_seconds=5,
        task_due_check_interval_seconds=5,
    )

    monkeypatch.setattr("app.jobs.scheduler.PlantingPlanRepository", FakePlantingPlanRepository)
    monkeypatch.setattr("app.jobs.scheduler.build_weather_provider", lambda session, settings: object())
    monkeypatch.setattr(
        "app.jobs.scheduler.build_cropflow_plan_orchestrator",
        lambda session, settings, weather_provider=None: object(),
    )
    monkeypatch.setattr("app.jobs.scheduler.EventRecordRepository", lambda session: object())
    monkeypatch.setattr("app.jobs.scheduler.WeatherUpdateService", FakeWeatherUpdateService)
    monkeypatch.setattr("app.jobs.scheduler.DailyWeatherCheckJob", FakeDailyWeatherCheckJob)

    scheduler = BackgroundJobScheduler(session_factory=factory, settings=settings)
    scheduler._run_daily_weather_check_cycle()

    assert FakeDailyWeatherCheckJob.instances
    all_calls = [call for instance in FakeDailyWeatherCheckJob.instances for call in instance.calls]
    assert [call[0] for call in all_calls] == [3, 4]
    worker_sessions = factory.sessions[1:]
    assert all(session.commit_count == 1 for session in worker_sessions)
    assert all(session.rollback_count == 0 for session in worker_sessions)


def test_scheduler_runs_task_due_check_cycle_for_active_plans(monkeypatch) -> None:
    factory = FakeSessionFactory([7, 8])
    FakeTaskDueCheckJob.instances.clear()
    settings = Settings(
        background_jobs_enabled=True,
        weather_check_interval_seconds=5,
        survey_recommendation_interval_seconds=5,
        task_due_check_interval_seconds=5,
    )

    monkeypatch.setattr("app.jobs.scheduler.PlantingPlanRepository", FakePlantingPlanRepository)
    monkeypatch.setattr("app.jobs.scheduler.build_cropflow_plan_orchestrator", lambda session, settings: object())
    monkeypatch.setattr("app.jobs.scheduler.EventRecordRepository", lambda session: object())
    monkeypatch.setattr("app.jobs.scheduler.TaskGenerationService", FakeTaskGenerationService)
    monkeypatch.setattr("app.jobs.scheduler.TaskDueCheckJob", FakeTaskDueCheckJob)

    scheduler = BackgroundJobScheduler(session_factory=factory, settings=settings)
    scheduler._run_task_due_check_cycle()

    assert FakeTaskDueCheckJob.instances
    all_calls = [call for instance in FakeTaskDueCheckJob.instances for call in instance.calls]
    assert [call[0] for call in all_calls] == [7, 8]
    worker_sessions = factory.sessions[1:]
    assert all(session.commit_count == 1 for session in worker_sessions)
    assert all(session.rollback_count == 0 for session in worker_sessions)


def test_runner_returns_immediately_when_background_jobs_disabled(monkeypatch) -> None:
    monkeypatch.setattr("app.jobs.runner.get_settings", lambda: Settings(background_jobs_enabled=False))
    called = {"session_factory": 0}
    monkeypatch.setattr(
        "app.jobs.runner.get_session_factory",
        lambda: called.__setitem__("session_factory", called["session_factory"] + 1),
    )

    asyncio.run(run_scheduler_forever())

    assert called["session_factory"] == 0
