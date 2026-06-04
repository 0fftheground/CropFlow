from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_review_request_query_service, get_review_request_service
from app.db.session import get_db
from app.models import EventRecord, ExecutionRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent, User
from app.services import (
    ReviewRequestDetail,
    ReviewRequestQueryService,
    ReviewRequestResolveInput,
    ReviewRequestResolveResult,
    ReviewRequestService,
)

router = APIRouter(prefix="/review-requests")


class ReviewRequestResolveRequest(BaseModel):
    decision: str
    decision_payload: dict[str, Any] = Field(default_factory=dict)
    decision_note: str | None = None
    resolved_by: str | None = None


class ReviewRequestResolveResponse(BaseModel):
    review_request_id: int
    event_record_id: int
    decision: str | None
    status: str
    task_intent_ids: list[int]
    farming_task_ids: list[int]
    operation_plan_ids: list[int]
    resolved_at: datetime | None


class ReviewRequestTaskIntentResponse(BaseModel):
    id: int
    task_subtype: str
    status: str
    trigger_type: str
    trigger_summary: str | None
    suggested_action: str | None
    rule_result: dict[str, Any]
    converted_task_id: int | None
    source_execution_record_id: int | None


class ReviewRequestFarmingTaskResponse(BaseModel):
    id: int
    task_subtype: str
    title: str
    status: str
    execution_mode: str
    planned_start_at: datetime | None
    planned_end_at: datetime | None


class ReviewRequestOperationPlanResponse(BaseModel):
    id: int
    farming_task_id: int
    plan_type: str
    status: str
    version: int
    algorithm_code: str | None
    execution_mode: str
    operation_window_start: datetime | None
    operation_window_end: datetime | None
    parameters: dict[str, Any]
    basis: str | None


class ReviewRequestExecutionRecordResponse(BaseModel):
    id: int
    execution_id: int
    record_type: str
    record_time: datetime
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    result_payload: dict[str, Any]
    attachments: list[Any]


class ReviewRequestEventRecordResponse(BaseModel):
    id: int
    event_type: str
    event_category: str
    event_source: str
    source_record_id: str | None
    payload: dict[str, Any]
    occurred_at: datetime
    processing_status: str
    error_message: str | None


class ReviewRequestDetailResponse(BaseModel):
    review_request_id: int
    planting_plan_id: int
    review_type: str
    status: str
    decision: str | None
    title: str
    description: str | None
    decision_payload: dict[str, Any]
    resolved_by: str | None
    resolved_at: datetime | None
    source_task_intent: ReviewRequestTaskIntentResponse | None
    linked_farming_task: ReviewRequestFarmingTaskResponse | None
    operation_plans: list[ReviewRequestOperationPlanResponse]
    source_execution_record: ReviewRequestExecutionRecordResponse | None
    event_records: list[ReviewRequestEventRecordResponse]


@router.get("/{review_request_id}", response_model=ReviewRequestDetailResponse)
def get_review_request_detail(
    review_request_id: int,
    service: ReviewRequestQueryService = Depends(get_review_request_query_service),
) -> ReviewRequestDetailResponse:
    try:
        result = service.get_detail(review_request_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_review_request_detail(result)


@router.post("/{review_request_id}/resolve", response_model=ReviewRequestResolveResponse)
def resolve_review_request(
    review_request_id: int,
    payload: ReviewRequestResolveRequest,
    service: ReviewRequestService = Depends(get_review_request_service),
    db: Session = Depends(get_db),
) -> ReviewRequestResolveResponse:
    try:
        resolved_by_user_id = _resolve_resolved_by_user_id(db, payload.resolved_by)
        result = service.resolve(
            review_request_id,
            ReviewRequestResolveInput(
                decision=payload.decision,
                decision_payload=payload.decision_payload,
                decision_note=payload.decision_note,
                resolved_by=resolved_by_user_id,
            ),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    return _serialize_resolve_response(result)


def _resolve_resolved_by_user_id(db: Session, resolved_by: str | None) -> str | None:
    if resolved_by is None:
        return None
    user = db.get(User, resolved_by)
    if user is not None:
        return user.id
    user = db.execute(
        select(User).where(
            or_(
                User.username == resolved_by,
                User.display_name == resolved_by,
            ),
        ),
    ).scalar_one_or_none()
    if user is not None:
        return user.id
    raise ValueError(f"Resolved user {resolved_by} does not exist.")


def _serialize_resolve_response(result: ReviewRequestResolveResult) -> ReviewRequestResolveResponse:
    return ReviewRequestResolveResponse(
        review_request_id=result.review_request.id,
        event_record_id=result.event_record.id,
        decision=result.review_request.decision,
        status=result.review_request.status,
        task_intent_ids=[item.id for item in result.task_intents],
        farming_task_ids=[item.id for item in result.farming_tasks],
        operation_plan_ids=[item.id for item in result.operation_plans],
        resolved_at=result.review_request.resolved_at,
    )


def _serialize_review_request_detail(result: ReviewRequestDetail) -> ReviewRequestDetailResponse:
    review_request = result.review_request
    return ReviewRequestDetailResponse(
        review_request_id=review_request.id,
        planting_plan_id=review_request.planting_plan_id,
        review_type=review_request.review_type,
        status=review_request.status,
        decision=review_request.decision,
        title=review_request.title,
        description=review_request.description,
        decision_payload=review_request.decision_payload or {},
        resolved_by=review_request.resolved_by,
        resolved_at=review_request.resolved_at,
        source_task_intent=(
            _serialize_task_intent(result.source_task_intent)
            if result.source_task_intent is not None
            else None
        ),
        linked_farming_task=(
            _serialize_farming_task(result.linked_farming_task)
            if result.linked_farming_task is not None
            else None
        ),
        operation_plans=[_serialize_operation_plan(item) for item in result.operation_plans],
        source_execution_record=(
            _serialize_execution_record(result.source_execution_record)
            if result.source_execution_record is not None
            else None
        ),
        event_records=[_serialize_event_record(item) for item in result.event_records],
    )


def _serialize_task_intent(task_intent: TaskIntent) -> ReviewRequestTaskIntentResponse:
    return ReviewRequestTaskIntentResponse(
        id=task_intent.id,
        task_subtype=task_intent.task_subtype,
        status=task_intent.status,
        trigger_type=task_intent.trigger_type,
        trigger_summary=task_intent.trigger_summary,
        suggested_action=task_intent.suggested_action,
        rule_result=task_intent.rule_result or {},
        converted_task_id=task_intent.converted_task_id,
        source_execution_record_id=task_intent.source_execution_record_id,
    )


def _serialize_farming_task(farming_task: FarmingTask) -> ReviewRequestFarmingTaskResponse:
    return ReviewRequestFarmingTaskResponse(
        id=farming_task.id,
        task_subtype=farming_task.task_subtype,
        title=farming_task.title,
        status=farming_task.status,
        execution_mode=farming_task.execution_mode,
        planned_start_at=farming_task.planned_start_at,
        planned_end_at=farming_task.planned_end_at,
    )


def _serialize_operation_plan(operation_plan: OperationPlan) -> ReviewRequestOperationPlanResponse:
    return ReviewRequestOperationPlanResponse(
        id=operation_plan.id,
        farming_task_id=operation_plan.farming_task_id,
        plan_type=operation_plan.plan_type,
        status=operation_plan.status,
        version=operation_plan.version,
        algorithm_code=operation_plan.algorithm_code,
        execution_mode=operation_plan.execution_mode,
        operation_window_start=operation_plan.operation_window_start,
        operation_window_end=operation_plan.operation_window_end,
        parameters=operation_plan.parameters or {},
        basis=operation_plan.basis,
    )


def _serialize_execution_record(execution_record: ExecutionRecord) -> ReviewRequestExecutionRecordResponse:
    return ReviewRequestExecutionRecordResponse(
        id=execution_record.id,
        execution_id=execution_record.execution_id,
        record_type=execution_record.record_type,
        record_time=execution_record.record_time,
        actual_start_at=execution_record.actual_start_at,
        actual_end_at=execution_record.actual_end_at,
        result_payload=execution_record.result_payload or {},
        attachments=execution_record.attachments or [],
    )


def _serialize_event_record(event_record: EventRecord) -> ReviewRequestEventRecordResponse:
    return ReviewRequestEventRecordResponse(
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
