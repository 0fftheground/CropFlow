from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_farming_task_query_service
from app.main import app
from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.services import FarmingTaskDetail


@dataclass
class FakeFarmingTaskQueryService:
    def get_detail(self, farming_task_id: int) -> FarmingTaskDetail:
        if farming_task_id == 404:
            raise LookupError("missing")
        return FarmingTaskDetail(
            farming_task=FarmingTask(
                id=farming_task_id,
                planting_plan_id=1,
                calendar_item_id=10,
                task_intent_id=11,
                review_request_id=12,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                title="茎叶除草",
                priority="normal",
                status="pending",
                execution_mode="manual",
                idempotency_key=f"task:{farming_task_id}",
            ),
            operation_plans=[
                OperationPlan(
                    id=20,
                    planting_plan_id=1,
                    farming_task_id=farming_task_id,
                    plan_type="stem_leaf_weed_control",
                    status="active",
                    version=2,
                    parameters={"controlTarget": ["稗草"]},
                    prescription_map={},
                    acceptance_criteria={},
                    execution_mode="manual",
                    idempotency_key="operation-plan:20",
                ),
            ],
            executions=[
                Execution(
                    id=30,
                    planting_plan_id=1,
                    farming_task_id=farming_task_id,
                    operation_plan_id=20,
                    status="completed",
                ),
            ],
            execution_records=[
                ExecutionRecord(
                    id=31,
                    planting_plan_id=1,
                    execution_id=30,
                    record_type="operation_result",
                    record_time=datetime(2026, 5, 22, 12, 0, 0),
                    actual_area=Decimal("12.5000"),
                    result_payload={"executionResult": "completed"},
                    attachments=[],
                ),
            ],
            review_request=ReviewRequest(
                id=12,
                planting_plan_id=1,
                review_type="weed_control_recommendation",
                status="resolved",
                source_entity_type="task_intent",
                source_entity_id=11,
                title="待审核",
                decision="approve",
                decision_payload={"decisionNote": "通过"},
                idempotency_key="review:12",
            ),
            source_task_intent=TaskIntent(
                id=11,
                planting_plan_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                status="converted",
                trigger_type="SurveyResultRecorded",
                trigger_summary="药前调查触发",
                rule_result={"branchType": "control"},
                suggested_action="建议执行茎叶除草",
                source_execution_record_id=32,
                converted_task_id=farming_task_id,
                idempotency_key="intent:11",
            ),
            source_calendar_item=CalendarItem(
                id=10,
                planting_plan_id=1,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_pre_survey",
                title="药前调查",
                suggested_start_date=date(2026, 4, 18),
                suggested_end_date=date(2026, 4, 18),
                status="generated",
                generation_condition={
                    "algorithmCode": "pestDisease.init_regular_survey",
                    "surveyMethod": "一级理论防治日期",
                    "rawPlan": {
                        "status": "need_survey",
                        "survey_window": ["20260502", "20260504"],
                        "survey_method": "一级理论防治日期",
                        "targets": ["二化螟"],
                        "exclude_reasons": {"稻飞虱": "早稻不调查稻飞虱"},
                    },
                },
                generated_task_id=farming_task_id,
                idempotency_key="calendar:10",
            ),
            source_execution_record=ExecutionRecord(
                id=32,
                planting_plan_id=1,
                execution_id=33,
                record_type="survey_result",
                record_time=datetime(2026, 5, 22, 9, 0, 0),
                result_payload={"survey_date": "20260418"},
                attachments=[],
            ),
            downstream_calendar_items=[
                CalendarItem(
                    id=40,
                    planting_plan_id=1,
                    task_category="plant_protection",
                    task_subtype="plant_protection.rice_safety_survey",
                    title="安全性调查",
                    suggested_start_date=date(2026, 4, 23),
                    suggested_end_date=date(2026, 4, 23),
                    status="active",
                    idempotency_key="calendar:40",
                ),
            ],
            event_records=[
                EventRecord(
                    id=50,
                    planting_plan_id=1,
                    event_type="ExecutionCompleted",
                    event_category="execution",
                    event_source="api",
                    source_record_id="31",
                    payload={
                        "taskId": farming_task_id,
                        "executionId": 30,
                        "executionRecordId": 31,
                        "operationDate": "2026-05-22",
                    },
                    occurred_at=datetime(2026, 5, 22, 10, 0, 0),
                    processing_status="processed",
                    idempotency_key="event:50",
                ),
            ],
        )


def test_get_task_detail_route_returns_aggregated_context() -> None:
    app.dependency_overrides[get_farming_task_query_service] = lambda: FakeFarmingTaskQueryService()
    client = TestClient(app)

    response = client.get("/api/tasks/10")

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["id"] == 10
    assert body["operation_plans"][0]["version"] == 2
    assert body["source_task_intent"]["id"] == 11
    assert body["source_calendar_item"]["generation_condition"]["surveyMethod"] == "一级理论防治日期"
    assert body["source_calendar_item"]["generation_condition"]["rawPlan"]["targets"] == ["二化螟"]
    assert body["source_execution_record"]["record_type"] == "survey_result"
    assert body["source_execution_record"]["operation_date"] is None
    assert body["execution_records"][0]["operation_date"] == "2026-05-22"
    assert body["downstream_calendar_items"][0]["task_subtype"] == "plant_protection.rice_safety_survey"
    assert body["event_records"][0]["event_type"] == "ExecutionCompleted"

    app.dependency_overrides.clear()


def test_get_task_detail_route_returns_404_for_missing_task() -> None:
    app.dependency_overrides[get_farming_task_query_service] = lambda: FakeFarmingTaskQueryService()
    client = TestClient(app)

    response = client.get("/api/tasks/404")

    assert response.status_code == 404

    app.dependency_overrides.clear()
