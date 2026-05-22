from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_survey_result_service, get_task_execution_service
from app.db.session import get_db
from app.services import (
    SurveyResultProcessingResult,
    SurveyResultService,
    TaskExecutionCompleteInput,
    TaskExecutionCompleteResult,
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


def _serialize_survey_result_response(result: SurveyResultProcessingResult) -> SurveyResultCreateResponse:
    return SurveyResultCreateResponse(
        execution_record_id=result.execution_record.id,
        event_record_id=result.event_record.id,
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
