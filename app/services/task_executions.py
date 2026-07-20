from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.core.constants import (
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_EXECUTION_COMPLETED,
    EVENT_TYPE_EXECUTION_RECORD_UPDATED,
    EXECUTION_MODE_MANUAL,
    EXECUTION_RECORD_TYPE_OPERATION_RESULT,
    EXECUTION_STATUS_COMPLETED,
    FARMING_TASK_STATUS_COMPLETED,
)
from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord
from app.repositories import (
    EventRecordRepository,
    ExecutionRecordRepository,
    ExecutionRepository,
    FarmingTaskRepository,
    OperationPlanRepository,
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


@dataclass(slots=True)
class TaskExecutionRecordUpdateInput:
    operation_date: date | None = None
    result_payload: dict[str, Any] | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    actual_area: Decimal | None = None
    actual_amount: Decimal | None = None
    amount_unit: str | None = None


@dataclass(slots=True)
class TaskExecutionRecordUpdateResult:
    execution: Execution
    execution_record: ExecutionRecord
    event_record: EventRecord
    operation_date: date | None
    updated_fields: list[str]


class TaskExecutionService:
    def __init__(
        self,
        farming_task_repository: FarmingTaskRepository,
        operation_plan_repository: OperationPlanRepository | None,
        execution_repository: ExecutionRepository,
        execution_record_repository: ExecutionRecordRepository,
        event_record_repository: EventRecordRepository,
        plan_orchestrator: TaskExecutionEventDispatcher,
    ) -> None:
        self.farming_task_repository = farming_task_repository
        self.operation_plan_repository = operation_plan_repository
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
        self._ensure_task_accepts_execution_records(farming_task)

        execution = self._get_or_create_execution(farming_task)
        farming_task.status = FARMING_TASK_STATUS_COMPLETED
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

    def update_latest_execution_record(
        self,
        farming_task_id: int,
        payload: TaskExecutionRecordUpdateInput,
    ) -> TaskExecutionRecordUpdateResult:
        farming_task = self.farming_task_repository.get(farming_task_id)
        if farming_task is None:
            raise LookupError(f"Farming task {farming_task_id} does not exist.")
        self._ensure_task_accepts_execution_records(farming_task)

        latest_records = self.execution_record_repository.list_by_task(farming_task_id)
        if not latest_records:
            raise ValueError(f"Farming task {farming_task_id} does not have any execution records.")

        latest_record = latest_records[0]
        execution = self.execution_repository.get(latest_record.execution_id)
        if execution is None:
            raise LookupError(f"Execution {latest_record.execution_id} does not exist.")
        completed_event = self._get_execution_completed_event(
            planting_plan_id=farming_task.planting_plan_id,
            execution_record_id=int(latest_record.id),
        )
        current_operation_date = _parse_optional_payload_date(
            completed_event.payload if completed_event is not None else {},
            "operationDate",
        )

        proposed_values = {
            "operation_date": payload.operation_date,
            "result_payload": payload.result_payload,
            "actual_start_at": payload.actual_start_at,
            "actual_end_at": payload.actual_end_at,
            "actual_area": payload.actual_area,
            "actual_amount": payload.actual_amount,
            "amount_unit": payload.amount_unit,
        }
        provided_fields = [field_name for field_name, value in proposed_values.items() if value is not None]
        if not provided_fields:
            raise ValueError("At least one execution record field must be provided for update.")

        before_snapshot = self._build_execution_record_snapshot(
            latest_record,
            operation_date=current_operation_date,
        )
        for field_name in provided_fields:
            if field_name == "operation_date":
                continue
            setattr(latest_record, field_name, proposed_values[field_name])
        if payload.actual_end_at is not None:
            latest_record.record_time = payload.actual_end_at
            execution.completed_at = payload.actual_end_at
        if payload.operation_date is not None:
            if completed_event is None:
                raise ValueError(
                    f"Execution record {latest_record.id} does not have an ExecutionCompleted event to update operation date.",
                )
            completed_event.payload = {
                **dict(completed_event.payload or {}),
                "operationDate": payload.operation_date.isoformat(),
            }
            completed_event.updated_at = _utcnow()
        latest_record.updated_at = _utcnow()

        after_snapshot = self._build_execution_record_snapshot(
            latest_record,
            operation_date=payload.operation_date or current_operation_date,
        )
        updated_fields = [
            field_name
            for field_name in after_snapshot
            if before_snapshot[field_name] != after_snapshot[field_name]
        ]
        if not updated_fields:
            raise ValueError("No execution record changes detected.")

        event_record = self._record_execution_record_updated_event(
            planting_plan_id=farming_task.planting_plan_id,
            task_id=farming_task.id,
            execution_id=execution.id,
            execution_record_id=latest_record.id,
            updated_fields=updated_fields,
            before=before_snapshot,
            after=after_snapshot,
        )
        self.plan_orchestrator.handle(event_record)
        return TaskExecutionRecordUpdateResult(
            execution=execution,
            execution_record=latest_record,
            event_record=event_record,
            operation_date=payload.operation_date or current_operation_date,
            updated_fields=updated_fields,
        )

    def _ensure_task_accepts_execution_records(self, farming_task) -> None:
        if farming_task.status == "cancelled":
            raise ValueError(f"Farming task {farming_task.id} is cancelled and cannot accept execution records.")

    def _get_or_create_execution(self, farming_task) -> Execution:
        active_operation_plan = (
            self.operation_plan_repository.get_active_by_task(farming_task.id)
            if self.operation_plan_repository is not None
            else None
        )
        executions = self.execution_repository.list_by_task(farming_task.id)
        if executions:
            execution = executions[0]
            if execution.operation_plan_id is None and active_operation_plan is not None:
                execution.operation_plan_id = active_operation_plan.id
            return execution

        execution = Execution(
            planting_plan_id=farming_task.planting_plan_id,
            farming_task_id=farming_task.id,
            operation_plan_id=active_operation_plan.id if active_operation_plan is not None else None,
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

    def _record_execution_record_updated_event(
        self,
        *,
        planting_plan_id: int,
        task_id: int,
        execution_id: int,
        execution_record_id: int,
        updated_fields: list[str],
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> EventRecord:
        event_record = EventRecord(
            planting_plan_id=planting_plan_id,
            event_type=EVENT_TYPE_EXECUTION_RECORD_UPDATED,
            event_category="execution",
            event_source="api",
            source_system="cropflow",
            source_record_id=str(execution_record_id),
            payload={
                "taskId": task_id,
                "executionId": execution_id,
                "executionRecordId": execution_record_id,
                "updatedFields": updated_fields,
                "before": {field_name: before[field_name] for field_name in updated_fields},
                "after": {field_name: after[field_name] for field_name in updated_fields},
            },
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=f"execution-record-updated:{execution_record_id}:{_utcnow().isoformat()}",
            created_by_type="user",
            created_by_id="api",
        )
        self.event_record_repository.add(event_record)
        self.event_record_repository.flush()
        return event_record

    def _get_execution_completed_event(
        self,
        *,
        planting_plan_id: int,
        execution_record_id: int,
    ) -> EventRecord | None:
        if hasattr(self.event_record_repository, "list_by_source_record_id"):
            for item in self.event_record_repository.list_by_source_record_id(str(execution_record_id)):
                if item.event_type == EVENT_TYPE_EXECUTION_COMPLETED:
                    return item
        if hasattr(self.event_record_repository, "list_by_plan"):
            for item in self.event_record_repository.list_by_plan(planting_plan_id):
                payload = dict(item.payload or {})
                if item.event_type != EVENT_TYPE_EXECUTION_COMPLETED:
                    continue
                if payload.get("executionRecordId") == execution_record_id:
                    return item
        return None

    def _build_execution_record_snapshot(
        self,
        execution_record: ExecutionRecord,
        *,
        operation_date: date | None = None,
    ) -> dict[str, Any]:
        return {
            "operation_date": _serialize_execution_value(operation_date),
            "result_payload": dict(execution_record.result_payload or {}),
            "actual_start_at": _serialize_execution_value(execution_record.actual_start_at),
            "actual_end_at": _serialize_execution_value(execution_record.actual_end_at),
            "actual_area": _serialize_execution_value(execution_record.actual_area),
            "actual_amount": _serialize_execution_value(execution_record.actual_amount),
            "amount_unit": execution_record.amount_unit,
            "record_time": _serialize_execution_value(execution_record.record_time),
        }


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _serialize_execution_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _parse_optional_payload_date(payload: dict[str, Any], *keys: str) -> date | None:
    for key in keys:
        raw_value = payload.get(key)
        if raw_value is None:
            continue
        if isinstance(raw_value, datetime):
            return raw_value.date()
        if isinstance(raw_value, date):
            return raw_value
        if isinstance(raw_value, str):
            if "T" in raw_value:
                return datetime.fromisoformat(raw_value).date()
            return date.fromisoformat(raw_value)
    return None
