from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date

from app.core.constants import DAILY_WEATHER_CHECK_JOB, EVENT_TYPE_WEATHER_UPDATED
from app.models import EventRecord, PlantingPlan
from app.services.calendar_tasks import WeatherUpdateService


def _make_plan() -> PlantingPlan:
    return PlantingPlan(
        id=11,
        plan_code="PLAN-011",
        plan_name="天气计划",
        farm_id=5,
        culti_type_code=5,
        planting_method_code=1,
        crop_name="水稻",
        variety_id=3,
        variety_name="黄广农占",
        sowing_date=date(2026, 4, 10),
        task_generation_window_days=14,
        metadata_payload={},
    )


@dataclass
class FakePlantingPlanRepository:
    plan: PlantingPlan

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return self.plan if self.plan.id == planting_plan_id else None


@dataclass
class FakeEventRecordRepository:
    records: list[EventRecord] = field(default_factory=list)
    flush_count: int = 0

    def get_by_idempotency_key(self, idempotency_key: str) -> EventRecord | None:
        return next((item for item in self.records if item.idempotency_key == idempotency_key), None)

    def add(self, entity: EventRecord) -> EventRecord:
        self.records.append(entity)
        return entity

    def flush(self) -> None:
        self.flush_count += 1


class FakeWeatherProvider:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.calls: list[tuple[int, date, date, date | None]] = []

    def get_daily_weather(
        self,
        planting_plan: PlantingPlan,
        start_date: date,
        end_date: date,
        *,
        as_of_date: date | None = None,
    ) -> list[dict[str, object]]:
        self.calls.append((planting_plan.id, start_date, end_date, as_of_date))
        return self.rows


class FakePlanOrchestrator:
    def __init__(self) -> None:
        self.handled: list[EventRecord] = []

    def handle(self, event_record: EventRecord) -> object:
        self.handled.append(event_record)
        return object()


def test_weather_update_service_creates_and_handles_weather_updated_event() -> None:
    plan = _make_plan()
    repository = FakeEventRecordRepository()
    weather_provider = FakeWeatherProvider(
        [
            {
                "date": "2026-05-29",
                "avg_temp": 24.5,
                "precipitation": 0.0,
                "source_type": "forecast",
                "data_version": "weather-forecast:2026-05-29",
            },
        ],
    )
    orchestrator = FakePlanOrchestrator()
    service = WeatherUpdateService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        event_record_repository=repository,
        weather_provider=weather_provider,
        plan_orchestrator=orchestrator,
    )

    records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))

    assert len(records) == 1
    assert len(repository.records) == 1
    assert orchestrator.handled == records
    assert repository.flush_count == 1
    assert records[0].event_type == EVENT_TYPE_WEATHER_UPDATED
    assert records[0].idempotency_key == (
        f"{DAILY_WEATHER_CHECK_JOB}:{plan.id}:2026-05-29:weather-forecast:2026-05-29"
    )
    assert records[0].payload["weatherDate"] == "2026-05-29"
    assert records[0].payload["dataVersion"] == "weather-forecast:2026-05-29"
    assert weather_provider.calls == [(plan.id, date(2026, 5, 29), date(2026, 5, 29), date(2026, 5, 29))]


def test_weather_update_service_skips_duplicate_weather_event() -> None:
    plan = _make_plan()
    existing = EventRecord(
        planting_plan_id=plan.id,
        event_type=EVENT_TYPE_WEATHER_UPDATED,
        event_category="job",
        event_source="background_job",
        source_system="cropflow",
        source_record_id="2026-05-29",
        payload={},
        occurred_at=datetime(2026, 5, 29),
        idempotency_key=f"{DAILY_WEATHER_CHECK_JOB}:{plan.id}:2026-05-29:weather-forecast:2026-05-29",
        created_by_type="system",
        created_by_id=DAILY_WEATHER_CHECK_JOB,
    )
    repository = FakeEventRecordRepository(records=[existing])
    weather_provider = FakeWeatherProvider(
        [
            {
                "date": "2026-05-29",
                "data_version": "weather-forecast:2026-05-29",
            },
        ],
    )
    orchestrator = FakePlanOrchestrator()
    service = WeatherUpdateService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        event_record_repository=repository,
        weather_provider=weather_provider,
        plan_orchestrator=orchestrator,
    )

    records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))

    assert records == [existing]
    assert len(repository.records) == 1
    assert repository.flush_count == 0
    assert orchestrator.handled == []
