from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.constants import (
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_SURVEY_RESULT_RECORDED,
    EXECUTION_MODE_MANUAL,
    EXECUTION_RECORD_TYPE_SURVEY_RESULT,
    EXECUTION_STATUS_COMPLETED,
)
from app.models import EventRecord, Execution, ExecutionRecord, ReviewRequest, TaskIntent
from app.repositories import (
    EventRecordRepository,
    ExecutionRecordRepository,
    ExecutionRepository,
    FarmingTaskRepository,
)


class SurveyResultEventDispatcher:
    def handle(self, event_record: EventRecord):
        raise NotImplementedError


@dataclass(slots=True)
class SurveyResultRecorded:
    planting_plan_id: int
    task_id: int
    task_subtype: str
    execution_id: int
    execution_record_id: int
    result_payload: dict[str, Any]


@dataclass(slots=True)
class SurveyResultProcessingResult:
    execution_record: ExecutionRecord
    event_record: EventRecord
    task_intents: list[TaskIntent]
    review_requests: list[ReviewRequest]


class SurveyResultService:
    def __init__(
        self,
        farming_task_repository: FarmingTaskRepository,
        execution_repository: ExecutionRepository,
        execution_record_repository: ExecutionRecordRepository,
        event_record_repository: EventRecordRepository,
        plan_orchestrator: SurveyResultEventDispatcher,
    ) -> None:
        self.farming_task_repository = farming_task_repository
        self.execution_repository = execution_repository
        self.execution_record_repository = execution_record_repository
        self.event_record_repository = event_record_repository
        self.plan_orchestrator = plan_orchestrator

    def record_survey_result(
        self,
        farming_task_id: int,
        result_payload: dict[str, Any],
        *,
        actual_start_at: datetime | None = None,
        actual_end_at: datetime | None = None,
    ) -> SurveyResultProcessingResult:
        farming_task = self.farming_task_repository.get(farming_task_id)
        if farming_task is None:
            raise LookupError(f"Farming task {farming_task_id} does not exist.")

        execution = self._get_or_create_execution(farming_task)
        execution_record = ExecutionRecord(
            planting_plan_id=farming_task.planting_plan_id,
            execution_id=execution.id,
            record_type=EXECUTION_RECORD_TYPE_SURVEY_RESULT,
            record_time=actual_end_at or _utcnow(),
            actual_start_at=actual_start_at,
            actual_end_at=actual_end_at or _utcnow(),
            result_payload=result_payload,
            attachments=[],
            created_by_type="user",
            created_by_id="api",
        )
        self.execution_record_repository.add(execution_record)
        self.execution_record_repository.flush()

        event = SurveyResultRecorded(
            planting_plan_id=farming_task.planting_plan_id,
            task_id=farming_task.id,
            task_subtype=farming_task.task_subtype,
            execution_id=execution.id,
            execution_record_id=execution_record.id,
            result_payload=result_payload,
        )
        event_record = self._record_survey_event(event)
        orchestrator_result = self.plan_orchestrator.handle(event_record)
        return SurveyResultProcessingResult(
            execution_record=execution_record,
            event_record=event_record,
            task_intents=orchestrator_result.task_intents,
            review_requests=orchestrator_result.review_requests,
        )

    def _get_or_create_execution(self, farming_task) -> Execution:
        executions = self.execution_repository.list_by_task(farming_task.id)
        if executions:
            execution = executions[0]
            execution.status = EXECUTION_STATUS_COMPLETED
            execution.completed_at = _utcnow()
            return execution

        execution = Execution(
            planting_plan_id=farming_task.planting_plan_id,
            farming_task_id=farming_task.id,
            execution_mode=farming_task.execution_mode or EXECUTION_MODE_MANUAL,
            status=EXECUTION_STATUS_COMPLETED,
            completed_at=_utcnow(),
            created_by_type="user",
            created_by_id="api",
        )
        self.execution_repository.add(execution)
        self.execution_repository.flush()
        return execution

    def _record_survey_event(self, event: SurveyResultRecorded) -> EventRecord:
        event_record = EventRecord(
            planting_plan_id=event.planting_plan_id,
            event_type=EVENT_TYPE_SURVEY_RESULT_RECORDED,
            event_category="runtime",
            event_source="api",
            source_system="cropflow",
            source_record_id=str(event.execution_record_id),
            payload={
                "taskId": event.task_id,
                "taskSubtype": event.task_subtype,
                "executionId": event.execution_id,
                "executionRecordId": event.execution_record_id,
                "resultPayload": event.result_payload,
            },
            occurred_at=_utcnow(),
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=f"survey-result-recorded:{event.execution_record_id}",
            created_by_type="user",
            created_by_id="api",
        )
        self.event_record_repository.add(event_record)
        self.event_record_repository.flush()
        return event_record


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
