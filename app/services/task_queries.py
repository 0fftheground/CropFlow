from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.repositories import (
    CalendarItemRepository,
    EventRecordRepository,
    ExecutionRecordRepository,
    ExecutionRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
    ReviewRequestRepository,
    TaskIntentRepository,
)


@dataclass(slots=True)
class FarmingTaskDetail:
    farming_task: FarmingTask
    operation_plans: list[OperationPlan]
    executions: list[Execution]
    execution_records: list[ExecutionRecord]
    review_request: ReviewRequest | None
    source_task_intent: TaskIntent | None
    source_calendar_item: CalendarItem | None
    source_execution_record: ExecutionRecord | None
    downstream_calendar_items: list[CalendarItem]
    event_records: list[EventRecord]


class FarmingTaskQueryService:
    def __init__(
        self,
        farming_task_repository: FarmingTaskRepository,
        operation_plan_repository: OperationPlanRepository,
        execution_repository: ExecutionRepository,
        execution_record_repository: ExecutionRecordRepository,
        review_request_repository: ReviewRequestRepository,
        task_intent_repository: TaskIntentRepository,
        calendar_item_repository: CalendarItemRepository,
        event_record_repository: EventRecordRepository,
    ) -> None:
        self.farming_task_repository = farming_task_repository
        self.operation_plan_repository = operation_plan_repository
        self.execution_repository = execution_repository
        self.execution_record_repository = execution_record_repository
        self.review_request_repository = review_request_repository
        self.task_intent_repository = task_intent_repository
        self.calendar_item_repository = calendar_item_repository
        self.event_record_repository = event_record_repository

    def get_detail(self, farming_task_id: int) -> FarmingTaskDetail:
        farming_task = self.farming_task_repository.get(farming_task_id)
        if farming_task is None:
            raise LookupError(f"Farming task {farming_task_id} does not exist.")

        review_request = (
            self.review_request_repository.get(farming_task.review_request_id)
            if farming_task.review_request_id is not None
            else None
        )
        source_task_intent = (
            self.task_intent_repository.get(farming_task.task_intent_id)
            if farming_task.task_intent_id is not None
            else None
        )
        if source_task_intent is None and review_request is not None and review_request.source_entity_type in {"task_intent", "cf_task_intent"}:
            source_entity = self.review_request_repository.get_source_entity(review_request)
            if isinstance(source_entity, TaskIntent):
                source_task_intent = source_entity

        event_records = [
            item
            for item in self.event_record_repository.list_by_plan(farming_task.planting_plan_id)
            if _event_references_task(item, farming_task.id, farming_task.review_request_id)
        ]
        return FarmingTaskDetail(
            farming_task=farming_task,
            operation_plans=self.operation_plan_repository.list_by_task(farming_task.id),
            executions=self.execution_repository.list_by_task(farming_task.id),
            execution_records=self.execution_record_repository.list_by_task(farming_task.id),
            review_request=review_request,
            source_task_intent=source_task_intent,
            source_calendar_item=(
                self.calendar_item_repository.get(farming_task.calendar_item_id)
                if farming_task.calendar_item_id is not None
                else None
            ),
            source_execution_record=(
                self.execution_record_repository.get(farming_task.source_execution_record_id)
                if farming_task.source_execution_record_id is not None
                else None
            ),
            downstream_calendar_items=self.calendar_item_repository.list_by_parent_task(farming_task.id),
            event_records=event_records,
        )


def _event_references_task(
    event_record: EventRecord,
    farming_task_id: int,
    review_request_id: int | None,
) -> bool:
    if event_record.source_record_id == str(farming_task_id):
        return True

    payload = dict(event_record.payload or {})
    if payload.get("taskId") == farming_task_id or payload.get("farmingTaskId") == farming_task_id:
        return True
    if payload.get("parentTaskId") == farming_task_id or payload.get("generatedTaskId") == farming_task_id:
        return True
    if payload.get("entityType") in {"farming_task", "cf_farming_task"} and payload.get("entityId") == farming_task_id:
        return True
    if review_request_id is not None and payload.get("reviewRequestId") == review_request_id:
        return True

    context_refs = payload.get("contextRefs")
    if isinstance(context_refs, dict) and context_refs.get("parentTaskId") == farming_task_id:
        return True

    return False
