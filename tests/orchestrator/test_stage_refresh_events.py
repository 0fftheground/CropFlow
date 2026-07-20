from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.constants import EVENT_TYPE_ACTUAL_STAGE_RECORDED, EVENT_TYPE_STAGE_CHANGED, EVENT_TYPE_WEATHER_UPDATED
from app.models import CropStageState, CropThermalTimeState, EventRecord, StagePredictionSnapshot
from app.orchestrator.core import StageRefreshHandler
from app.services.stage_management import ActualStageRecordResult, StageRefreshResult


@dataclass
class FakeEventRecordRepository:
    records: list[EventRecord] = field(default_factory=list)

    def get_by_idempotency_key(self, idempotency_key: str) -> EventRecord | None:
        return next((item for item in self.records if item.idempotency_key == idempotency_key), None)

    def add(self, event_record: EventRecord) -> EventRecord:
        self.records.append(event_record)
        return event_record


class FakeStageManagementService:
    def __init__(self) -> None:
        self.weather_update_payloads: list[dict[str, Any]] = []
        self.actual_stage_calls: list[dict[str, Any]] = []
        self.actual_stage_batch_calls: list[dict[str, Any]] = []

    def refresh_for_weather_update(
        self,
        planting_plan_id: int,
        *,
        source_event_id: int | None = None,
        as_of_date: date | None = None,
        source_event_payload: dict[str, Any] | None = None,
    ) -> StageRefreshResult:
        self.weather_update_payloads.append(dict(source_event_payload or {}))
        return StageRefreshResult(
            snapshot=StagePredictionSnapshot(
                id=10,
                planting_plan_id=planting_plan_id,
                prediction_version=2,
                prediction_source="weather_update",
                algorithm_code="stage_prediction_algorithm",
                input_payload={},
                stage_timeline={},
                thermal_thresholds={},
            ),
            crop_stage_state=CropStageState(
                planting_plan_id=planting_plan_id,
                current_stage_code="tillering",
                current_stage_name="分蘖期",
                stage_source="predicted",
                effective_date=as_of_date or date(2026, 5, 29),
                version=2,
            ),
            crop_thermal_time_state=CropThermalTimeState(
                planting_plan_id=planting_plan_id,
                accumulated_thermal_time=Decimal("800"),
            ),
            previous_stage_code="seedling",
            stage_changed=True,
        )

    def apply_actual_stage_recorded(
        self,
        planting_plan_id: int,
        *,
        stage_code: str,
        effective_date: date,
        stage_name: str | None = None,
        source_event_id: int | None = None,
    ) -> ActualStageRecordResult:
        self.actual_stage_calls.append(
            {
                "stage_code": stage_code,
                "stage_name": stage_name,
                "effective_date": effective_date,
                "source_event_id": source_event_id,
            },
        )
        return ActualStageRecordResult(
            snapshot=StagePredictionSnapshot(
                id=11,
                planting_plan_id=planting_plan_id,
                prediction_version=3,
                prediction_source="manual_adjustment",
                algorithm_code="stage_prediction_algorithm",
                input_payload={},
                stage_timeline={"stages": [], "raw_stage_points": []},
                thermal_thresholds={},
            ),
            crop_stage_state=CropStageState(
                planting_plan_id=planting_plan_id,
                current_stage_code=stage_code,
                current_stage_name=stage_name or stage_code,
                stage_source="manual",
                effective_date=effective_date,
                version=3,
            ),
            crop_thermal_time_state=CropThermalTimeState(
                planting_plan_id=planting_plan_id,
                accumulated_thermal_time=Decimal("900"),
            ),
            previous_stage_code="tillering",
            stage_changed=True,
        )

    def apply_actual_stage_records(
        self,
        planting_plan_id: int,
        *,
        stage_dates: dict[str, date],
        stage_names: dict[str, str | None] | None = None,
        source_event_id: int | None = None,
    ) -> ActualStageRecordResult:
        latest_stage_code, latest_effective_date = max(stage_dates.items(), key=lambda item: (item[1], item[0]))
        self.actual_stage_batch_calls.append(
            {
                "stage_dates": dict(stage_dates),
                "stage_names": dict(stage_names or {}),
                "source_event_id": source_event_id,
            },
        )
        return ActualStageRecordResult(
            snapshot=StagePredictionSnapshot(
                id=12,
                planting_plan_id=planting_plan_id,
                prediction_version=4,
                prediction_source="manual_adjustment",
                algorithm_code="stage_prediction_algorithm",
                input_payload={},
                stage_timeline={"stages": [], "raw_stage_points": []},
                thermal_thresholds={},
            ),
            crop_stage_state=CropStageState(
                planting_plan_id=planting_plan_id,
                current_stage_code=latest_stage_code,
                current_stage_name=latest_stage_code,
                stage_source="manual",
                effective_date=latest_effective_date,
                version=4,
            ),
            crop_thermal_time_state=CropThermalTimeState(
                planting_plan_id=planting_plan_id,
                accumulated_thermal_time=Decimal("950"),
            ),
            previous_stage_code="tillering",
            stage_changed=True,
        )


def test_weather_update_records_stage_changed_event() -> None:
    event_repository = FakeEventRecordRepository()
    stage_service = FakeStageManagementService()
    handler = StageRefreshHandler(stage_service, event_repository)  # type: ignore[arg-type]
    event_record = EventRecord(
        id=5,
        planting_plan_id=1,
        event_type=EVENT_TYPE_WEATHER_UPDATED,
        event_category="job",
        event_source="background_job",
        payload={"weatherDate": "2026-05-29", "sourceType": "observed"},
        occurred_at=datetime(2026, 5, 29),
        idempotency_key="weather-event",
    )

    result = handler.handle(event_record)

    assert result.crop_stage_states[0].current_stage_code == "tillering"
    assert stage_service.weather_update_payloads == [{"weatherDate": "2026-05-29", "sourceType": "observed"}]
    assert event_repository.records[0].event_type == EVENT_TYPE_STAGE_CHANGED
    assert event_repository.records[0].payload["previousStageCode"] == "seedling"
    assert event_repository.records[0].payload["currentStageCode"] == "tillering"
    assert event_repository.records[0].payload["sourceSnapshotId"] == 10


def test_forecast_weather_update_does_not_record_stage_changed_event() -> None:
    event_repository = FakeEventRecordRepository()
    stage_service = FakeStageManagementService()
    handler = StageRefreshHandler(stage_service, event_repository)  # type: ignore[arg-type]
    event_record = EventRecord(
        id=7,
        planting_plan_id=1,
        event_type=EVENT_TYPE_WEATHER_UPDATED,
        event_category="job",
        event_source="background_job",
        payload={"weatherDate": "2026-05-29", "sourceType": "forecast"},
        occurred_at=datetime(2026, 5, 29),
        idempotency_key="forecast-weather-event",
    )

    result = handler.handle(event_record)

    assert result.crop_stage_states[0].current_stage_code == "tillering"
    assert stage_service.weather_update_payloads == [{"weatherDate": "2026-05-29", "sourceType": "forecast"}]
    assert event_repository.records == []


def test_actual_stage_recorded_updates_stage_and_records_stage_changed_event() -> None:
    event_repository = FakeEventRecordRepository()
    stage_service = FakeStageManagementService()
    handler = StageRefreshHandler(stage_service, event_repository)  # type: ignore[arg-type]
    event_record = EventRecord(
        id=6,
        planting_plan_id=1,
        event_type=EVENT_TYPE_ACTUAL_STAGE_RECORDED,
        event_category="runtime",
        event_source="api",
        payload={"stageCode": "heading", "stageName": "齐穗期", "effectiveDate": "2026-06-18"},
        occurred_at=datetime(2026, 6, 18),
        idempotency_key="actual-stage-event",
    )

    result = handler.handle(event_record)

    assert result.crop_stage_states[0].current_stage_code == "heading"
    assert stage_service.actual_stage_calls[0]["effective_date"] == date(2026, 6, 18)
    assert event_repository.records[0].event_type == EVENT_TYPE_STAGE_CHANGED
    assert event_repository.records[0].payload["previousStageCode"] == "tillering"
    assert event_repository.records[0].payload["currentStageCode"] == "heading"
    assert event_repository.records[0].payload["sourceSnapshotId"] == 11


def test_actual_stage_recorded_batch_updates_stage_once_and_records_stage_changed_event() -> None:
    event_repository = FakeEventRecordRepository()
    stage_service = FakeStageManagementService()
    handler = StageRefreshHandler(stage_service, event_repository)  # type: ignore[arg-type]
    event_record = EventRecord(
        id=8,
        planting_plan_id=1,
        event_type=EVENT_TYPE_ACTUAL_STAGE_RECORDED,
        event_category="runtime",
        event_source="api",
        payload={
            "stageCode": "BBCH58",
            "effectiveDate": "2026-06-24",
            "stageDates": {"BBCH45": "2026-06-10", "BBCH58": "2026-06-24"},
        },
        occurred_at=datetime(2026, 6, 24),
        idempotency_key="actual-stage-batch-event",
    )

    result = handler.handle(event_record)

    assert result.crop_stage_states[0].current_stage_code == "BBCH58"
    assert stage_service.actual_stage_batch_calls[0]["stage_dates"] == {
        "BBCH45": date(2026, 6, 10),
        "BBCH58": date(2026, 6, 24),
    }
    assert stage_service.actual_stage_calls == []
    assert event_repository.records[0].event_type == EVENT_TYPE_STAGE_CHANGED
    assert event_repository.records[0].payload["currentStageCode"] == "BBCH58"
    assert event_repository.records[0].payload["sourceSnapshotId"] == 12
