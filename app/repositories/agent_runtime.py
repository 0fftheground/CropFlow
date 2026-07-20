from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent_runtime.contracts import AgentEventEnvelope, RuntimeRejected
from app.models import (
    AgentApprovalRequest,
    AgentAuditRecord,
    AgentEvent,
    AgentMessage,
    AgentRun,
    AgentSession,
    AgentToolCall,
    User,
)


ACTIVE_RUN_STATUSES = {"pending", "running", "waiting_approval"}


class AgentRuntimeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: str) -> User | None:
        return self.session.get(User, user_id)

    def get_session(self, session_id: str) -> AgentSession | None:
        return self.session.get(AgentSession, session_id)

    def ensure_session(
        self,
        *,
        session_id: str,
        user_id: str,
        planting_plan_id: int,
        selected_role: str,
    ) -> AgentSession:
        existing = self.get_session(session_id)
        if existing is not None:
            if (
                existing.user_id != user_id
                or existing.planting_plan_id != planting_plan_id
                or existing.selected_role != selected_role
            ):
                raise RuntimeRejected(
                    "Agent session cannot change user, role, or active PlantingPlan.",
                    code="session_scope_mismatch",
                )
            return existing

        entity = AgentSession(
            id=session_id,
            user_id=user_id,
            planting_plan_id=planting_plan_id,
            selected_role=selected_role,
            status="active",
            metadata_payload={},
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def add_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        entity = AgentMessage(
            id=f"msg-{uuid4().hex}",
            session_id=session_id,
            run_id=run_id,
            role=role,
            content=content,
            metadata_payload=metadata or {},
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_message(self, message_id: str) -> AgentMessage | None:
        return self.session.get(AgentMessage, message_id)

    def list_recent_messages(self, session_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        stmt = (
            select(AgentMessage)
            .where(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
        )
        items = list(reversed(list(self.session.scalars(stmt))))
        return [
            {
                "message_id": item.id,
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]

    def get_active_run_for_session(self, session_id: str) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .where(AgentRun.session_id == session_id)
            .where(AgentRun.status.in_(ACTIVE_RUN_STATUSES))
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def create_run(
        self,
        *,
        run_id: str,
        session_id: str,
        user_message_id: str,
        provider_name: str,
    ) -> AgentRun:
        entity = AgentRun(
            id=run_id,
            session_id=session_id,
            user_message_id=user_message_id,
            provider_name=provider_name,
            provider_state={},
            status="pending",
            iteration=0,
        )
        self.session.add(entity)
        self.session.flush()
        message = self.get_message(user_message_id)
        if message is not None:
            message.run_id = run_id
        self.session.flush()
        return entity

    def get_run(self, run_id: str) -> AgentRun | None:
        return self.session.get(AgentRun, run_id)

    def update_run(self, run_id: str, **changes: Any) -> AgentRun:
        entity = self.get_run(run_id)
        if entity is None:
            raise LookupError(f"Agent run {run_id} does not exist.")
        for name, value in changes.items():
            setattr(entity, name, value)
        self.session.flush()
        return entity

    def create_tool_call(
        self,
        *,
        run_id: str,
        call_id: str,
        action_name: str,
        arguments: dict[str, Any],
        approval_required: bool,
    ) -> AgentToolCall:
        existing = self.get_tool_call(call_id)
        if existing is not None:
            if (
                existing.run_id != run_id
                or existing.action_name != action_name
                or dict(existing.arguments or {}) != arguments
            ):
                raise RuntimeRejected(
                    f"Agent tool call id {call_id} conflicts with a different persisted proposal.",
                    code="tool_call_id_conflict",
                )
            return existing
        entity = AgentToolCall(
            id=call_id,
            run_id=run_id,
            action_name=action_name,
            arguments=arguments,
            status="proposed",
            result={},
            approval_required=approval_required,
            idempotency_key=f"{run_id}:{call_id}:{action_name}",
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_tool_call(self, call_id: str) -> AgentToolCall | None:
        return self.session.get(AgentToolCall, call_id)

    def update_tool_call(self, call_id: str, **changes: Any) -> AgentToolCall:
        entity = self.get_tool_call(call_id)
        if entity is None:
            raise LookupError(f"Agent tool call {call_id} does not exist.")
        for name, value in changes.items():
            setattr(entity, name, value)
        self.session.flush()
        return entity

    def begin_action_transaction(self):
        """Isolate one Tool execution from Runtime state in the outer transaction."""
        return self.session.begin_nested()

    def list_tool_results(self, run_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(AgentToolCall)
            .where(AgentToolCall.run_id == run_id)
            .where(AgentToolCall.status.in_({"completed", "rejected", "failed", "unknown"}))
            .order_by(AgentToolCall.created_at.asc())
        )
        return [
            {
                "call_id": item.id,
                "action_name": item.action_name,
                "status": item.status,
                "result": item.result or {},
                "error_code": item.error_code,
                "error_message": item.error_message,
            }
            for item in self.session.scalars(stmt)
        ]

    def create_approval(
        self,
        *,
        run_id: str,
        tool_call_id: str,
        action_name: str,
        action_summary: str,
        requested_by: str,
    ) -> AgentApprovalRequest:
        existing = self.get_approval_by_tool_call(tool_call_id)
        if existing is not None:
            return existing
        entity = AgentApprovalRequest(
            id=f"approval-{uuid4().hex}",
            run_id=run_id,
            tool_call_id=tool_call_id,
            status="pending",
            action_name=action_name,
            action_summary=action_summary,
            requested_by=requested_by,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_approval(self, approval_id: str) -> AgentApprovalRequest | None:
        return self.session.get(AgentApprovalRequest, approval_id)

    def get_approval_for_update(self, approval_id: str) -> AgentApprovalRequest | None:
        stmt = (
            select(AgentApprovalRequest)
            .where(AgentApprovalRequest.id == approval_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.session.scalar(stmt)

    def get_approval_by_tool_call(self, tool_call_id: str) -> AgentApprovalRequest | None:
        stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.tool_call_id == tool_call_id)
        return self.session.scalar(stmt)

    def update_approval(self, approval_id: str, **changes: Any) -> AgentApprovalRequest:
        entity = self.get_approval(approval_id)
        if entity is None:
            raise LookupError(f"Agent approval {approval_id} does not exist.")
        for name, value in changes.items():
            setattr(entity, name, value)
        self.session.flush()
        return entity

    def list_pending_approvals(self, run_id: str) -> list[AgentApprovalRequest]:
        stmt = (
            select(AgentApprovalRequest)
            .where(AgentApprovalRequest.run_id == run_id)
            .where(AgentApprovalRequest.status == "pending")
            .order_by(AgentApprovalRequest.created_at.asc())
        )
        return list(self.session.scalars(stmt))

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> AgentEventEnvelope:
        sequence_stmt = select(func.coalesce(func.max(AgentEvent.sequence), 0) + 1).where(AgentEvent.run_id == run_id)
        sequence = int(self.session.scalar(sequence_stmt) or 1)
        entity = AgentEvent(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
        )
        self.session.add(entity)
        self.session.flush()
        return AgentEventEnvelope(
            event_id=entity.id,
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
            created_at=entity.created_at,
        )

    def list_events(self, run_id: str, *, after_sequence: int = 0) -> list[AgentEventEnvelope]:
        stmt = (
            select(AgentEvent)
            .where(AgentEvent.run_id == run_id)
            .where(AgentEvent.sequence > after_sequence)
            .order_by(AgentEvent.sequence.asc())
        )
        return [
            AgentEventEnvelope(
                event_id=item.id,
                run_id=item.run_id,
                sequence=item.sequence,
                event_type=item.event_type,
                payload=item.payload or {},
                created_at=item.created_at,
            )
            for item in self.session.scalars(stmt)
        ]

    def append_audit(
        self,
        *,
        run_id: str,
        audit_type: str,
        actor_user_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        self.session.add(
            AgentAuditRecord(
                run_id=run_id,
                audit_type=audit_type,
                actor_user_id=actor_user_id,
                payload=payload,
            )
        )
        self.session.flush()


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
