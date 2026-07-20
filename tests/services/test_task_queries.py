from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.services import FarmingTaskQueryService


@dataclass
class FakeFarmingTaskRepository:
    task: FarmingTask | None

    def get(self, farming_task_id: int) -> FarmingTask | None:
        return self.task if self.task and self.task.id == farming_task_id else None


@dataclass
class FakeOperationPlanRepository:
    items: list[OperationPlan] = field(default_factory=list)

    def list_by_task(self, farming_task_id: int) -> list[OperationPlan]:
        return [item for item in self.items if item.farming_task_id == farming_task_id]


@dataclass
class FakeExecutionRepository:
    items: list[Execution] = field(default_factory=list)

    def list_by_task(self, farming_task_id: int) -> list[Execution]:
        return [item for item in self.items if item.farming_task_id == farming_task_id]


@dataclass
class FakeExecutionRecordRepository:
    items: list[ExecutionRecord] = field(default_factory=list)

    def list_by_task(self, farming_task_id: int) -> list[ExecutionRecord]:
        return list(self.items)

    def get(self, execution_record_id: int) -> ExecutionRecord | None:
        return next((item for item in self.items if item.id == execution_record_id), None)


@dataclass
class FakeReviewRequestRepository:
    review_request: ReviewRequest | None = None

    def get(self, review_request_id: int) -> ReviewRequest | None:
        return self.review_request if self.review_request and self.review_request.id == review_request_id else None

    def get_source_entity(self, review_request: ReviewRequest):
        return None


@dataclass
class FakeTaskIntentRepository:
    task_intent: TaskIntent | None = None

    def get(self, task_intent_id: int) -> TaskIntent | None:
        return self.task_intent if self.task_intent and self.task_intent.id == task_intent_id else None


@dataclass
class FakeCalendarItemRepository:
    source_item: CalendarItem | None = None
    downstream_items: list[CalendarItem] = field(default_factory=list)

    def get(self, calendar_item_id: int) -> CalendarItem | None:
        return self.source_item if self.source_item and self.source_item.id == calendar_item_id else None

    def list_by_parent_task(self, parent_task_id: int) -> list[CalendarItem]:
        return list(self.downstream_items)


@dataclass
class FakeEventRecordRepository:
    items: list[EventRecord] = field(default_factory=list)

    def list_by_plan(self, planting_plan_id: int) -> list[EventRecord]:
        return [item for item in self.items if item.planting_plan_id == planting_plan_id]


def test_farming_task_query_service_returns_aggregated_detail() -> None:
    task = FarmingTask(
        id=1,
        planting_plan_id=10,
        calendar_item_id=2,
        task_intent_id=3,
        review_request_id=4,
        task_category="plant_protection",
        task_subtype="plant_protection.stem_leaf_weed_control",
        title="茎叶除草",
        source_execution_record_id=6,
        idempotency_key="task:1",
    )
    service = FarmingTaskQueryService(
        farming_task_repository=FakeFarmingTaskRepository(task),
        operation_plan_repository=FakeOperationPlanRepository(
            [OperationPlan(id=20, planting_plan_id=10, farming_task_id=1, plan_type="weed", idempotency_key="op:20")],
        ),
        execution_repository=FakeExecutionRepository(
            [Execution(id=30, planting_plan_id=10, farming_task_id=1, status="completed")],
        ),
        execution_record_repository=FakeExecutionRecordRepository(
            [
                ExecutionRecord(
                    id=6,
                    planting_plan_id=10,
                    execution_id=30,
                    record_type="survey_result",
                    result_payload={"survey_date": "20260418"},
                    attachments=[],
                ),
            ],
        ),
        review_request_repository=FakeReviewRequestRepository(
            ReviewRequest(
                id=4,
                planting_plan_id=10,
                review_type="weed_control",
                source_entity_type="task_intent",
                source_entity_id=3,
                title="待审核",
                idempotency_key="review:4",
            ),
        ),
        task_intent_repository=FakeTaskIntentRepository(
            TaskIntent(
                id=3,
                planting_plan_id=10,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                trigger_type="SurveyResultRecorded",
                rule_result={},
                idempotency_key="intent:3",
            ),
        ),
        calendar_item_repository=FakeCalendarItemRepository(
            source_item=CalendarItem(
                id=2,
                planting_plan_id=10,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_pre_survey",
                title="药前调查",
                suggested_start_date=date(2026, 4, 18),
                suggested_end_date=date(2026, 4, 18),
                status="generated",
                idempotency_key="calendar:2",
            ),
            downstream_items=[
                CalendarItem(
                    id=8,
                    planting_plan_id=10,
                    task_category="plant_protection",
                    task_subtype="plant_protection.rice_safety_survey",
                    title="安全性调查",
                    suggested_start_date=date(2026, 4, 23),
                    suggested_end_date=date(2026, 4, 23),
                    status="active",
                    idempotency_key="calendar:8",
                ),
            ],
        ),
        event_record_repository=FakeEventRecordRepository(
            [
                EventRecord(
                    id=50,
                    planting_plan_id=10,
                    event_type="FarmingTaskCreated",
                    event_category="runtime",
                    event_source="orchestrator",
                    source_record_id="1",
                    payload={"farmingTaskId": 1},
                    occurred_at=datetime(2026, 5, 22, 10, 0, 0),
                    processing_status="processed",
                    idempotency_key="event:50",
                ),
            ],
        ),
    )

    detail = service.get_detail(1)

    assert detail.farming_task.id == 1
    assert detail.operation_plans[0].id == 20
    assert detail.executions[0].id == 30
    assert detail.source_calendar_item.id == 2
    assert detail.source_execution_record.id == 6
    assert detail.downstream_calendar_items[0].id == 8
    assert detail.event_records[0].id == 50
