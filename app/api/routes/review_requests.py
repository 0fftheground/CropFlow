from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_review_request_service
from app.db.session import get_db
from app.services import ReviewRequestResolveInput, ReviewRequestResolveResult, ReviewRequestService

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


@router.post("/{review_request_id}/resolve", response_model=ReviewRequestResolveResponse)
def resolve_review_request(
    review_request_id: int,
    payload: ReviewRequestResolveRequest,
    service: ReviewRequestService = Depends(get_review_request_service),
    db: Session = Depends(get_db),
) -> ReviewRequestResolveResponse:
    try:
        result = service.resolve(
            review_request_id,
            ReviewRequestResolveInput(
                decision=payload.decision,
                decision_payload=payload.decision_payload,
                decision_note=payload.decision_note,
                resolved_by=payload.resolved_by,
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
