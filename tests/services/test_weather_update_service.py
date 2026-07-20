from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date

from app.core.constants import DAILY_WEATHER_CHECK_JOB, EVENT_TYPE_WEATHER_UPDATED
from app.models import EventRecord, PlantingPlan, WeatherSnapshot
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
    extra_plans: list[PlantingPlan] = field(default_factory=list)

    def get(self, planting_plan_id: int) -> PlantingPlan | None:
        return next(
            (plan for plan in [self.plan, *self.extra_plans] if plan.id == planting_plan_id),
            None,
        )


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
        for index, record in enumerate(self.records, start=1):
            if record.id is None:
                record.id = index


@dataclass
class FakeWeatherSnapshotRepository:
    records: list[WeatherSnapshot] = field(default_factory=list)
    flush_count: int = 0

    def get_by_identity(
        self,
        *,
        farm_id: int,
        weather_year: int,
        weather_date: date,
        source_type: str,
        data_version: str,
        data_hash: str,
    ) -> WeatherSnapshot | None:
        return next(
            (
                item
                for item in self.records
                if item.farm_id == farm_id
                and item.weather_year == weather_year
                and item.weather_date == weather_date
                and item.source_type == source_type
                and item.data_version == data_version
                and item.data_hash == data_hash
            ),
            None,
        )

    def add(self, entity: WeatherSnapshot) -> WeatherSnapshot:
        self.records.append(entity)
        return entity

    def flush(self) -> None:
        self.flush_count += 1
        for index, record in enumerate(self.records, start=1):
            if record.id is None:
                record.id = index

    def get_active_by_farm_date_source(
        self,
        *,
        farm_id: int,
        weather_year: int,
        weather_date: date,
        source_type: str,
    ) -> WeatherSnapshot | None:
        return next(
            (
                item
                for item in reversed(self.records)
                if item.farm_id == farm_id
                and item.weather_year == weather_year
                and item.weather_date == weather_date
                and item.source_type == source_type
                and item.is_active is True
            ),
            None,
        )

    def supersede_active_for_farm_date_source(
        self,
        *,
        farm_id: int,
        weather_year: int,
        weather_date: date,
        source_type: str,
        superseded_by_snapshot_id: int,
    ) -> None:
        for item in self.records:
            if (
                item.farm_id == farm_id
                and item.weather_year == weather_year
                and item.weather_date == weather_date
                and item.source_type == source_type
                and item.id != superseded_by_snapshot_id
                and item.is_active is True
            ):
                item.is_active = False
                item.superseded_at = datetime(2026, 5, 29)
                item.superseded_by_snapshot_id = superseded_by_snapshot_id


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
    snapshot_repository = FakeWeatherSnapshotRepository()
    service = WeatherUpdateService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        event_record_repository=repository,
        weather_provider=weather_provider,
        plan_orchestrator=orchestrator,
        weather_snapshot_repository=snapshot_repository,
    )

    records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))

    assert len(records) == 1
    assert len(repository.records) == 1
    assert orchestrator.handled == records
    assert repository.flush_count == 1
    assert records[0].event_type == EVENT_TYPE_WEATHER_UPDATED
    assert records[0].idempotency_key.startswith(
        f"{DAILY_WEATHER_CHECK_JOB}:{plan.id}:2026-05-29:weather-forecast:2026-05-29:",
    )
    assert records[0].payload["weatherDate"] == "2026-05-29"
    assert records[0].payload["dataVersion"] == "weather-forecast:2026-05-29"
    assert records[0].payload["dataHash"]
    assert records[0].payload["weatherSnapshotId"] == 1
    assert records[0].payload["weatherChangeType"] == "new_snapshot"
    assert records[0].payload["previousWeatherSnapshotId"] is None
    assert len(snapshot_repository.records) == 1
    assert snapshot_repository.records[0].farm_id == plan.farm_id
    assert snapshot_repository.records[0].weather_year == 2026
    assert snapshot_repository.records[0].is_active is True
    assert snapshot_repository.records[0].source_event_id == records[0].id
    assert weather_provider.calls == [(plan.id, date(2026, 5, 29), date(2026, 5, 29), date(2026, 5, 29))]


def test_weather_update_service_creates_new_event_when_payload_hash_changes() -> None:
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
        idempotency_key=(
            f"{DAILY_WEATHER_CHECK_JOB}:{plan.id}:2026-05-29:"
            "weather-forecast:2026-05-29:existing-hash"
        ),
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
    snapshot_repository = FakeWeatherSnapshotRepository()
    service = WeatherUpdateService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        event_record_repository=repository,
        weather_provider=weather_provider,
        plan_orchestrator=orchestrator,
        weather_snapshot_repository=snapshot_repository,
    )

    records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))

    assert records != [existing]
    assert len(repository.records) == 2
    assert repository.flush_count == 1
    assert len(snapshot_repository.records) == 1
    assert records[0].payload["weatherChangeType"] == "new_snapshot"
    assert orchestrator.handled == [records[0]]


def test_weather_update_service_skips_duplicate_weather_event() -> None:
    plan = _make_plan()
    repository = FakeEventRecordRepository()
    snapshot_repository = FakeWeatherSnapshotRepository()
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
        weather_snapshot_repository=snapshot_repository,
    )

    first_records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))
    second_records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))

    assert second_records == first_records
    assert len(repository.records) == 1
    assert len(snapshot_repository.records) == 1
    assert second_records[0].payload["weatherChangeType"] == "new_snapshot"
    assert orchestrator.handled == first_records


def test_weather_snapshot_is_reused_across_plans_in_same_farm_year() -> None:
    plan = _make_plan()
    other_plan = _make_plan()
    other_plan.id = 12
    other_plan.plan_code = "PLAN-012"
    repository = FakeEventRecordRepository()
    snapshot_repository = FakeWeatherSnapshotRepository()
    weather_provider = FakeWeatherProvider(
        [
            {
                "date": "2026-05-29",
                "avg_temp": 24.5,
                "source_type": "observed",
                "data_version": "weather-observed:2026-05-29",
            },
        ],
    )
    orchestrator = FakePlanOrchestrator()
    service = WeatherUpdateService(
        planting_plan_repository=FakePlantingPlanRepository(plan, [other_plan]),
        event_record_repository=repository,
        weather_provider=weather_provider,
        plan_orchestrator=orchestrator,
        weather_snapshot_repository=snapshot_repository,
    )

    first_records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))
    second_records = service.generate_weather_updates(other_plan.id, check_date=date(2026, 5, 29))

    assert len(snapshot_repository.records) == 1
    assert first_records[0].payload["weatherSnapshotId"] == second_records[0].payload["weatherSnapshotId"]
    assert second_records[0].payload["weatherChangeType"] == "reused_snapshot"
    assert {record.planting_plan_id for record in repository.records} == {11, 12}
    assert len(orchestrator.handled) == 2


def test_weather_update_service_supersedes_previous_active_snapshot_when_content_changes() -> None:
    plan = _make_plan()
    repository = FakeEventRecordRepository()
    snapshot_repository = FakeWeatherSnapshotRepository()
    weather_provider = FakeWeatherProvider(
        [
            {
                "date": "2026-05-29",
                "avg_temp": 24.5,
                "source_type": "observed",
                "data_version": "weather-observed:2026-05-29",
            },
        ],
    )
    orchestrator = FakePlanOrchestrator()
    service = WeatherUpdateService(
        planting_plan_repository=FakePlantingPlanRepository(plan),
        event_record_repository=repository,
        weather_provider=weather_provider,
        plan_orchestrator=orchestrator,
        weather_snapshot_repository=snapshot_repository,
    )

    first_records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))
    weather_provider.rows = [
        {
            "date": "2026-05-29",
            "avg_temp": 25.0,
            "source_type": "observed",
            "data_version": "weather-observed:2026-05-29",
        },
    ]
    second_records = service.generate_weather_updates(plan.id, check_date=date(2026, 5, 29))

    assert len(snapshot_repository.records) == 2
    assert snapshot_repository.records[0].is_active is False
    assert snapshot_repository.records[0].superseded_by_snapshot_id == snapshot_repository.records[1].id
    assert snapshot_repository.records[1].is_active is True
    assert second_records[0].payload["weatherChangeType"] == "changed_snapshot"
    assert second_records[0].payload["previousWeatherSnapshotId"] == first_records[0].payload["weatherSnapshotId"]
