from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.core.constants import EVENT_TYPE_REVIEW_REQUEST_RESOLVED
from app.models import EventRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.orchestrator.core import PlanOrchestrator, ReviewRequestResolvedHandler
from app.services import ReviewRequestResolveInput, ReviewRequestService


@dataclass
class FakeReviewRequestRepository:
    item: ReviewRequest

    def get(self, review_request_id: int) -> ReviewRequest | None:
        return self.item if self.item.id == review_request_id else None


@dataclass
class FakeTaskIntentRepository:
    item: TaskIntent

    def get(self, task_intent_id: int) -> TaskIntent | None:
        return self.item if self.item.id == task_intent_id else None


@dataclass
class FakeFarmingTaskRepository:
    items: list[FarmingTask] = field(default_factory=list)
    next_id: int = 100

    def add(self, task: FarmingTask) -> FarmingTask:
        self.items.append(task)
        return task

    def flush(self) -> None:
        for task in self.items:
            if task.id is None:
                task.id = self.next_id
                self.next_id += 1


@dataclass
class FakeOperationPlanRepository:
    items: list[OperationPlan] = field(default_factory=list)
    next_id: int = 200

    def add(self, operation_plan: OperationPlan) -> OperationPlan:
        self.items.append(operation_plan)
        return operation_plan

    def flush(self) -> None:
        for operation_plan in self.items:
            if operation_plan.id is None:
                operation_plan.id = self.next_id
                self.next_id += 1


@dataclass
class FakeEventRecordRepository:
    items: list[EventRecord] = field(default_factory=list)
    next_id: int = 1

    def add(self, event_record: EventRecord) -> EventRecord:
        if event_record.id is None:
            event_record.id = self.next_id
            self.next_id += 1
        self.items.append(event_record)
        return event_record

    def flush(self) -> None:
        return None


def make_service() -> tuple[
    ReviewRequestService,
    TaskIntent,
    ReviewRequest,
    FakeFarmingTaskRepository,
    FakeOperationPlanRepository,
    FakeEventRecordRepository,
]:
    task_intent = TaskIntent(
        id=10,
        planting_plan_id=1,
        task_category="plant_protection",
        task_subtype="plant_protection.stem_leaf_weed_control",
        status="pending",
        trigger_type="SurveyResultRecorded",
        trigger_summary="药前调查达到防治条件。",
        suggested_action="建议执行茎叶除草",
        parent_task_id=5,
        source_execution_id=6,
        source_execution_record_id=7,
        rule_result={
            "algorithmCode": "weed_treatment_diagnosis",
            "proposedTask": {
                "title": "茎叶除草",
                "recommendedControlDate": ["2026-04-20", "2026-04-20"],
            },
            "proposedPlan": {
                "controlPlan": {"prescriptions": [{"pesticide": "示例农药"}]},
                "basis": "杂草密度达到阈值。",
            },
        },
        idempotency_key="task-intent:10",
    )
    review_request = ReviewRequest(
        id=20,
        planting_plan_id=1,
        review_type="weed_control_recommendation",
        status="open",
        source_entity_type="task_intent",
        source_entity_id=10,
        title="茎叶除草建议待审核",
        decision_payload={},
        idempotency_key="review-request:20",
    )
    task_intent_repo = FakeTaskIntentRepository(task_intent)
    review_repo = FakeReviewRequestRepository(review_request)
    farming_task_repo = FakeFarmingTaskRepository()
    operation_plan_repo = FakeOperationPlanRepository()
    event_repo = FakeEventRecordRepository()
    orchestrator = PlanOrchestrator(
        {
            EVENT_TYPE_REVIEW_REQUEST_RESOLVED: ReviewRequestResolvedHandler(
                task_intent_repository=task_intent_repo,
                review_request_repository=review_repo,
                farming_task_repository=farming_task_repo,
                operation_plan_repository=operation_plan_repo,
                event_record_repository=event_repo,
            ),
        },
    )
    service = ReviewRequestService(
        review_request_repository=review_repo,
        event_record_repository=event_repo,
        plan_orchestrator=orchestrator,
    )
    return service, task_intent, review_request, farming_task_repo, operation_plan_repo, event_repo


def test_approve_review_request_converts_task_intent_to_task_and_operation_plan() -> None:
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, event_repo = make_service()

    result = service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="approve",
            decision_payload={},
            decision_note="同意执行",
            resolved_by="agronomist-1",
        ),
    )

    assert review_request.status == "resolved"
    assert task_intent.status == "converted"
    assert task_intent.converted_task_id == 100
    assert farming_task_repo.items[0].task_intent_id == 10
    assert farming_task_repo.items[0].review_request_id == 20
    assert farming_task_repo.items[0].planned_start_at.date() == date(2026, 4, 20)
    assert operation_plan_repo.items[0].farming_task_id == 100
    assert operation_plan_repo.items[0].algorithm_code == "weed_treatment_diagnosis"
    assert result.farming_tasks == farming_task_repo.items
    assert [item.event_type for item in event_repo.items] == [
        "ReviewRequestResolved",
        "FarmingTaskCreated",
        "OperationPlanCreated",
    ]


def test_no_action_review_request_marks_task_intent_no_action() -> None:
    service, task_intent, review_request, farming_task_repo, operation_plan_repo, _ = make_service()

    result = service.resolve(
        20,
        ReviewRequestResolveInput(
            decision="no_action",
            decision_payload={},
            decision_note="现场确认无需处理",
            resolved_by="agronomist-1",
        ),
    )

    assert review_request.status == "resolved"
    assert task_intent.status == "no_action"
    assert task_intent.no_action_reason == "现场确认无需处理"
    assert farming_task_repo.items == []
    assert operation_plan_repo.items == []
    assert result.task_intents == [task_intent]
