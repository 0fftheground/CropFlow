from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4


class AgentRole(StrEnum):
    OBSERVER = "observer"
    OPERATOR = "operator"
    REVIEWER = "reviewer"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCallStatus(StrEnum):
    PROPOSED = "proposed"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class RuntimeActor:
    user_id: str
    display_name: str
    role: AgentRole


@dataclass(frozen=True, slots=True)
class RuntimeScope:
    planting_plan_id: int
    plan_status: str
    pending_task_count: int
    open_review_count: int


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = field(default_factory=lambda: f"call-{uuid4().hex}")


@dataclass(frozen=True, slots=True)
class ModelTurnResult:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "end_turn"
    provider_state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelRequest:
    run_id: str
    current_user_input: str
    recent_messages: tuple[dict[str, Any], ...]
    actor: dict[str, Any]
    object_view: dict[str, Any]
    available_actions: tuple[dict[str, Any], ...]
    tool_results: tuple[dict[str, Any], ...]
    provider_state: dict[str, Any]


class ModelProvider(Protocol):
    name: str

    async def complete_turn(self, request: ModelRequest) -> ModelTurnResult:
        ...


@dataclass(frozen=True, slots=True)
class RunCommand:
    user_id: str
    planting_plan_id: int
    message: str
    session_id: str | None = None
    role: str | None = None


@dataclass(frozen=True, slots=True)
class AgentEventEnvelope:
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any]
    event_id: int | None = None
    created_at: datetime | None = None

    def to_sse(self) -> str:
        data = json.dumps(self.payload, ensure_ascii=False, default=str)
        event_id = self.event_id if self.event_id is not None else self.sequence
        return f"id: {event_id}\nevent: {self.event_type}\ndata: {data}\n\n"


class RuntimeRejected(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "runtime_rejected",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class ActionRejected(RuntimeRejected):
    pass


class ApprovalRejected(RuntimeRejected):
    pass
