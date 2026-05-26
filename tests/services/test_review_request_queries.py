from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models import EventRecord, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.services import ReviewRequestQueryService


@dataclass
class FakeReviewRequestRepository:
    review_request: ReviewRequest | None = None
    source_entity: TaskIntent | None = None

    def get(self, review_request_id: int) -> ReviewRequest | None:
        return self.review_request if self.review_request and self.review_request.id == review_request_id else None

    def get_source_entity(self, review_request: ReviewRequest):
        return self.source_entity


@dataclass
class FakeTaskIntentRepository:
    def get(self, task_intent_id: int):
        return None


@dataclass
class FakeFarmingTaskRepository:
    task: FarmingTask | None = None

    def get(self, farming_task_id: int) -> FarmingTask | None:
        return self.task if self.task and self.task.id == farming_task_id else None


@dataclass
class FakeOperationPlanRepository:
    items: list[OperationPlan] = field(default_factory=list)

    def list_by_task(self, farming_task_id: int) -> list[OperationPlan]:
        return [item for item in self.items if item.farming_task_id == farming_task_id]


@dataclass
class FakeExecutionRecordRepository:
    record: ExecutionRecord | None = None

    def get(self, execution_record_id: int) -> ExecutionRecord | None:
        return self.record if self.record and self.record.id == execution_record_id else None


@dataclass
class FakeEventRecordRepository:
    items: list[EventRecord] = field(default_factory=list)

    def list_by_plan(self, planting_plan_id: int) -> list[EventRecord]:
        return [item for item in self.items if item.planting_plan_id == planting_plan_id]


def test_review_request_query_service_returns_linked_context() -> None:
    review_request = ReviewRequest(
        id=1,
        planting_plan_id=10,
        review_type="weed_control_recommendation",
        source_entity_type="task_intent",
        source_entity_id=2,
        title="待审核",
        decision_payload={"contextRefs": {"sourceExecutionRecordId": 9}},
        idempotency_key="review:1",
    )
    source_task_intent = TaskIntent(
        id=2,
        planting_plan_id=10,
        task_category="plant_protection",
        task_subtype="plant_protection.stem_leaf_weed_control",
        trigger_type="SurveyResultRecorded",
        rule_result={},
        converted_task_id=3,
        source_execution_record_id=9,
        idempotency_key="intent:2",
    )
    service = ReviewRequestQueryService(
        review_request_repository=FakeReviewRequestRepository(review_request, source_task_intent),
        task_intent_repository=FakeTaskIntentRepository(),
        farming_task_repository=FakeFarmingTaskRepository(
            FarmingTask(
                id=3,
                planting_plan_id=10,
                task_category="plant_protection",
                task_subtype="plant_protection.stem_leaf_weed_control",
                title="茎叶除草",
                idempotency_key="task:3",
            ),
        ),
        operation_plan_repository=FakeOperationPlanRepository(
            [OperationPlan(id=4, planting_plan_id=10, farming_task_id=3, plan_type="weed", idempotency_key="op:4")],
        ),
        execution_record_repository=FakeExecutionRecordRepository(
            ExecutionRecord(
                id=9,
                planting_plan_id=10,
                execution_id=99,
                record_type="survey_result",
                result_payload={"survey_date": "20260418"},
                attachments=[],
            ),
        ),
        event_record_repository=FakeEventRecordRepository(
            [
                EventRecord(
                    id=5,
                    planting_plan_id=10,
                    event_type="ReviewRequestCreated",
                    event_category="runtime",
                    event_source="orchestrator",
                    source_record_id="1",
                    payload={"reviewRequestId": 1},
                    occurred_at=datetime(2026, 5, 22, 10, 0, 0),
                    processing_status="processed",
                    idempotency_key="event:5",
                ),
            ],
        ),
    )

    detail = service.get_detail(1)

    assert detail.review_request.id == 1
    assert detail.source_task_intent.id == 2
    assert detail.linked_farming_task.id == 3
    assert detail.operation_plans[0].id == 4
    assert detail.source_execution_record.id == 9
    assert detail.event_records[0].id == 5
