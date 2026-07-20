from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi.testclient import TestClient

from app.api.deps import get_survey_result_service
from app.api.deps import get_task_execution_service
from app.db.session import get_db
from app.main import app
from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask, ReviewRequest, TaskIntent
from app.services import (
    SurveyResultProcessingResult,
    TaskExecutionCompleteInput,
    TaskExecutionCompleteResult,
    TaskExecutionRecordUpdateInput,
    TaskExecutionRecordUpdateResult,
)


@dataclass
class FakeSurveyResultService:
    def record_survey_result(
        self,
        farming_task_id: int,
        result_payload: dict,
        *,
        actual_start_at=None,
        actual_end_at=None,
    ) -> SurveyResultProcessingResult:
        if farming_task_id == 404:
            raise LookupError("missing")
        if farming_task_id == 400:
            raise ValueError("invalid service evaluation payload")
        return SurveyResultProcessingResult(
            execution_record=ExecutionRecord(
                id=11,
                planting_plan_id=1,
                execution_id=7,
                record_type="survey_result",
                result_payload=result_payload,
                attachments=[],
            ),
            event_record=EventRecord(
                id=12,
                event_type="SurveyResultRecorded",
                event_category="runtime",
                event_source="api",
                payload={},
                occurred_at=datetime(2026, 5, 22, 10, 0, 0),
                idempotency_key="event:12",
            ),
            farming_tasks=(
                [
                    FarmingTask(
                        id=15,
                        planting_plan_id=1,
                        task_category="plant_protection",
                        task_subtype="plant_protection.service_effect_survey",
                        title="服务人员现场确认",
                        status="pending",
                        execution_mode="manual",
                        idempotency_key="task:15",
                    ),
                ]
                if farming_task_id == 11
                else []
            ),
            task_intents=(
                []
                if farming_task_id == 11
                else [
                    TaskIntent(
                        id=13,
                        planting_plan_id=1,
                        task_category="plant_protection",
                        task_subtype="plant_protection.stem_leaf_weed_control",
                        trigger_type="SurveyResultRecorded",
                        rule_result={},
                        idempotency_key="intent:13",
                    ),
                ]
            ),
            review_requests=(
                []
                if farming_task_id == 11
                else [
                    ReviewRequest(
                        id=14,
                        planting_plan_id=1,
                        review_type="weed_control_recommendation",
                        source_entity_type="task_intent",
                        source_entity_id=13,
                        title="待审核",
                        decision_payload={},
                        idempotency_key="review:14",
                    ),
                ]
            ),
        )


@dataclass
class FakeTaskExecutionService:
    def complete_task(
        self,
        farming_task_id: int,
        payload: TaskExecutionCompleteInput,
    ) -> TaskExecutionCompleteResult:
        if farming_task_id == 404:
            raise LookupError("missing")
        return TaskExecutionCompleteResult(
            execution=Execution(
                id=21,
                planting_plan_id=1,
                farming_task_id=farming_task_id,
                status="completed",
            ),
            execution_record=ExecutionRecord(
                id=22,
                planting_plan_id=1,
                execution_id=21,
                record_type="operation_result",
                result_payload=payload.result_payload,
                attachments=[],
            ),
            event_record=EventRecord(
                id=23,
                event_type="ExecutionCompleted",
                event_category="execution",
                event_source="api",
                payload={"operationDate": payload.operation_date.isoformat()},
                occurred_at=datetime(2026, 5, 22, 12, 0, 0),
                idempotency_key="event:23",
            ),
            calendar_items=[
                CalendarItem(
                    id=24,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.rice_safety_survey",
                    title="安全性调查",
                    suggested_start_date=datetime(2026, 4, 23).date(),
                    suggested_end_date=datetime(2026, 4, 23).date(),
                    idempotency_key="calendar:24",
                ),
                CalendarItem(
                    id=25,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.control_effect_survey",
                    title="防效调查",
                    suggested_start_date=datetime(2026, 4, 27).date(),
                    suggested_end_date=datetime(2026, 4, 27).date(),
                    idempotency_key="calendar:25",
                ),
            ],
        )

    def update_latest_execution_record(
        self,
        farming_task_id: int,
        payload: TaskExecutionRecordUpdateInput,
    ) -> TaskExecutionRecordUpdateResult:
        if farming_task_id == 404:
            raise LookupError("missing")
        if farming_task_id == 400:
            raise ValueError("no execution record")
        updated_fields = ["actual_amount", "result_payload"]
        if payload.operation_date is not None:
            updated_fields.insert(0, "operation_date")
        return TaskExecutionRecordUpdateResult(
            execution=Execution(
                id=21,
                planting_plan_id=1,
                farming_task_id=farming_task_id,
                status="completed",
            ),
            execution_record=ExecutionRecord(
                id=22,
                planting_plan_id=1,
                execution_id=21,
                record_type="operation_result",
                result_payload=payload.result_payload or {},
                attachments=[],
            ),
            event_record=EventRecord(
                id=24,
                event_type="ExecutionRecordUpdated",
                event_category="execution",
                event_source="api",
                payload={},
                occurred_at=datetime(2026, 5, 22, 12, 5, 0),
                idempotency_key="event:24",
            ),
            operation_date=payload.operation_date,
            updated_fields=updated_fields,
        )


class DummySession:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_create_survey_result_route_returns_m3_outputs() -> None:
    app.dependency_overrides[get_survey_result_service] = lambda: FakeSurveyResultService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post(
        "/api/tasks/10/survey-results",
        json={
            "result_payload": {
                "survey_date": "20260418",
                "rice_leaf_age": 4.5,
            },
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "execution_record_id": 11,
        "event_record_id": 12,
        "farming_task_ids": [],
        "task_intent_ids": [13],
        "review_request_ids": [14],
    }

    app.dependency_overrides.clear()


def test_create_survey_result_route_returns_404_for_missing_task() -> None:
    app.dependency_overrides[get_survey_result_service] = lambda: FakeSurveyResultService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post("/api/tasks/404/survey-results", json={"result_payload": {}})

    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_create_survey_result_route_returns_followup_task_ids() -> None:
    app.dependency_overrides[get_survey_result_service] = lambda: FakeSurveyResultService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post("/api/tasks/11/survey-results", json={"result_payload": {"is_satisfied": False}})

    assert response.status_code == 201
    assert response.json() == {
        "execution_record_id": 11,
        "event_record_id": 12,
        "farming_task_ids": [15],
        "task_intent_ids": [],
        "review_request_ids": [],
    }

    app.dependency_overrides.clear()


def test_create_survey_result_route_returns_400_for_invalid_payload() -> None:
    app.dependency_overrides[get_survey_result_service] = lambda: FakeSurveyResultService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post("/api/tasks/400/survey-results", json={"result_payload": {}})

    assert response.status_code == 400

    app.dependency_overrides.clear()


def test_complete_task_execution_route_returns_calendar_item_ids() -> None:
    app.dependency_overrides[get_task_execution_service] = lambda: FakeTaskExecutionService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post(
        "/api/tasks/10/execution-completions",
        json={
            "operation_date": "2026-04-20T00:00:00",
            "result_payload": {"actual": "completed"},
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "execution_id": 21,
        "execution_record_id": 22,
        "event_record_id": 23,
        "operation_date": "2026-04-20",
        "calendar_item_ids": [24, 25],
    }

    app.dependency_overrides.clear()


def test_complete_task_execution_route_returns_404_for_missing_task() -> None:
    app.dependency_overrides[get_task_execution_service] = lambda: FakeTaskExecutionService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.post("/api/tasks/404/execution-completions", json={"operation_date": "2026-04-20T00:00:00"})

    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_update_latest_execution_record_route_returns_updated_fields() -> None:
    app.dependency_overrides[get_task_execution_service] = lambda: FakeTaskExecutionService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    response = client.patch(
        "/api/tasks/10/execution-records/latest",
        json={
            "operation_date": "2026-05-12T00:00:00",
            "actual_amount": "12.5",
            "result_payload": {"note": "corrected"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "execution_id": 21,
        "execution_record_id": 22,
        "event_record_id": 24,
        "operation_date": "2026-05-12",
        "updated_fields": ["operation_date", "actual_amount", "result_payload"],
    }

    app.dependency_overrides.clear()


def test_update_latest_execution_record_route_maps_errors() -> None:
    app.dependency_overrides[get_task_execution_service] = lambda: FakeTaskExecutionService()
    app.dependency_overrides[get_db] = lambda: DummySession()
    client = TestClient(app)

    missing_response = client.patch("/api/tasks/404/execution-records/latest", json={"actual_amount": "1"})
    invalid_response = client.patch("/api/tasks/400/execution-records/latest", json={"actual_amount": "1"})

    assert missing_response.status_code == 404
    assert invalid_response.status_code == 400

    app.dependency_overrides.clear()
