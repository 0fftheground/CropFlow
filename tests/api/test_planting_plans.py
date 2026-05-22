from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_planting_plan_query_service, get_planting_plan_service
from app.db.session import get_db
from app.main import app
from app.models import CalendarItem, FarmingTask, PlantingPlan, ReviewRequest, TaskIntent
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
            "plan_code": "PLAN-001",
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
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "active"
    assert fake_service.list_statuses == ["active"]

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


def test_list_calendar_items_and_tasks_routes() -> None:
    app.dependency_overrides[get_planting_plan_query_service] = lambda: FakePlantingPlanQueryService()
    client = TestClient(app)

    calendar_response = client.get("/api/planting-plans/1/calendar-items")
    tasks_response = client.get("/api/planting-plans/1/tasks")
    intents_response = client.get("/api/planting-plans/1/task-intents")
    reviews_response = client.get("/api/planting-plans/1/review-requests")

    assert calendar_response.status_code == 200
    assert calendar_response.json()[0]["task_subtype"] == "plant_protection.stem_leaf_weed_pre_survey"
    assert tasks_response.status_code == 200
    assert tasks_response.json()[0]["calendar_item_id"] == 1
    assert intents_response.status_code == 200
    assert intents_response.json()[0]["status"] == "pending"
    assert reviews_response.status_code == 200
    assert reviews_response.json()[0]["source_entity_type"] == "task_intent"

    app.dependency_overrides.clear()
