from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_farming_task_query_service, get_survey_result_service, get_task_execution_service
from app.db.session import get_db
from app.models import CalendarItem, EventRecord, Execution, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.services import (
    FarmingTaskDetail,
    FarmingTaskQueryService,
    SurveyResultProcessingResult,
    SurveyResultService,
    TaskExecutionCompleteInput,
    TaskExecutionCompleteResult,
    TaskExecutionRecordUpdateInput,
    TaskExecutionRecordUpdateResult,
    TaskExecutionService,
)

router = APIRouter(prefix="/tasks")


class SurveyResultCreateRequest(BaseModel):
    result_payload: dict[str, Any] = Field(default_factory=dict)
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None


class SurveyResultCreateResponse(BaseModel):
    execution_record_id: int
    event_record_id: int
    farming_task_ids: list[int]
    task_intent_ids: list[int]
    review_request_ids: list[int]


class TaskExecutionCompleteRequest(BaseModel):
    result_payload: dict[str, Any] = Field(default_factory=dict)
    operation_date: datetime
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    actual_area: Decimal | None = None
    actual_amount: Decimal | None = None
    amount_unit: str | None = None


class TaskExecutionCompleteResponse(BaseModel):
    execution_id: int
    execution_record_id: int
    event_record_id: int
    calendar_item_ids: list[int]


class TaskExecutionRecordUpdateRequest(BaseModel):
    result_payload: dict[str, Any] | None = None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None
    actual_area: Decimal | None = None
    actual_amount: Decimal | None = None
    amount_unit: str | None = None


class TaskExecutionRecordUpdateResponse(BaseModel):
    execution_id: int
    execution_record_id: int
    event_record_id: int
    updated_fields: list[str]


class FarmingTaskResponse(BaseModel):
    id: int
    planting_plan_id: int
    calendar_item_id: int | None
    task_intent_id: int | None
    review_request_id: int | None
    task_category: str
    task_subtype: str
    title: str
    description: str | None
    target_stage_code: str | None
    planned_start_at: datetime | None
    planned_end_at: datetime | None
    priority: str
    status: str
    execution_mode: str
    generation_reason: str | None
    parent_task_id: int | None
    source_execution_id: int | None
    source_execution_record_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class TaskDetailReviewRequestResponse(BaseModel):
    id: int
    review_type: str
    status: str
    decision: str | None
    title: str
    description: str | None
    decision_payload: dict[str, Any]
    resolved_by: str | None
    resolved_at: datetime | None


class TaskDetailTaskIntentResponse(BaseModel):
    id: int
    task_subtype: str
    status: str
    trigger_type: str
    trigger_summary: str | None
    suggested_action: str | None
    rule_result: dict[str, Any]
    source_execution_record_id: int | None
    converted_task_id: int | None


class TaskDetailCalendarItemResponse(BaseModel):
    id: int
    task_subtype: str
    title: str
    suggested_start_date: datetime | date
    suggested_end_date: datetime | date
    status: str
    generation_condition: dict[str, Any]
    generated_task_id: int | None


class OperationPlanResponse(BaseModel):
    id: int
    farming_task_id: int
    plan_type: str
    status: str
    version: int
    algorithm_code: str | None
    algorithm_version: str | None
    operation_area: dict[str, Any]
    operation_window_start: datetime | None
    operation_window_end: datetime | None
    execution_mode: str
    parameters: dict[str, Any]
    prescription_map: dict[str, Any]
    acceptance_criteria: dict[str, Any]
    basis: str | None
    source_event_id: int | None
    created_at: datetime | None
    updated_at: datetime | None


class ExecutionResponse(BaseModel):
    id: int
    planting_plan_id: int
    farming_task_id: int
    operation_plan_id: int | None
    execution_mode: str
    status: str
    assigned_to_type: str | None
    assigned_to_id: str | None
    external_system_code: str | None
    external_execution_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None
    created_at: datetime | None
    updated_at: datetime | None


class ExecutionRecordResponse(BaseModel):
    id: int
    planting_plan_id: int
    execution_id: int
    record_type: str
    record_time: datetime
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    actual_area: Decimal | None
    actual_amount: Decimal | None
    amount_unit: str | None
    result_payload: dict[str, Any]
    attachments: list[Any]
    created_at: datetime | None
    updated_at: datetime | None


class EventRecordResponse(BaseModel):
    id: int
    event_type: str
    event_category: str
    event_source: str
    source_record_id: str | None
    payload: dict[str, Any]
    occurred_at: datetime
    processing_status: str
    error_message: str | None


class FarmingTaskDetailResponse(BaseModel):
    task: FarmingTaskResponse
    operation_plans: list[OperationPlanResponse]
    executions: list[ExecutionResponse]
    execution_records: list[ExecutionRecordResponse]
    review_request: TaskDetailReviewRequestResponse | None
    source_task_intent: TaskDetailTaskIntentResponse | None
    source_calendar_item: TaskDetailCalendarItemResponse | None
    source_execution_record: ExecutionRecordResponse | None
    downstream_calendar_items: list[TaskDetailCalendarItemResponse]
    event_records: list[EventRecordResponse]


@router.get("/{task_id}", response_model=FarmingTaskDetailResponse)
def get_task_detail(
    task_id: int,
    service: FarmingTaskQueryService = Depends(get_farming_task_query_service),
) -> FarmingTaskDetailResponse:
    try:
        result = service.get_detail(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_task_detail(result)


@router.post("/{task_id}/survey-results", response_model=SurveyResultCreateResponse, status_code=status.HTTP_201_CREATED)
def create_survey_result(
    task_id: int,
    payload: SurveyResultCreateRequest,
    service: SurveyResultService = Depends(get_survey_result_service),
    db: Session = Depends(get_db),
) -> SurveyResultCreateResponse:
    try:
        result = service.record_survey_result(
            task_id,
            payload.result_payload,
            actual_start_at=payload.actual_start_at,
            actual_end_at=payload.actual_end_at,
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    return _serialize_survey_result_response(result)


@router.post("/{task_id}/execution-completions", response_model=TaskExecutionCompleteResponse, status_code=status.HTTP_201_CREATED)
def complete_task_execution(
    task_id: int,
    payload: TaskExecutionCompleteRequest,
    service: TaskExecutionService = Depends(get_task_execution_service),
    db: Session = Depends(get_db),
) -> TaskExecutionCompleteResponse:
    try:
        result = service.complete_task(
            task_id,
            TaskExecutionCompleteInput(
                result_payload=payload.result_payload,
                operation_date=payload.operation_date.date(),
                actual_start_at=payload.actual_start_at,
                actual_end_at=payload.actual_end_at,
                actual_area=payload.actual_area,
                actual_amount=payload.actual_amount,
                amount_unit=payload.amount_unit,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    return _serialize_task_execution_response(result)


@router.patch("/{task_id}/execution-records/latest", response_model=TaskExecutionRecordUpdateResponse)
def update_latest_execution_record(
    task_id: int,
    payload: TaskExecutionRecordUpdateRequest,
    service: TaskExecutionService = Depends(get_task_execution_service),
    db: Session = Depends(get_db),
) -> TaskExecutionRecordUpdateResponse:
    try:
        result = service.update_latest_execution_record(
            task_id,
            TaskExecutionRecordUpdateInput(
                result_payload=payload.result_payload,
                actual_start_at=payload.actual_start_at,
                actual_end_at=payload.actual_end_at,
                actual_area=payload.actual_area,
                actual_amount=payload.actual_amount,
                amount_unit=payload.amount_unit,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    return _serialize_task_execution_record_update_response(result)


def _serialize_survey_result_response(result: SurveyResultProcessingResult) -> SurveyResultCreateResponse:
    return SurveyResultCreateResponse(
        execution_record_id=result.execution_record.id,
        event_record_id=result.event_record.id,
        farming_task_ids=[item.id for item in result.farming_tasks],
        task_intent_ids=[item.id for item in result.task_intents],
        review_request_ids=[item.id for item in result.review_requests],
    )


def _serialize_task_execution_response(result: TaskExecutionCompleteResult) -> TaskExecutionCompleteResponse:
    return TaskExecutionCompleteResponse(
        execution_id=result.execution.id,
        execution_record_id=result.execution_record.id,
        event_record_id=result.event_record.id,
        calendar_item_ids=[item.id for item in result.calendar_items],
    )


def _serialize_task_execution_record_update_response(
    result: TaskExecutionRecordUpdateResult,
) -> TaskExecutionRecordUpdateResponse:
    return TaskExecutionRecordUpdateResponse(
        execution_id=result.execution.id,
        execution_record_id=result.execution_record.id,
        event_record_id=result.event_record.id,
        updated_fields=result.updated_fields,
    )


def _serialize_task_detail(detail: FarmingTaskDetail) -> FarmingTaskDetailResponse:
    return FarmingTaskDetailResponse(
        task=_serialize_farming_task(detail.farming_task),
        operation_plans=[_serialize_operation_plan(item) for item in detail.operation_plans],
        executions=[_serialize_execution(item) for item in detail.executions],
        execution_records=[_serialize_execution_record(item) for item in detail.execution_records],
        review_request=_serialize_review_request(detail.review_request) if detail.review_request is not None else None,
        source_task_intent=(
            _serialize_task_intent(detail.source_task_intent)
            if detail.source_task_intent is not None
            else None
        ),
        source_calendar_item=(
            _serialize_calendar_item(detail.source_calendar_item)
            if detail.source_calendar_item is not None
            else None
        ),
        source_execution_record=(
            _serialize_execution_record(detail.source_execution_record)
            if detail.source_execution_record is not None
            else None
        ),
        downstream_calendar_items=[_serialize_calendar_item(item) for item in detail.downstream_calendar_items],
        event_records=[_serialize_event_record(item) for item in detail.event_records],
    )


def _serialize_farming_task(task: FarmingTask) -> FarmingTaskResponse:
    return FarmingTaskResponse(
        id=task.id,
        planting_plan_id=task.planting_plan_id,
        calendar_item_id=task.calendar_item_id,
        task_intent_id=task.task_intent_id,
        review_request_id=task.review_request_id,
        task_category=task.task_category,
        task_subtype=task.task_subtype,
        title=task.title,
        description=task.description,
        target_stage_code=task.target_stage_code,
        planned_start_at=task.planned_start_at,
        planned_end_at=task.planned_end_at,
        priority=task.priority or "normal",
        status=task.status or "pending",
        execution_mode=task.execution_mode or "manual",
        generation_reason=task.generation_reason,
        parent_task_id=task.parent_task_id,
        source_execution_id=task.source_execution_id,
        source_execution_record_id=task.source_execution_record_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _serialize_review_request(review_request: ReviewRequest) -> TaskDetailReviewRequestResponse:
    return TaskDetailReviewRequestResponse(
        id=review_request.id,
        review_type=review_request.review_type,
        status=review_request.status,
        decision=review_request.decision,
        title=review_request.title,
        description=review_request.description,
        decision_payload=review_request.decision_payload or {},
        resolved_by=review_request.resolved_by,
        resolved_at=review_request.resolved_at,
    )


def _serialize_task_intent(task_intent: TaskIntent) -> TaskDetailTaskIntentResponse:
    return TaskDetailTaskIntentResponse(
        id=task_intent.id,
        task_subtype=task_intent.task_subtype,
        status=task_intent.status,
        trigger_type=task_intent.trigger_type,
        trigger_summary=task_intent.trigger_summary,
        suggested_action=task_intent.suggested_action,
        rule_result=task_intent.rule_result or {},
        source_execution_record_id=task_intent.source_execution_record_id,
        converted_task_id=task_intent.converted_task_id,
    )


def _serialize_calendar_item(calendar_item: CalendarItem) -> TaskDetailCalendarItemResponse:
    return TaskDetailCalendarItemResponse(
        id=calendar_item.id,
        task_subtype=calendar_item.task_subtype,
        title=calendar_item.title,
        suggested_start_date=calendar_item.suggested_start_date,
        suggested_end_date=calendar_item.suggested_end_date,
        status=calendar_item.status,
        generation_condition=calendar_item.generation_condition or {},
        generated_task_id=calendar_item.generated_task_id,
    )


def _serialize_operation_plan(operation_plan: OperationPlan) -> OperationPlanResponse:
    return OperationPlanResponse(
        id=operation_plan.id,
        farming_task_id=operation_plan.farming_task_id,
        plan_type=operation_plan.plan_type,
        status=operation_plan.status,
        version=operation_plan.version,
        algorithm_code=operation_plan.algorithm_code,
        algorithm_version=operation_plan.algorithm_version,
        operation_area=operation_plan.operation_area or {},
        operation_window_start=operation_plan.operation_window_start,
        operation_window_end=operation_plan.operation_window_end,
        execution_mode=operation_plan.execution_mode,
        parameters=operation_plan.parameters or {},
        prescription_map=operation_plan.prescription_map or {},
        acceptance_criteria=operation_plan.acceptance_criteria or {},
        basis=operation_plan.basis,
        source_event_id=operation_plan.source_event_id,
        created_at=operation_plan.created_at,
        updated_at=operation_plan.updated_at,
    )


def _serialize_execution(execution: Execution) -> ExecutionResponse:
    return ExecutionResponse(
        id=execution.id,
        planting_plan_id=execution.planting_plan_id,
        farming_task_id=execution.farming_task_id,
        operation_plan_id=execution.operation_plan_id,
        execution_mode=execution.execution_mode or "manual",
        status=execution.status or "pending",
        assigned_to_type=execution.assigned_to_type,
        assigned_to_id=execution.assigned_to_id,
        external_system_code=execution.external_system_code,
        external_execution_id=execution.external_execution_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        failure_reason=execution.failure_reason,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
    )


def _serialize_execution_record(execution_record: ExecutionRecord) -> ExecutionRecordResponse:
    return ExecutionRecordResponse(
        id=execution_record.id,
        planting_plan_id=execution_record.planting_plan_id,
        execution_id=execution_record.execution_id,
        record_type=execution_record.record_type,
        record_time=execution_record.record_time,
        actual_start_at=execution_record.actual_start_at,
        actual_end_at=execution_record.actual_end_at,
        actual_area=execution_record.actual_area,
        actual_amount=execution_record.actual_amount,
        amount_unit=execution_record.amount_unit,
        result_payload=execution_record.result_payload or {},
        attachments=execution_record.attachments or [],
        created_at=execution_record.created_at,
        updated_at=execution_record.updated_at,
    )


def _serialize_event_record(event_record: EventRecord) -> EventRecordResponse:
    return EventRecordResponse(
        id=event_record.id,
        event_type=event_record.event_type,
        event_category=event_record.event_category,
        event_source=event_record.event_source,
        source_record_id=event_record.source_record_id,
        payload=event_record.payload or {},
        occurred_at=event_record.occurred_at,
        processing_status=event_record.processing_status,
        error_message=event_record.error_message,
    )
