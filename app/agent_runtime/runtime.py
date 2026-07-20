from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import uuid4

from app.agent_runtime.actions import ActionInvocation, CropFlowActionExecutor
from app.agent_runtime.contracts import (
    ActionRejected,
    AgentEventEnvelope,
    ApprovalRejected,
    ApprovalStatus,
    ModelProvider,
    RunCommand,
    RunStatus,
    RuntimeActor,
    RuntimeRejected,
    RuntimeScope,
    ToolCall,
    ToolCallStatus,
)
from app.agent_runtime.projection import CropFlowContextBuilder
from app.agent_runtime.resilience import RunBudgetPolicy
from app.repositories.agent_runtime import AgentRuntimeRepository, utcnow_naive


TERMINAL_TOOL_CALL_STATUSES = {
    ToolCallStatus.COMPLETED.value,
    ToolCallStatus.REJECTED.value,
    ToolCallStatus.FAILED.value,
    ToolCallStatus.UNKNOWN.value,
}


@dataclass(frozen=True, slots=True)
class PreparedRun:
    run_id: str
    session_id: str
    user_message_id: str


class AgentRuntime:
    def __init__(
        self,
        *,
        repository: AgentRuntimeRepository,
        context_builder: CropFlowContextBuilder,
        action_executor: CropFlowActionExecutor,
        model_provider: ModelProvider,
        max_iterations: int = 8,
        parallel_query_executor: Callable[[ActionInvocation], Awaitable[dict[str, Any]]] | None = None,
        max_parallel_queries: int = 4,
        budget_policy: RunBudgetPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.context_builder = context_builder
        self.action_executor = action_executor
        self.model_provider = model_provider
        self.max_iterations = max_iterations
        self.parallel_query_executor = parallel_query_executor
        self.max_parallel_queries = max(1, max_parallel_queries)
        self.budget_policy = budget_policy or RunBudgetPolicy()

    def prepare_run(self, command: RunCommand) -> PreparedRun:
        actor = self.context_builder.resolve_actor(command.user_id, command.role)
        self.context_builder.load_snapshot(command.planting_plan_id)
        session_id = command.session_id or f"session-{uuid4().hex}"
        self.repository.ensure_session(
            session_id=session_id,
            user_id=actor.user_id,
            planting_plan_id=command.planting_plan_id,
            selected_role=actor.role.value,
        )
        active_run = self.repository.get_active_run_for_session(session_id)
        if active_run is not None:
            raise RuntimeRejected(
                f"Agent session {session_id} already has active run {active_run.id}.",
                code="session_run_conflict",
            )
        user_message = self.repository.add_message(
            session_id=session_id,
            role="user",
            content=command.message,
        )
        run_id = f"run-{uuid4().hex}"
        self.repository.create_run(
            run_id=run_id,
            session_id=session_id,
            user_message_id=user_message.id,
            provider_name=self.model_provider.name,
        )
        self.repository.append_audit(
            run_id=run_id,
            audit_type="run_prepared",
            actor_user_id=actor.user_id,
            payload={
                "session_id": session_id,
                "planting_plan_id": command.planting_plan_id,
                "selected_role": actor.role.value,
            },
        )
        return PreparedRun(run_id=run_id, session_id=session_id, user_message_id=user_message.id)

    async def run(
        self,
        command: RunCommand,
        *,
        prepared: PreparedRun | None = None,
    ) -> AsyncIterator[AgentEventEnvelope]:
        prepared_run = prepared or self.prepare_run(command)
        run = self.repository.get_run(prepared_run.run_id)
        if run is None:
            raise RuntimeRejected(f"Agent run {prepared_run.run_id} does not exist.", code="run_not_found")
        self.repository.update_run(
            run.id,
            status=RunStatus.RUNNING.value,
            started_at=run.started_at or utcnow_naive(),
        )
        yield self._emit(
            run.id,
            "run_started",
            {
                "session_id": prepared_run.session_id,
                "user_message_id": prepared_run.user_message_id,
                "active_object": {"type": "PlantingPlan", "id": command.planting_plan_id},
            },
        )
        deadline = self._new_execution_deadline()
        async for event in self._continue_run(run.id, deadline=deadline):
            yield event

    async def decide_approval(
        self,
        *,
        approval_id: str,
        decision: str,
        decided_by: str,
        decision_note: str | None = None,
    ) -> AsyncIterator[AgentEventEnvelope]:
        deadline = self._new_execution_deadline()
        approval = self.repository.get_approval_for_update(approval_id)
        if approval is None:
            raise ApprovalRejected(f"Agent approval {approval_id} does not exist.", code="approval_not_found")
        if approval.status != ApprovalStatus.PENDING.value:
            raise ApprovalRejected(
                f"Agent approval {approval_id} is already {approval.status}.",
                code="approval_already_decided",
            )
        if decision not in {ApprovalStatus.APPROVED.value, ApprovalStatus.DENIED.value}:
            raise ApprovalRejected(f"Unsupported approval decision: {decision}.", code="invalid_approval_decision")

        run = self.repository.get_run(approval.run_id)
        if run is None:
            raise ApprovalRejected(f"Agent run {approval.run_id} does not exist.", code="run_not_found")
        session = self.repository.get_session(run.session_id)
        if session is None:
            raise ApprovalRejected(f"Agent session {run.session_id} does not exist.", code="session_not_found")
        if decided_by != session.user_id:
            raise ApprovalRejected(
                "Approval must be decided by the user who owns the active Agent session.",
                code="approval_actor_mismatch",
            )
        self.context_builder.resolve_actor(decided_by, session.selected_role)

        tool_call = self.repository.get_tool_call(approval.tool_call_id)
        if tool_call is None:
            raise ApprovalRejected(
                f"Tool call {approval.tool_call_id} does not exist.",
                code="tool_call_not_found",
            )
        if tool_call.run_id != run.id or tool_call.status != ToolCallStatus.WAITING_APPROVAL.value:
            raise ApprovalRejected(
                "Approval target is no longer waiting for a decision.",
                code="approval_target_state_mismatch",
            )

        now = utcnow_naive()
        self.repository.update_approval(
            approval_id,
            status=decision,
            decided_by=decided_by,
            decision_note=decision_note,
            decided_at=now,
        )
        self.repository.append_audit(
            run_id=run.id,
            audit_type="approval_decided",
            actor_user_id=decided_by,
            payload={
                "approval_id": approval_id,
                "tool_call_id": approval.tool_call_id,
                "decision": decision,
                "decision_note": decision_note,
            },
        )
        yield self._emit(
            run.id,
            "approval_decided",
            {
                "approval_id": approval_id,
                "tool_call_id": approval.tool_call_id,
                "decision": decision,
                "decided_by": decided_by,
            },
        )

        if decision == ApprovalStatus.DENIED.value:
            rejection = {
                "code": "approval_denied",
                "message": decision_note or "The user denied this action.",
            }
            self.repository.update_tool_call(
                tool_call.id,
                status=ToolCallStatus.REJECTED.value,
                result=rejection,
                error_code="approval_denied",
                error_message=rejection["message"],
                completed_at=now,
            )
            self.repository.update_run(run.id, status=RunStatus.RUNNING.value)
            yield self._emit(
                run.id,
                "tool_execution_rejected",
                {"call_id": tool_call.id, "name": tool_call.action_name, **rejection},
            )
            async for event in self._continue_run(run.id, deadline=deadline):
                yield event
            return

        self.repository.update_run(run.id, status=RunStatus.RUNNING.value)
        try:
            async for event in self._execute_persisted_tool_call(run.id, tool_call.id, deadline=deadline):
                yield event
        except ActionRejected as exc:
            actor = self.context_builder.resolve_actor(session.user_id, session.selected_role)
            self._reject_tool_call(tool_call.id, exc, actor)
            yield self._emit(
                run.id,
                "tool_execution_rejected",
                {
                    "call_id": tool_call.id,
                    "name": tool_call.action_name,
                    "code": exc.code,
                    "message": exc.message,
                },
            )
            async for event in self._continue_run(run.id, deadline=deadline):
                yield event
            return
        except Exception as exc:
            async for event in self._fail_run(run.id, exc):
                yield event
            return
        async for event in self._continue_run(run.id, deadline=deadline):
            yield event

    async def _continue_run(
        self,
        run_id: str,
        *,
        deadline: float,
    ) -> AsyncIterator[AgentEventEnvelope]:
        run = self.repository.get_run(run_id)
        if run is None:
            raise RuntimeRejected(f"Agent run {run_id} does not exist.", code="run_not_found")
        session = self.repository.get_session(run.session_id)
        user_message = self.repository.get_message(run.user_message_id)
        if session is None or user_message is None:
            raise RuntimeRejected("Agent run persistence is incomplete.", code="run_state_incomplete")

        try:
            for iteration in range(run.iteration + 1, self.max_iterations + 1):
                self._ensure_execution_time(deadline)
                actor = self.context_builder.resolve_actor(session.user_id, session.selected_role)
                snapshot = self.context_builder.load_snapshot(session.planting_plan_id)
                provider_state = dict(run.provider_state or {})
                budget_snapshot = self.budget_policy.enforce(provider_state, before_model_call=True)
                provider_state["runtime_budget"] = budget_snapshot
                model_request = self.context_builder.build_model_request(
                    run_id=run_id,
                    session_id=session.id,
                    user_input=user_message.content,
                    actor=actor,
                    provider_state=provider_state,
                )
                run = self.repository.update_run(
                    run_id,
                    iteration=iteration,
                    provider_state=provider_state,
                )
                yield self._emit(
                    run_id,
                    "context_built",
                    {
                        "iteration": iteration,
                        "planting_plan_status": snapshot.scope.plan_status,
                        "available_actions": [item["name"] for item in model_request.available_actions],
                    },
                )
                yield self._emit(run_id, "model_call_started", {"iteration": iteration})
                try:
                    async with asyncio.timeout(self._remaining_execution_seconds(deadline)):
                        turn = await self.model_provider.complete_turn(model_request)
                except TimeoutError as exc:
                    raise self._execution_timeout_error() from exc
                provider_state = dict(turn.provider_state or {})
                budget_snapshot = self.budget_policy.snapshot(provider_state)
                provider_state["runtime_budget"] = budget_snapshot
                run = self.repository.update_run(run_id, provider_state=provider_state)
                yield self._emit(
                    run_id,
                    "model_call_completed",
                    {
                        "iteration": iteration,
                        "finish_reason": turn.finish_reason,
                        "tool_call_count": len(turn.tool_calls),
                        "usage_totals": provider_state.get("usage_totals", {}),
                        "provider_attempt_count": (
                            provider_state.get("provider_attempts_history", [0])[-1]
                            if provider_state.get("provider_attempts_history")
                            else None
                        ),
                        "runtime_budget": budget_snapshot,
                    },
                )
                self.budget_policy.enforce(provider_state)
                if turn.finish_reason == "length":
                    raise RuntimeRejected(
                        "Model output reached max_tokens before the turn completed.",
                        code="model_output_truncated",
                    )

                if turn.tool_calls:
                    if turn.text:
                        yield self._emit(
                            run_id,
                            "progress_message",
                            {"iteration": iteration, "text": turn.text},
                        )
                    # Persist in provider order before scheduling so Tool Results
                    # are reinjected in the same stable order after parallel work.
                    for model_call in turn.tool_calls:
                        model_contract = self.action_executor.ontology.get_action(model_call.name)
                        self.repository.create_tool_call(
                            run_id=run_id,
                            call_id=model_call.call_id,
                            action_name=model_call.name,
                            arguments=model_call.arguments,
                            approval_required=bool(model_contract and model_contract.approval_required),
                        )
                    parallel_queries = []
                    serial_actions = []
                    for model_call in turn.tool_calls:
                        model_contract = self.action_executor.ontology.get_action(model_call.name)
                        if (
                            model_contract is not None
                            and model_contract.parallel_safe
                            and not model_contract.side_effect
                            and not model_contract.approval_required
                        ):
                            parallel_queries.append(model_call)
                        else:
                            serial_actions.append(model_call)

                    if parallel_queries:
                        for serial_call in serial_actions:
                            contract = self.action_executor.ontology.get_action(serial_call.name)
                            if contract is None:
                                code = "unknown_action"
                                message = f"Unknown action: {serial_call.name}."
                            elif contract.side_effect or contract.approval_required:
                                code = "side_effect_requires_replan"
                                message = (
                                    "A side-effect action cannot execute in the same model batch as queries. "
                                    "Review the query results and propose one action in a new model turn."
                                )
                            else:
                                code = "serial_action_requires_replan"
                                message = "This action is not safe for parallel execution and must be proposed again."
                            for event in self._reject_model_call(
                                run_id=run_id,
                                model_call=serial_call,
                                actor=actor,
                                code=code,
                                message=message,
                            ):
                                yield event

                        try:
                            async with asyncio.timeout(self._remaining_execution_seconds(deadline)):
                                query_events = await self._execute_parallel_query_batch(
                                    run_id=run_id,
                                    model_calls=parallel_queries,
                                    actor=actor,
                                    scope=snapshot.scope,
                                )
                        except TimeoutError as exc:
                            for model_call in parallel_queries:
                                tool_call = self.repository.get_tool_call(model_call.call_id)
                                if tool_call is None or tool_call.status != ToolCallStatus.RUNNING.value:
                                    continue
                                self.repository.update_tool_call(
                                    tool_call.id,
                                    status=ToolCallStatus.FAILED.value,
                                    result={},
                                    error_code="run_execution_timeout",
                                    error_message="Parallel query exceeded the active run execution timeout.",
                                    completed_at=utcnow_naive(),
                                )
                                self.repository.append_audit(
                                    run_id=run_id,
                                    audit_type="action_failed",
                                    actor_user_id=actor.user_id,
                                    payload={
                                        "call_id": tool_call.id,
                                        "action_name": tool_call.action_name,
                                        "error_code": "run_execution_timeout",
                                        "execution_mode": "parallel_query",
                                    },
                                )
                                yield self._emit(
                                    run_id,
                                    "tool_execution_failed",
                                    {
                                        "call_id": tool_call.id,
                                        "name": tool_call.action_name,
                                        "status": ToolCallStatus.FAILED.value,
                                        "error_code": "run_execution_timeout",
                                        "message": "Parallel query exceeded the active run execution timeout.",
                                    },
                                )
                            raise self._execution_timeout_error() from exc
                        for event in query_events:
                            yield event
                        continue

                    primary_call = serial_actions[0]
                    for extra_call in serial_actions[1:]:
                        for event in self._reject_model_call(
                            run_id=run_id,
                            model_call=extra_call,
                            actor=actor,
                            code="serial_action_requires_replan",
                            message=(
                                "Only one serial or side-effect action can be handled per model turn. "
                                "Wait for its result and propose the next action in a new turn."
                            ),
                        ):
                            yield event

                    contract = self.action_executor.ontology.get_action(primary_call.name)
                    tool_call = self.repository.create_tool_call(
                        run_id=run_id,
                        call_id=primary_call.call_id,
                        action_name=primary_call.name,
                        arguments=primary_call.arguments,
                        approval_required=bool(contract and contract.approval_required),
                    )
                    if tool_call.status in TERMINAL_TOOL_CALL_STATUSES:
                        continue
                    yield self._emit(
                        run_id,
                        "tool_call_proposed",
                        {
                            "call_id": tool_call.id,
                            "name": tool_call.action_name,
                            "arguments": tool_call.arguments,
                        },
                    )
                    if contract is not None and contract.side_effect and self._has_unknown_side_effect(run_id):
                        for event in self._reject_model_call(
                            run_id=run_id,
                            model_call=primary_call,
                            actor=actor,
                            code="action_outcome_reconciliation_required",
                            message=(
                                "A previous side-effect action has an unknown outcome. "
                                "Do not retry a write action until authoritative business state is reconciled."
                            ),
                        ):
                            # The proposal event was already emitted above.
                            if event.event_type != "tool_call_proposed":
                                yield event
                        continue
                    invocation = ActionInvocation(
                        run_id=run_id,
                        call_id=tool_call.id,
                        action_name=tool_call.action_name,
                        arguments=dict(tool_call.arguments or {}),
                        actor=actor,
                        scope=snapshot.scope,
                    )
                    try:
                        validated_contract = self.action_executor.validate(invocation)
                    except ActionRejected as exc:
                        self._reject_tool_call(tool_call.id, exc, actor)
                        yield self._emit(
                            run_id,
                            "tool_execution_rejected",
                            {
                                "call_id": tool_call.id,
                                "name": tool_call.action_name,
                                "code": exc.code,
                                "message": exc.message,
                            },
                        )
                        continue

                    self.repository.append_audit(
                        run_id=run_id,
                        audit_type="pre_action_passed",
                        actor_user_id=actor.user_id,
                        payload={
                            "call_id": tool_call.id,
                            "action_name": tool_call.action_name,
                            "risk_level": validated_contract.risk_level,
                            "approval_required": validated_contract.approval_required,
                            "planting_plan_id": snapshot.scope.planting_plan_id,
                        },
                    )
                    if validated_contract.approval_required:
                        approval = self.repository.create_approval(
                            run_id=run_id,
                            tool_call_id=tool_call.id,
                            action_name=tool_call.action_name,
                            action_summary=self.action_executor.approval_summary(invocation),
                            requested_by=actor.user_id,
                        )
                        self.repository.update_tool_call(
                            tool_call.id,
                            status=ToolCallStatus.WAITING_APPROVAL.value,
                        )
                        self.repository.update_run(run_id, status=RunStatus.WAITING_APPROVAL.value)
                        self.repository.append_audit(
                            run_id=run_id,
                            audit_type="approval_requested",
                            actor_user_id=actor.user_id,
                            payload={
                                "approval_id": approval.id,
                                "call_id": tool_call.id,
                                "action_name": tool_call.action_name,
                            },
                        )
                        yield self._emit(
                            run_id,
                            "approval_required",
                            {
                                "approval_id": approval.id,
                                "call_id": tool_call.id,
                                "action_name": tool_call.action_name,
                                "summary": approval.action_summary,
                            },
                        )
                        return

                    async for event in self._execute_persisted_tool_call(
                        run_id,
                        tool_call.id,
                        deadline=deadline,
                    ):
                        yield event
                    run = self.repository.get_run(run_id)
                    continue

                assistant_message = self.repository.add_message(
                    session_id=session.id,
                    run_id=run_id,
                    role="assistant",
                    content=turn.text,
                )
                yield self._emit(
                    run_id,
                    "message_completed",
                    {
                        "message_id": assistant_message.id,
                        "role": "assistant",
                        "content": turn.text,
                    },
                )
                self.repository.update_run(
                    run_id,
                    status=RunStatus.COMPLETED.value,
                    completed_at=utcnow_naive(),
                )
                yield self._emit(run_id, "run_completed", {"iteration_count": iteration})
                return

            raise RuntimeRejected(
                f"Agent loop exceeded max_iterations={self.max_iterations}.",
                code="max_iterations_exceeded",
            )
        except Exception as exc:
            async for event in self._fail_run(run_id, exc):
                yield event

    async def _execute_parallel_query_batch(
        self,
        *,
        run_id: str,
        model_calls: list[ToolCall],
        actor: RuntimeActor,
        scope: RuntimeScope,
    ) -> list[AgentEventEnvelope]:
        events: list[AgentEventEnvelope] = []
        invocations: list[ActionInvocation] = []
        for model_call in model_calls:
            contract = self.action_executor.ontology.get_action(model_call.name)
            tool_call = self.repository.create_tool_call(
                run_id=run_id,
                call_id=model_call.call_id,
                action_name=model_call.name,
                arguments=model_call.arguments,
                approval_required=bool(contract and contract.approval_required),
            )
            if tool_call.status in TERMINAL_TOOL_CALL_STATUSES:
                continue
            events.append(
                self._emit(
                    run_id,
                    "tool_call_proposed",
                    {
                        "call_id": tool_call.id,
                        "name": tool_call.action_name,
                        "arguments": tool_call.arguments,
                    },
                )
            )
            self.repository.update_tool_call(
                tool_call.id,
                status=ToolCallStatus.RUNNING.value,
                started_at=utcnow_naive(),
            )
            events.append(
                self._emit(
                    run_id,
                    "tool_execution_started",
                    {"call_id": tool_call.id, "name": tool_call.action_name, "execution_mode": "parallel_query"},
                )
            )
            invocations.append(
                ActionInvocation(
                    run_id=run_id,
                    call_id=tool_call.id,
                    action_name=tool_call.action_name,
                    arguments=dict(tool_call.arguments or {}),
                    actor=actor,
                    scope=scope,
                )
            )

        semaphore = asyncio.Semaphore(self.max_parallel_queries)

        async def execute(invocation: ActionInvocation):
            async with semaphore:
                handler = self.parallel_query_executor or getattr(
                    self.action_executor,
                    "execute_parallel_query",
                    None,
                )
                if handler is not None:
                    return await handler(invocation)
                return self.action_executor.execute(invocation)

        results = await asyncio.gather(
            *(execute(invocation) for invocation in invocations),
            return_exceptions=True,
        )
        for invocation, result in zip(invocations, results, strict=True):
            if isinstance(result, ActionRejected):
                self._reject_tool_call(invocation.call_id, result, actor)
                events.append(
                    self._emit(
                        run_id,
                        "tool_execution_rejected",
                        {
                            "call_id": invocation.call_id,
                            "name": invocation.action_name,
                            "code": result.code,
                            "message": result.message,
                        },
                    )
                )
                continue
            if isinstance(result, BaseException):
                self.repository.update_tool_call(
                    invocation.call_id,
                    status=ToolCallStatus.FAILED.value,
                    result={},
                    error_code=type(result).__name__,
                    error_message=str(result),
                    completed_at=utcnow_naive(),
                )
                self.repository.append_audit(
                    run_id=run_id,
                    audit_type="action_failed",
                    actor_user_id=actor.user_id,
                    payload={
                        "call_id": invocation.call_id,
                        "action_name": invocation.action_name,
                        "error_type": type(result).__name__,
                        "message": str(result),
                        "execution_mode": "parallel_query",
                    },
                )
                events.append(
                    self._emit(
                        run_id,
                        "tool_execution_failed",
                        {
                            "call_id": invocation.call_id,
                            "name": invocation.action_name,
                            "error_type": type(result).__name__,
                            "message": str(result),
                        },
                    )
                )
                continue

            contract = self.action_executor.ontology.get_action(invocation.action_name)
            self.repository.append_audit(
                run_id=run_id,
                audit_type="pre_action_passed",
                actor_user_id=actor.user_id,
                payload={
                    "call_id": invocation.call_id,
                    "action_name": invocation.action_name,
                    "risk_level": contract.risk_level if contract else "low",
                    "approval_required": False,
                    "planting_plan_id": scope.planting_plan_id,
                    "execution_mode": "parallel_query",
                },
            )
            self.repository.update_tool_call(
                invocation.call_id,
                status=ToolCallStatus.COMPLETED.value,
                result=result,
                error_code=None,
                error_message=None,
                completed_at=utcnow_naive(),
            )
            self.repository.append_audit(
                run_id=run_id,
                audit_type="action_completed",
                actor_user_id=actor.user_id,
                payload={
                    "call_id": invocation.call_id,
                    "action_name": invocation.action_name,
                    "planting_plan_id": scope.planting_plan_id,
                    "execution_mode": "parallel_query",
                },
            )
            events.append(
                self._emit(
                    run_id,
                    "tool_execution_completed",
                    {
                        "call_id": invocation.call_id,
                        "name": invocation.action_name,
                        "result": result,
                        "execution_mode": "parallel_query",
                    },
                )
            )
        return events

    def _reject_model_call(
        self,
        *,
        run_id: str,
        model_call: ToolCall,
        actor: RuntimeActor,
        code: str,
        message: str,
    ) -> list[AgentEventEnvelope]:
        contract = self.action_executor.ontology.get_action(model_call.name)
        tool_call = self.repository.create_tool_call(
            run_id=run_id,
            call_id=model_call.call_id,
            action_name=model_call.name,
            arguments=model_call.arguments,
            approval_required=bool(contract and contract.approval_required),
        )
        if tool_call.status in TERMINAL_TOOL_CALL_STATUSES:
            return []
        proposed = self._emit(
            run_id,
            "tool_call_proposed",
            {
                "call_id": tool_call.id,
                "name": tool_call.action_name,
                "arguments": tool_call.arguments,
            },
        )
        rejection = ActionRejected(message, code=code)
        self._reject_tool_call(tool_call.id, rejection, actor)
        rejected = self._emit(
            run_id,
            "tool_execution_rejected",
            {
                "call_id": tool_call.id,
                "name": tool_call.action_name,
                "code": code,
                "message": message,
            },
        )
        return [proposed, rejected]

    async def _execute_persisted_tool_call(
        self,
        run_id: str,
        call_id: str,
        *,
        deadline: float,
    ) -> AsyncIterator[AgentEventEnvelope]:
        self._ensure_execution_time(deadline)
        run = self.repository.get_run(run_id)
        tool_call = self.repository.get_tool_call(call_id)
        if run is None or tool_call is None:
            raise RuntimeRejected("Agent action persistence is incomplete.", code="tool_state_incomplete")
        if tool_call.run_id != run_id:
            raise RuntimeRejected("Agent tool call belongs to a different run.", code="tool_run_mismatch")
        if tool_call.status in TERMINAL_TOOL_CALL_STATUSES:
            return
        session = self.repository.get_session(run.session_id)
        if session is None:
            raise RuntimeRejected(f"Agent session {run.session_id} does not exist.", code="session_not_found")
        actor = self.context_builder.resolve_actor(session.user_id, session.selected_role)
        snapshot = self.context_builder.load_snapshot(session.planting_plan_id)
        invocation = ActionInvocation(
            run_id=run_id,
            call_id=tool_call.id,
            action_name=tool_call.action_name,
            arguments=dict(tool_call.arguments or {}),
            actor=actor,
            scope=snapshot.scope,
        )

        if tool_call.approval_required:
            approval = self.repository.get_approval_by_tool_call(call_id)
            if approval is None or approval.status != ApprovalStatus.APPROVED.value:
                raise ActionRejected(
                    "This action requires an approved approval request before execution.",
                    code="approval_required",
                )

        # Approval does not freeze business state. Validate again immediately
        # before the side effect so stale task/review state cannot slip through.
        self.action_executor.validate(invocation)
        self.repository.update_tool_call(
            call_id,
            status=ToolCallStatus.RUNNING.value,
            started_at=utcnow_naive(),
        )
        yield self._emit(
            run_id,
            "tool_execution_started",
            {"call_id": call_id, "name": tool_call.action_name},
        )
        contract = self.action_executor.ontology.get_action(tool_call.action_name)
        try:
            with self.repository.begin_action_transaction():
                result = self.action_executor.execute(invocation)
        except ActionRejected as exc:
            self._reject_tool_call(call_id, exc, actor)
            yield self._emit(
                run_id,
                "tool_execution_rejected",
                {
                    "call_id": call_id,
                    "name": tool_call.action_name,
                    "code": exc.code,
                    "message": exc.message,
                },
            )
            return
        except Exception as exc:
            outcome_unknown = bool(contract and contract.side_effect)
            status = ToolCallStatus.UNKNOWN.value if outcome_unknown else ToolCallStatus.FAILED.value
            error_code = "action_outcome_unknown" if outcome_unknown else type(exc).__name__
            error_message = str(exc)
            result_payload = {"outcome": "unknown", "retry_allowed": False} if outcome_unknown else {}
            self.repository.update_tool_call(
                call_id,
                status=status,
                result=result_payload,
                error_code=error_code,
                error_message=error_message,
                completed_at=utcnow_naive(),
            )
            self.repository.append_audit(
                run_id=run_id,
                audit_type="action_outcome_unknown" if outcome_unknown else "action_failed",
                actor_user_id=actor.user_id,
                payload={
                    "call_id": call_id,
                    "action_name": tool_call.action_name,
                    "error_type": type(exc).__name__,
                    "message": error_message,
                    "status": status,
                    "retry_allowed": not outcome_unknown,
                },
            )
            yield self._emit(
                run_id,
                "tool_execution_failed",
                {
                    "call_id": call_id,
                    "name": tool_call.action_name,
                    "status": status,
                    "error_code": error_code,
                    "message": error_message,
                    "result": result_payload,
                },
            )
            return

        self.repository.update_tool_call(
            call_id,
            status=ToolCallStatus.COMPLETED.value,
            result=result,
            error_code=None,
            error_message=None,
            completed_at=utcnow_naive(),
        )
        self.repository.append_audit(
            run_id=run_id,
            audit_type="action_completed",
            actor_user_id=actor.user_id,
            payload={
                "call_id": call_id,
                "action_name": tool_call.action_name,
                "planting_plan_id": session.planting_plan_id,
            },
        )
        yield self._emit(
            run_id,
            "tool_execution_completed",
            {"call_id": call_id, "name": tool_call.action_name, "result": result},
        )
        self._ensure_execution_time(deadline)

    def _has_unknown_side_effect(self, run_id: str) -> bool:
        for result in self.repository.list_tool_results(run_id):
            if result["status"] != ToolCallStatus.UNKNOWN.value:
                continue
            contract = self.action_executor.ontology.get_action(result["action_name"])
            if contract is not None and contract.side_effect:
                return True
        return False

    def _reject_tool_call(self, call_id: str, exc: ActionRejected, actor: RuntimeActor) -> None:
        tool_call = self.repository.get_tool_call(call_id)
        if tool_call is None:
            return
        self.repository.update_tool_call(
            call_id,
            status=ToolCallStatus.REJECTED.value,
            result={"code": exc.code, "message": exc.message},
            error_code=exc.code,
            error_message=exc.message,
            completed_at=utcnow_naive(),
        )
        self.repository.append_audit(
            run_id=tool_call.run_id,
            audit_type="action_rejected",
            actor_user_id=actor.user_id,
            payload={
                "call_id": call_id,
                "action_name": tool_call.action_name,
                "code": exc.code,
                "message": exc.message,
            },
        )

    async def _fail_run(self, run_id: str, exc: Exception) -> AsyncIterator[AgentEventEnvelope]:
        error_code = exc.code if isinstance(exc, RuntimeRejected) else type(exc).__name__
        message = exc.message if isinstance(exc, RuntimeRejected) else str(exc)
        details = exc.details if isinstance(exc, RuntimeRejected) else {}
        self.repository.update_run(
            run_id,
            status=RunStatus.FAILED.value,
            error_code=error_code,
            error_message=message,
            completed_at=utcnow_naive(),
        )
        self.repository.append_audit(
            run_id=run_id,
            audit_type="run_failed",
            actor_user_id=None,
            payload={"error_code": error_code, "message": message, "details": details},
        )
        yield self._emit(
            run_id,
            "run_failed",
            {"error_code": error_code, "message": message, "details": details},
        )

    def _new_execution_deadline(self) -> float:
        return time.monotonic() + self.budget_policy.execution_timeout_seconds

    def _remaining_execution_seconds(self, deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise self._execution_timeout_error()
        return remaining

    def _ensure_execution_time(self, deadline: float) -> None:
        self._remaining_execution_seconds(deadline)

    def _execution_timeout_error(self) -> RuntimeRejected:
        timeout = self.budget_policy.execution_timeout_seconds
        return RuntimeRejected(
            f"Agent run active execution exceeded {timeout:g} seconds.",
            code="run_execution_timeout",
            details={"execution_timeout_seconds": timeout, "approval_wait_excluded": True},
        )

    def _emit(self, run_id: str, event_type: str, payload: dict[str, Any]) -> AgentEventEnvelope:
        return self.repository.append_event(run_id, event_type, payload)
