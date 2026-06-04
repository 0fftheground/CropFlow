from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_planting_plan_query_service, get_planting_plan_service
from app.db.session import get_db
from app.main import app
from app.models import (
    CalendarItem,
    CropStageState,
    CropThermalTimeState,
    EventRecord,
    FarmingTask,
    OperationPlan,
    PlantingPlan,
    ReviewRequest,
    StagePredictionSnapshot,
    TaskIntent,
)
from app.services import PlantingPlanDetails


def _make_details(plan_id: int, *, status: str = "draft") -> PlantingPlanDetails:
    return PlantingPlanDetails(
        planting_plan=PlantingPlan(
            id=plan_id,
            plan_code=f"PLAN-{plan_id:03d}",
            plan_name=f"计划 {plan_id}",
            farm_id=1,
            culti_type_code=5,
            planting_method_code=1,
            crop_name="水稻",
            variety_id=3,
            variety_name="黄广农占",
            sowing_date=date(2026, 4, 10),
            transplant_leaf_age=Decimal("4.50"),
            status=status,
            task_generation_window_days=14,
            metadata_payload={"source": "test"},
            created_at=datetime(2026, 5, 22, 10, 0, 0),
            updated_at=datetime(2026, 5, 22, 10, 0, 0),
        ),
        field_ids=[10, 11],
    )


@dataclass
class FakePlantingPlanService:
    created_payload: object | None = None
    updated_payload: object | None = None
    actual_stage_payload: object | None = None
    list_statuses: list[str] | None = None

    def create(self, payload):
        self.created_payload = payload
        return _make_details(1)

    def get_details(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return _make_details(planting_plan_id)

    def list_by_statuses(self, statuses):
        self.list_statuses = statuses
        return [_make_details(2, status="active")]

    def update(self, planting_plan_id: int, payload):
        self.updated_payload = payload
        return _make_details(planting_plan_id, status=payload.status or "draft")

    def record_actual_stages(self, planting_plan_id: int, payload):
        self.actual_stage_payload = payload
        stage_code, effective_date = next(iter(payload.stage_dates.items()))
        return [
            EventRecord(
                id=12,
                planting_plan_id=planting_plan_id,
                event_type="ActualStageRecorded",
                event_category="runtime",
                event_source="api",
                source_system="cropflow",
                source_record_id=payload.source_record_id,
                payload={
                    "stageCode": stage_code,
                    "effectiveDate": effective_date.isoformat(),
                    "sourceRecordId": payload.source_record_id,
                    "operatorId": payload.operator_id,
                    "note": payload.note,
                    "metadata": payload.metadata_payload,
                },
                occurred_at=datetime(2026, 6, 18, 9, 0, 0),
                processing_status="received",
                idempotency_key="actual-stage-recorded:1:58:2026-06-18:manual-1",
            ),
        ]


class FakePlantingPlanQueryService:
    def list_calendar_items(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return [
            CalendarItem(
                id=1,
                planting_plan_id=planting_plan_id,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_pre_survey",
                title="茎叶除草药前调查",
                description="调查杂草情况",
                suggested_start_date=date(2026, 4, 18),
                suggested_end_date=date(2026, 4, 18),
                status="active",
                generation_condition={"algorithmCode": "weed_survey_date_diagnosis"},
                idempotency_key="calendar-item:1:test",
            ),
        ]

    def list_farming_tasks(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return [
            FarmingTask(
                id=1,
                planting_plan_id=planting_plan_id,
                calendar_item_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_pre_survey",
                title="茎叶除草药前调查",
                description="调查杂草情况",
                planned_start_at=datetime(2026, 4, 18, 0, 0, 0),
                planned_end_at=datetime(2026, 4, 18, 23, 59, 59),
                priority="normal",
                status="pending",
                execution_mode="manual",
                generation_reason="calendar_item:1:window_reached",
                idempotency_key="farming-task:calendar-item:1",
            ),
        ]

    def list_task_intents(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return [
            TaskIntent(
                id=1,
                planting_plan_id=planting_plan_id,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                priority="normal",
                status="pending",
                trigger_type="SurveyResultRecorded",
                trigger_summary="药前调查触发防治建议",
                rule_result={"branchType": "weed_control"},
                suggested_action="建议执行茎叶除草",
                need_more_info_fields={},
                idempotency_key="task-intent:1",
            ),
        ]

    def list_review_requests(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return [
            ReviewRequest(
                id=1,
                planting_plan_id=planting_plan_id,
                review_type="weed_control_recommendation",
                status="open",
                priority="normal",
                source_entity_type="task_intent",
                source_entity_id=1,
                title="茎叶除草建议待审核",
                decision_payload={"contextRefs": {"taskIntentId": 1}},
                idempotency_key="review-request:1",
            ),
        ]

    def list_event_records(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return [
            EventRecord(
                id=9,
                planting_plan_id=planting_plan_id,
                event_type="PlanCreated",
                event_category="plan",
                event_source="api",
                source_system="cropflow",
                payload={"planCode": "PLAN-001"},
                occurred_at=datetime(2026, 5, 22, 10, 0, 0),
                processing_status="processed",
                idempotency_key="event:9",
            ),
        ]

    def get_crop_stage_state(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return CropStageState(
            id=7,
            planting_plan_id=planting_plan_id,
            current_stage_code="tillering",
            current_stage_name="分蘖期",
            stage_source="predicted",
            effective_date=date(2026, 4, 20),
            source_snapshot_id=8,
            last_updated_at=datetime(2026, 5, 27, 9, 0, 0),
            version=2,
        )

    def get_crop_thermal_time_state(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return CropThermalTimeState(
            id=8,
            planting_plan_id=planting_plan_id,
            accumulated_thermal_time=Decimal("780.00"),
            thermal_time_unit="degree_day",
            base_temperature=Decimal("10.00"),
            start_date=date(2026, 4, 10),
            last_calculated_date=date(2026, 5, 27),
            threshold_snapshot_id=8,
            data_version="weather-20260527-v1",
        )

    def get_latest_stage_prediction_snapshot(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return StagePredictionSnapshot(
            id=8,
            planting_plan_id=planting_plan_id,
            prediction_version=3,
            prediction_source="plan_change",
            algorithm_code="stage_prediction_algorithm",
            algorithm_version="v1.0.0",
            input_payload={"as_of_date": "2026-05-27"},
            stage_timeline={
                "stages": [
                    {
                        "stage_code": "tillering",
                        "stage_name": "分蘖期",
                        "start_date": "2026-04-20",
                        "end_date": "2026-06-09",
                        "key_date": "2026-04-20",
                    },
                ],
            },
            thermal_thresholds={"accumulated_thermal_time": 780},
        )

    def get_debug_snapshot(self, planting_plan_id: int):
        if planting_plan_id == 404:
            raise LookupError("missing")
        return type(
            "DebugSnapshot",
            (),
            {
                "planting_plan": _make_details(planting_plan_id).planting_plan,
                "field_ids": [10, 11],
                "calendar_items": self.list_calendar_items(planting_plan_id),
                "farming_tasks": self.list_farming_tasks(planting_plan_id),
                "task_intents": self.list_task_intents(planting_plan_id),
                "review_requests": self.list_review_requests(planting_plan_id),
                "operation_plans": [
                    OperationPlan(
                        id=3,
                        planting_plan_id=planting_plan_id,
                        farming_task_id=1,
                        plan_type="prescription",
                        status="active",
                        version=1,
                        execution_mode="manual",
                        parameters={"dose": "30ml"},
                        prescription_map={"herbicide": "A"},
                        basis="test",
                    ),
                ],
                "event_records": self.list_event_records(planting_plan_id),
                "crop_stage_state": self.get_crop_stage_state(planting_plan_id),
                "crop_thermal_time_state": self.get_crop_thermal_time_state(planting_plan_id),
                "stage_prediction_snapshots": [self.get_latest_stage_prediction_snapshot(planting_plan_id)],
            },
        )()


class DummySession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_create_and_list_planting_plans_routes() -> None:
    fake_service = FakePlantingPlanService()
    app.dependency_overrides[get_planting_plan_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    create_response = client.post(
        "/api/planting-plans",
        json={
            "plan_name": "早稻计划",
            "farm_id": 1,
            "field_ids": [10, 11],
            "culti_type_code": 5,
            "planting_method_code": 1,
            "crop_name": "水稻",
            "variety_id": 3,
            "sowing_date": "2026-04-10",
        },
    )
    list_response = client.get("/api/planting-plans", params=[("statuses", "active")])

    assert create_response.status_code == 201
    assert create_response.json()["plan_code"] == "PLAN-001"
    assert fake_service.created_payload.plan_code is None
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "active"
    assert fake_service.list_statuses == ["active"]

    app.dependency_overrides.clear()


def test_create_planting_plan_route_allows_missing_field_ids() -> None:
    fake_service = FakePlantingPlanService()
    app.dependency_overrides[get_planting_plan_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post(
        "/api/planting-plans",
        json={
            "plan_name": "早稻计划",
            "farm_id": 1,
            "culti_type_code": 5,
            "planting_method_code": 1,
            "crop_name": "水稻",
            "variety_id": 3,
            "sowing_date": "2026-04-10",
        },
    )

    assert response.status_code == 201
    assert fake_service.created_payload.field_ids == []

    app.dependency_overrides.clear()


def test_get_and_patch_planting_plan_routes() -> None:
    fake_service = FakePlantingPlanService()
    app.dependency_overrides[get_planting_plan_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    get_response = client.get("/api/planting-plans/1")
    patch_response = client.patch("/api/planting-plans/1", json={"status": "completed"})

    assert get_response.status_code == 200
    assert get_response.json()["id"] == 1
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "completed"

    app.dependency_overrides.clear()


def test_record_actual_stages_route_accepts_code_date_map() -> None:
    fake_service = FakePlantingPlanService()
    app.dependency_overrides[get_planting_plan_service] = lambda: fake_service
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post(
        "/api/planting-plans/1/actual-stages",
        json={
            "stages": {"BBCH58": "2026-06-18"},
            "source_record_id": "manual-1",
            "operator_id": "user-7",
            "note": "田间观测齐穗",
        },
    )

    assert response.status_code == 201
    assert response.json()[0]["event_type"] == "ActualStageRecorded"
    assert response.json()[0]["payload"]["stageCode"] == "BBCH58"
    assert fake_service.actual_stage_payload.stage_dates == {"BBCH58": date(2026, 6, 18)}

    app.dependency_overrides.clear()


def test_list_calendar_items_and_tasks_routes() -> None:
    app.dependency_overrides[get_planting_plan_query_service] = lambda: FakePlantingPlanQueryService()
    client = TestClient(app)

    calendar_response = client.get("/api/planting-plans/1/calendar-items")
    tasks_response = client.get("/api/planting-plans/1/tasks")
    intents_response = client.get("/api/planting-plans/1/task-intents")
    reviews_response = client.get("/api/planting-plans/1/review-requests")
    events_response = client.get("/api/planting-plans/1/event-records")
    stage_response = client.get("/api/planting-plans/1/stage-state")
    thermal_response = client.get("/api/planting-plans/1/thermal-time-state")
    snapshot_response = client.get("/api/planting-plans/1/stage-predictions/latest")
    debug_response = client.get("/api/planting-plans/1/debug-snapshot")

    assert calendar_response.status_code == 200
    assert calendar_response.json()[0]["task_subtype"] == "plant_protection.stem_leaf_weed_pre_survey"
    assert tasks_response.status_code == 200
    assert tasks_response.json()[0]["calendar_item_id"] == 1
    assert intents_response.status_code == 200
    assert intents_response.json()[0]["status"] == "pending"
    assert reviews_response.status_code == 200
    assert reviews_response.json()[0]["source_entity_type"] == "task_intent"
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_type"] == "PlanCreated"
    assert stage_response.status_code == 200
    assert stage_response.json()["current_stage_code"] == "tillering"
    assert thermal_response.status_code == 200
    assert thermal_response.json()["accumulated_thermal_time"] == "780.00"
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["algorithm_code"] == "stage_prediction_algorithm"
    assert debug_response.status_code == 200
    assert debug_response.json()["operation_plans"][0]["farming_task_id"] == 1
    assert debug_response.json()["stage_prediction_snapshots"][0]["prediction_version"] == 3

    app.dependency_overrides.clear()
