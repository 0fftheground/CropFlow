from __future__ import annotations

from dataclasses import dataclass

from app.models import EventRecord, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.repositories import (
    EventRecordRepository,
    ExecutionRecordRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    ReviewRequestRepository,
    TaskIntentRepository,
)


@dataclass(slots=True)
class ReviewRequestDetail:
    review_request: ReviewRequest
    source_task_intent: TaskIntent | None
    linked_farming_task: FarmingTask | None
    operation_plans: list[OperationPlan]
    source_execution_record: ExecutionRecord | None
    event_records: list[EventRecord]


class ReviewRequestQueryService:
    def __init__(
        self,
        review_request_repository: ReviewRequestRepository,
        task_intent_repository: TaskIntentRepository,
        farming_task_repository: FarmingTaskRepository,
        operation_plan_repository: OperationPlanRepository,
        execution_record_repository: ExecutionRecordRepository,
        event_record_repository: EventRecordRepository,
    ) -> None:
        self.review_request_repository = review_request_repository
        self.task_intent_repository = task_intent_repository
        self.farming_task_repository = farming_task_repository
        self.operation_plan_repository = operation_plan_repository
        self.execution_record_repository = execution_record_repository
        self.event_record_repository = event_record_repository

    def get_detail(self, review_request_id: int) -> ReviewRequestDetail:
        review_request = self.review_request_repository.get(review_request_id)
        if review_request is None:
            raise LookupError(f"Review request {review_request_id} does not exist.")

        source_task_intent: TaskIntent | None = None
        if review_request.source_entity_type in {"task_intent", "cf_task_intent"}:
            source_entity = self.review_request_repository.get_source_entity(review_request)
            if isinstance(source_entity, TaskIntent):
                source_task_intent = source_entity

        linked_farming_task = None
        if source_task_intent is not None and source_task_intent.converted_task_id is not None:
            linked_farming_task = self.farming_task_repository.get(source_task_intent.converted_task_id)

        source_execution_record = None
        source_execution_record_id = _resolve_source_execution_record_id(review_request, source_task_intent)
        if source_execution_record_id is not None:
            source_execution_record = self.execution_record_repository.get(source_execution_record_id)

        operation_plans = (
            self.operation_plan_repository.list_by_task(linked_farming_task.id)
            if linked_farming_task is not None
            else []
        )
        event_records = [
            item
            for item in self.event_record_repository.list_by_plan(review_request.planting_plan_id)
            if _event_references_review_request(item, review_request.id)
        ]
        return ReviewRequestDetail(
            review_request=review_request,
            source_task_intent=source_task_intent,
            linked_farming_task=linked_farming_task,
            operation_plans=operation_plans,
            source_execution_record=source_execution_record,
            event_records=event_records,
        )


def _resolve_source_execution_record_id(
    review_request: ReviewRequest,
    source_task_intent: TaskIntent | None,
) -> int | None:
    if source_task_intent is not None and source_task_intent.source_execution_record_id is not None:
        return source_task_intent.source_execution_record_id
    context_refs = (review_request.decision_payload or {}).get("contextRefs")
    if isinstance(context_refs, dict):
        source_execution_record_id = context_refs.get("sourceExecutionRecordId")
        if isinstance(source_execution_record_id, int):
            return source_execution_record_id
    return None


def _event_references_review_request(event_record: EventRecord, review_request_id: int) -> bool:
    if event_record.source_record_id == str(review_request_id):
        return True

    payload = dict(event_record.payload or {})
    if payload.get("reviewRequestId") == review_request_id:
        return True
    if payload.get("entityType") in {"review_request", "cf_review_request"} and payload.get("entityId") == review_request_id:
        return True
    return False
