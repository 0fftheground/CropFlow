from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.constants import (
    EVENT_PROCESSING_STATUS_RECEIVED,
    EVENT_TYPE_REVIEW_REQUEST_RESOLVED,
    REVIEW_REQUEST_STATUS_OPEN,
    REVIEW_REQUEST_STATUS_RESOLVED,
)
from app.models import EventRecord, FarmingTask, OperationPlan, ReviewRequest, TaskIntent
from app.repositories import EventRecordRepository, ReviewRequestRepository

ALLOWED_REVIEW_DECISIONS = {"approve", "reject", "adjust", "no_action", "need_more_info"}


class ReviewRequestEventDispatcher:
    def handle(self, event_record: EventRecord):
        raise NotImplementedError


@dataclass(slots=True)
class ReviewRequestResolveInput:
    decision: str
    decision_payload: dict[str, Any]
    decision_note: str | None = None
    resolved_by: str | None = None


@dataclass(slots=True)
class ReviewRequestResolveResult:
    review_request: ReviewRequest
    event_record: EventRecord
    task_intents: list[TaskIntent]
    farming_tasks: list[FarmingTask]
    operation_plans: list[OperationPlan]


class ReviewRequestService:
    def __init__(
        self,
        review_request_repository: ReviewRequestRepository,
        event_record_repository: EventRecordRepository,
        plan_orchestrator: ReviewRequestEventDispatcher,
    ) -> None:
        self.review_request_repository = review_request_repository
        self.event_record_repository = event_record_repository
        self.plan_orchestrator = plan_orchestrator

    def resolve(self, review_request_id: int, payload: ReviewRequestResolveInput) -> ReviewRequestResolveResult:
        if payload.decision not in ALLOWED_REVIEW_DECISIONS:
            raise ValueError(f"Unsupported review decision: {payload.decision}.")

        review_request = self.review_request_repository.get(review_request_id)
        if review_request is None:
            raise LookupError(f"Review request {review_request_id} does not exist.")
        if review_request.status != REVIEW_REQUEST_STATUS_OPEN:
            raise ValueError(f"Review request {review_request_id} is not open.")

        now = _utcnow()
        review_request.status = REVIEW_REQUEST_STATUS_RESOLVED
        review_request.decision = payload.decision
        review_request.resolved_by = payload.resolved_by
        review_request.resolved_at = now
        review_request.decision_payload = {
            **(review_request.decision_payload or {}),
            "decisionInput": payload.decision_payload,
            "decisionNote": payload.decision_note,
        }
        event_record = self._record_resolved_event(review_request, payload, now)
        orchestrator_result = self.plan_orchestrator.handle(event_record)
        return ReviewRequestResolveResult(
            review_request=review_request,
            event_record=event_record,
            task_intents=orchestrator_result.task_intents,
            farming_tasks=orchestrator_result.farming_tasks,
            operation_plans=orchestrator_result.operation_plans,
        )

    def _record_resolved_event(
        self,
        review_request: ReviewRequest,
        payload: ReviewRequestResolveInput,
        occurred_at: datetime,
    ) -> EventRecord:
        event_record = EventRecord(
            planting_plan_id=review_request.planting_plan_id,
            event_type=EVENT_TYPE_REVIEW_REQUEST_RESOLVED,
            event_category="review",
            event_source="api",
            source_system="cropflow",
            source_record_id=str(review_request.id),
            payload={
                "reviewRequestId": review_request.id,
                "sourceEntityType": review_request.source_entity_type,
                "sourceEntityId": review_request.source_entity_id,
                "decision": payload.decision,
                "decisionPayload": payload.decision_payload,
                "decisionNote": payload.decision_note,
                "resolvedBy": payload.resolved_by,
            },
            occurred_at=occurred_at,
            processing_status=EVENT_PROCESSING_STATUS_RECEIVED,
            idempotency_key=f"review-request-resolved:{review_request.id}:{payload.decision}:{occurred_at.isoformat()}",
            created_by_type="user",
            created_by_id=payload.resolved_by or "api",
        )
        self.event_record_repository.add(event_record)
        self.event_record_repository.flush()
        return event_record


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
