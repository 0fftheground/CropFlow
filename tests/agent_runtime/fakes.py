from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.agent_runtime.actions import ActionInvocation
from app.agent_runtime.contracts import (
    ActionRejected,
    AgentEventEnvelope,
    AgentRole,
    ModelRequest,
    ModelTurnResult,
    RuntimeActor,
    RuntimeRejected,
    RuntimeScope,
)
from app.agent_runtime.ontology import CropFlowOntology


class MemoryRepository:
    def __init__(self, *, role: str = "observer") -> None:
        self.users = {
            "user-1": SimpleNamespace(
                id="user-1",
                username="tester",
                display_name="测试用户",
                status="active",
                metadata_payload={"agent_roles": [role]},
            )
        }
        self.sessions: dict[str, SimpleNamespace] = {}
        self.messages: dict[str, SimpleNamespace] = {}
        self.runs: dict[str, SimpleNamespace] = {}
        self.tool_calls: dict[str, SimpleNamespace] = {}
        self.approvals: dict[str, SimpleNamespace] = {}
        self.events: list[AgentEventEnvelope] = []
        self.audits: list[dict[str, Any]] = []
        self.rollback_count = 0

    def get_user(self, user_id: str):
        return self.users.get(user_id)

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def ensure_session(self, *, session_id: str, user_id: str, planting_plan_id: int, selected_role: str):
        existing = self.sessions.get(session_id)
        if existing:
            if (existing.user_id, existing.planting_plan_id, existing.selected_role) != (
                user_id,
                planting_plan_id,
                selected_role,
            ):
                raise RuntimeRejected("session scope mismatch", code="session_scope_mismatch")
            return existing
        entity = SimpleNamespace(
            id=session_id,
            user_id=user_id,
            planting_plan_id=planting_plan_id,
            selected_role=selected_role,
            status="active",
        )
        self.sessions[session_id] = entity
        return entity

    def add_message(self, *, session_id: str, role: str, content: str, run_id=None, metadata=None):
        entity = SimpleNamespace(
            id=f"msg-{uuid4().hex}",
            session_id=session_id,
            run_id=run_id,
            role=role,
            content=content,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.messages[entity.id] = entity
        return entity

    def get_message(self, message_id: str):
        return self.messages.get(message_id)

    def list_recent_messages(self, session_id: str, *, limit: int = 20):
        items = [item for item in self.messages.values() if item.session_id == session_id][-limit:]
        return [
            {"message_id": item.id, "role": item.role, "content": item.content, "created_at": None}
            for item in items
        ]

    def get_active_run_for_session(self, session_id: str):
        return next(
            (
                item
                for item in self.runs.values()
                if item.session_id == session_id and item.status in {"pending", "running", "waiting_approval"}
            ),
            None,
        )

    def create_run(self, *, run_id: str, session_id: str, user_message_id: str, provider_name: str):
        entity = SimpleNamespace(
            id=run_id,
            session_id=session_id,
            user_message_id=user_message_id,
            provider_name=provider_name,
            provider_state={},
            status="pending",
            iteration=0,
            started_at=None,
            completed_at=None,
            error_code=None,
            error_message=None,
        )
        self.runs[run_id] = entity
        self.messages[user_message_id].run_id = run_id
        return entity

    def get_run(self, run_id: str):
        return self.runs.get(run_id)

    def update_run(self, run_id: str, **changes):
        entity = self.runs[run_id]
        for key, value in changes.items():
            setattr(entity, key, value)
        return entity

    def create_tool_call(
        self,
        *,
        run_id: str,
        call_id: str,
        action_name: str,
        arguments: dict[str, Any],
        approval_required: bool,
    ):
        if call_id in self.tool_calls:
            existing = self.tool_calls[call_id]
            if (
                existing.run_id != run_id
                or existing.action_name != action_name
                or existing.arguments != arguments
            ):
                raise RuntimeRejected("tool call id conflict", code="tool_call_id_conflict")
            return existing
        entity = SimpleNamespace(
            id=call_id,
            run_id=run_id,
            action_name=action_name,
            arguments=arguments,
            approval_required=approval_required,
            status="proposed",
            result={},
            error_code=None,
            error_message=None,
            started_at=None,
            completed_at=None,
        )
        self.tool_calls[call_id] = entity
        return entity

    def get_tool_call(self, call_id: str):
        return self.tool_calls.get(call_id)

    def update_tool_call(self, call_id: str, **changes):
        entity = self.tool_calls[call_id]
        for key, value in changes.items():
            setattr(entity, key, value)
        return entity

    def list_tool_results(self, run_id: str):
        return [
            {
                "call_id": item.id,
                "action_name": item.action_name,
                "status": item.status,
                "result": item.result,
                "error_code": item.error_code,
                "error_message": item.error_message,
            }
            for item in self.tool_calls.values()
            if item.run_id == run_id and item.status in {"completed", "rejected", "failed", "unknown"}
        ]

    def begin_action_transaction(self):
        repository = self

        class MemoryActionTransaction:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                if exc_type is not None:
                    repository.rollback_count += 1
                return False

        return MemoryActionTransaction()

    def create_approval(
        self,
        *,
        run_id: str,
        tool_call_id: str,
        action_name: str,
        action_summary: str,
        requested_by: str,
    ):
        existing = self.get_approval_by_tool_call(tool_call_id)
        if existing:
            return existing
        entity = SimpleNamespace(
            id=f"approval-{uuid4().hex}",
            run_id=run_id,
            tool_call_id=tool_call_id,
            action_name=action_name,
            action_summary=action_summary,
            requested_by=requested_by,
            status="pending",
            decided_by=None,
            decision_note=None,
            decided_at=None,
        )
        self.approvals[entity.id] = entity
        return entity

    def get_approval(self, approval_id: str):
        return self.approvals.get(approval_id)

    def get_approval_for_update(self, approval_id: str):
        return self.get_approval(approval_id)

    def get_approval_by_tool_call(self, tool_call_id: str):
        return next((item for item in self.approvals.values() if item.tool_call_id == tool_call_id), None)

    def update_approval(self, approval_id: str, **changes):
        entity = self.approvals[approval_id]
        for key, value in changes.items():
            setattr(entity, key, value)
        return entity

    def list_pending_approvals(self, run_id: str):
        return [item for item in self.approvals.values() if item.run_id == run_id and item.status == "pending"]

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]):
        sequence = sum(item.run_id == run_id for item in self.events) + 1
        event = AgentEventEnvelope(
            event_id=sequence,
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
        )
        self.events.append(event)
        return event

    def list_events(self, run_id: str, *, after_sequence: int = 0):
        return [item for item in self.events if item.run_id == run_id and item.sequence > after_sequence]

    def append_audit(self, *, run_id: str, audit_type: str, actor_user_id: str | None, payload):
        self.audits.append(
            {"run_id": run_id, "audit_type": audit_type, "actor_user_id": actor_user_id, "payload": payload}
        )


class FakeContextBuilder:
    def __init__(self, repository: MemoryRepository, ontology: CropFlowOntology) -> None:
        self.repository = repository
        self.ontology = ontology
        self.task_status = "pending"
        self.review_status = "open"
        self.extra_object_view: dict[str, Any] = {}

    def resolve_actor(self, user_id: str, requested_role: str | None):
        user = self.repository.get_user(user_id)
        if user is None:
            raise RuntimeRejected("user missing", code="user_not_found")
        role = AgentRole(requested_role or user.metadata_payload["agent_roles"][0])
        if role.value not in user.metadata_payload["agent_roles"]:
            raise RuntimeRejected("role missing", code="role_not_assigned")
        return RuntimeActor(user_id=user.id, display_name=user.display_name, role=role)

    def load_snapshot(self, planting_plan_id: int):
        if planting_plan_id != 1:
            raise RuntimeRejected("plan missing", code="planting_plan_not_found")
        scope = RuntimeScope(
            planting_plan_id=1,
            plan_status="active",
            pending_task_count=int(self.task_status in {"pending", "confirmed", "in_progress"}),
            open_review_count=int(self.review_status == "open"),
        )
        object_view = {
            "object_type": "PlantingPlan",
            "object_id": 1,
            "status": "active",
            "current_tasks": [{"task_id": 10, "status": self.task_status}],
            "open_review_requests": [{"review_request_id": 20, "status": self.review_status}],
        }
        object_view.update(self.extra_object_view)
        return SimpleNamespace(
            scope=scope,
            object_view=object_view,
        )

    def build_model_request(
        self,
        *,
        run_id: str,
        session_id: str,
        user_input: str,
        actor: RuntimeActor,
        provider_state: dict[str, Any],
    ):
        session = self.repository.get_session(session_id)
        snapshot = self.load_snapshot(session.planting_plan_id)
        actions = self.ontology.resolve_actions(actor, snapshot.scope)
        return ModelRequest(
            run_id=run_id,
            current_user_input=user_input,
            recent_messages=tuple(self.repository.list_recent_messages(session_id)),
            actor={"user_id": actor.user_id, "display_name": actor.display_name, "role": actor.role.value},
            object_view=snapshot.object_view,
            available_actions=tuple(item.model_schema() for item in actions),
            tool_results=tuple(self.repository.list_tool_results(run_id)),
            provider_state=provider_state,
        )


class FakeActionExecutor:
    def __init__(self, context_builder: FakeContextBuilder, ontology: CropFlowOntology) -> None:
        self.context_builder = context_builder
        self.ontology = ontology
        self.executed: list[str] = []
        self.fail_actions: set[str] = set()
        self.result_overrides: dict[str, dict[str, Any]] = {}
        self.active_parallel_query_executions = 0
        self.max_parallel_query_executions = 0

    def validate(self, invocation: ActionInvocation):
        contract = self.ontology.get_action(invocation.action_name)
        if contract is None:
            raise ActionRejected("unknown", code="unknown_action")
        available = {item.name for item in self.ontology.resolve_actions(invocation.actor, invocation.scope)}
        if invocation.action_name not in available:
            raise ActionRejected("not available", code="action_not_available")
        if "task_id" in invocation.arguments:
            if invocation.arguments.get("task_id") != 10:
                raise ActionRejected("wrong task scope", code="object_scope_mismatch")
        if "review_request_id" in invocation.arguments:
            if invocation.arguments.get("review_request_id") != 20:
                raise ActionRejected("wrong review scope", code="object_scope_mismatch")
        if invocation.action_name == "complete_farming_task":
            if self.context_builder.task_status not in {"pending", "confirmed", "in_progress"}:
                raise ActionRejected("stale task state", code="business_state_mismatch")
        if invocation.action_name == "resolve_review_request" and self.context_builder.review_status != "open":
            raise ActionRejected("stale review state", code="business_state_mismatch")
        return contract

    def execute(self, invocation: ActionInvocation):
        self.validate(invocation)
        if invocation.action_name in self.fail_actions:
            raise RuntimeError(f"simulated {invocation.action_name} failure")
        self.executed.append(invocation.action_name)
        if invocation.action_name in self.result_overrides:
            return self.result_overrides[invocation.action_name]
        if invocation.action_name == "complete_farming_task":
            self.context_builder.task_status = "completed"
            return {"task_id": 10, "task_status": "completed"}
        if invocation.action_name == "view_plan_context":
            return self.context_builder.load_snapshot(1).object_view
        if invocation.action_name == "get_task_detail":
            return {"farming_task": {"task_id": 10, "status": self.context_builder.task_status}}
        if invocation.action_name == "get_review_request_detail":
            return {
                "review_request": {
                    "review_request_id": 20,
                    "status": self.context_builder.review_status,
                }
            }
        if invocation.action_name == "resolve_review_request":
            self.context_builder.review_status = "resolved"
            return {"review_request_id": 20, "status": "resolved"}
        return {"ok": True}

    async def execute_parallel_query(self, invocation: ActionInvocation):
        self.active_parallel_query_executions += 1
        self.max_parallel_query_executions = max(
            self.max_parallel_query_executions,
            self.active_parallel_query_executions,
        )
        try:
            await asyncio.sleep(0.01)
            return self.execute(invocation)
        finally:
            self.active_parallel_query_executions -= 1

    def approval_summary(self, invocation: ActionInvocation):
        return f"approve {invocation.action_name}"


class SequenceProvider:
    name = "sequence"

    def __init__(self, turns: list[ModelTurnResult]) -> None:
        self.turns = list(turns)
        self.requests: list[ModelRequest] = []

    async def complete_turn(self, request: ModelRequest):
        self.requests.append(request)
        if not self.turns:
            raise AssertionError("No scripted model turn remains")
        return self.turns.pop(0)


class DummyDb:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
