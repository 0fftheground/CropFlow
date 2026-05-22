from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.core.constants import (
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_EXECUTION_COMPLETED,
    EXECUTION_MODE_MANUAL,
    EXECUTION_RECORD_TYPE_OPERATION_RESULT,
    EXECUTION_STATUS_COMPLETED,
)
from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord
from app.repositories import (
    EventRecordRepository,
    ExecutionRecordRepository,
    ExecutionRepository,
    FarmingTaskRepository,
)


class TaskExecutionEventDispatcher:
    def handle(self, event_record: EventRecord):
        raise NotImplementedError


@dataclass(slots=True)
class TaskExecutionCompleteInput:
    result_payload: dict[str, Any]
    operation_date: date
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    actual_area: Decimal | None = None
    actual_amount: Decimal | None = None
    amount_unit: str | None = None


@dataclass(slots=True)
class TaskExecutionCompleteResult:
    execution: Execution
    execution_record: ExecutionRecord
    event_record: EventRecord
    calendar_items: list[CalendarItem]


class TaskExecutionService:
    def __init__(
        self,
        farming_task_repository: FarmingTaskRepository,
        execution_repository: ExecutionRepository,
        execution_record_repository: ExecutionRecordRepository,
        event_record_repository: EventRecordRepository,
        plan_orchestrator: TaskExecutionEventDispatcher,
    ) -> None:
        self.farming_task_repository = farming_task_repository
        self.execution_repository = execution_repository
        self.execution_record_repository = execution_record_repository
        self.event_record_repository = event_record_repository
        self.plan_orchestrator = plan_orchestrator

    def complete_task(
        self,
        farming_task_id: int,
        payload: TaskExecutionCompleteInput,
    ) -> TaskExecutionCompleteResult:
        farming_task = self.farming_task_repository.get(farming_task_id)
        if farming_task is None:
            raise LookupError(f"Farming task {farming_task_id} does not exist.")

        execution = self._get_or_create_execution(farming_task)
        execution.status = EXECUTION_STATUS_COMPLETED
        execution.completed_at = payload.actual_end_at or _utcnow()

        execution_record = ExecutionRecord(
            planting_plan_id=farming_task.planting_plan_id,
            execution_id=execution.id,
            record_type=EXECUTION_RECORD_TYPE_OPERATION_RESULT,
            record_time=payload.actual_end_at or _utcnow(),
            actual_start_at=payload.actual_start_at,
            actual_end_at=payload.actual_end_at or _utcnow(),
            actual_area=payload.actual_area,
            actual_amount=payload.actual_amount,
            amount_unit=payload.amount_unit,
            result_payload=payload.result_payload,
            attachments=[],
            created_by_type="user",
            created_by_id="api",
        )
        self.execution_record_repository.add(execution_record)
        self.execution_record_repository.flush()

        event_record = self._record_execution_completed_event(
            planting_plan_id=farming_task.planting_plan_id,
            task_id=farming_task.id,
            task_subtype=farming_task.task_subtype,
            execution_id=execution.id,
            execution_record_id=execution_record.id,
            operation_date=payload.operation_date,
            result_payload=payload.result_payload,
        )
        orchestrator_result = self.plan_orchestrator.handle(event_record)
        return TaskExecutionCompleteResult(
            execution=execution,
            execution_record=execution_record,
            event_record=event_record,
            calendar_items=orchestrator_result.calendar_items,
        )

    def _get_or_create_execution(self, farming_task) -> Execution:
        executions = self.execution_repository.list_by_task(farming_task.id)
        if executions:
            return executions[0]

        execution = Execution(
            planting_plan_id=farming_task.planting_plan_id,
            farming_task_id=farming_task.id,
            operation_plan_id=None,
            execution_mode=farming_task.execution_mode or EXECUTION_MODE_MANUAL,
            status=EXECUTION_STATUS_COMPLETED,
            completed_at=_utcnow(),
            created_by_type="user",
            created_by_id="api",
        )
        self.execution_repository.add(execution)
        self.execution_repository.flush()
        return execution

    def _record_execution_completed_event(
        self,
        *,
        planting_plan_id: int,
        task_id: int,
        task_subtype: str,
        execution_id: int,
        execution_record_id: int,
        operation_date: date,
        result_payload: dict[str, Any],
    ) -> EventRecord:
        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_EXECUTION_COMPLETED,
            event_category="execution",
            event_source="api",
            source_system="cropflow",
            source_record_id=str(execution_record_id),
            payload={
                "taskId": task_id,
                "taskSubtype": task_subtype,
                "executionId": execution_id,
                "executionRecordId": execution_record_id,
                "operationDate": operation_date.isoformat(),
                "resultPayload": result_payload,
            },
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=f"execution-completed:{execution_record_id}",
            created_by_type="user",
            created_by_id="api",
        )
        self.event_record_repository.add(event_record)
        self.event_record_repository.flush()
        return event_record


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
