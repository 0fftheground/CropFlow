from __future__ import annotations

import asyncio

import pytest

from app.agent_runtime.contracts import ModelTurnResult, RunCommand, ToolCall
from app.agent_runtime.ontology import CropFlowOntology
from app.agent_runtime.runtime import AgentRuntime
from app.agent_runtime.resilience import ModelPricing, RunBudgetPolicy
from tests.agent_runtime.fakes import FakeActionExecutor, FakeContextBuilder, MemoryRepository, SequenceProvider


def build_runtime(
    *,
    role: str,
    turns: list[ModelTurnResult],
    budget_policy: RunBudgetPolicy | None = None,
    provider=None,
):
    repository = MemoryRepository(role=role)
    ontology = CropFlowOntology()
    context_builder = FakeContextBuilder(repository, ontology)
    action_executor = FakeActionExecutor(context_builder, ontology)
    provider = provider or SequenceProvider(turns)
    runtime = AgentRuntime(
        repository=repository,
        context_builder=context_builder,
        action_executor=action_executor,
        model_provider=provider,
        max_iterations=5,
        budget_policy=budget_policy,
    )
    return runtime, repository, context_builder, action_executor, provider


def test_review_action_schema_explains_empty_decision_payload() -> None:
    action = CropFlowOntology().get_action("resolve_review_request")

    assert action is not None
    description = action.input_schema["properties"]["decision_payload"]["description"]
    assert "空对象" in description


@pytest.mark.asyncio
async def test_read_action_executes_and_tool_result_is_injected_into_next_turn() -> None:
    runtime, repository, _, executor, provider = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                text="读取计划",
                tool_calls=(ToolCall(call_id="call-view", name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="计划读取完成"),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看计划", session_id="session-1")
        )
    ]

    assert repository.get_run(events[0].run_id).status == "completed"
    assert executor.executed == ["view_plan_context"]
    assert provider.requests[1].tool_results[0]["call_id"] == "call-view"
    assert [item.event_type for item in events][-1] == "run_completed"


@pytest.mark.asyncio
async def test_side_effect_waits_for_approval_then_rechecks_and_executes() -> None:
    runtime, repository, context, executor, _ = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                text="申请完成任务",
                tool_calls=(
                    ToolCall(
                        call_id="call-complete",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="任务已经完成"),
        ],
    )

    first_events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务 10", session_id="session-1")
        )
    ]
    run_id = first_events[0].run_id
    approval = repository.list_pending_approvals(run_id)[0]

    assert repository.get_run(run_id).status == "waiting_approval"
    assert executor.executed == []
    assert context.task_status == "pending"

    resumed_events = [
        event
        async for event in runtime.decide_approval(
            approval_id=approval.id,
            decision="approved",
            decided_by="user-1",
            decision_note="确认执行",
        )
    ]

    assert repository.get_run(run_id).status == "completed"
    assert context.task_status == "completed"
    assert executor.executed == ["complete_farming_task"]
    assert any(item.event_type == "approval_decided" for item in resumed_events)
    assert any(item.event_type == "tool_execution_completed" for item in resumed_events)


@pytest.mark.asyncio
async def test_approval_does_not_bypass_fresh_business_state_check() -> None:
    runtime, repository, context, executor, provider = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-stale",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="任务状态已变化，因此未重复执行"),
        ],
    )
    first_events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务 10", session_id="session-1")
        )
    ]
    run_id = first_events[0].run_id
    approval = repository.list_pending_approvals(run_id)[0]
    context.task_status = "completed"

    resumed_events = [
        event
        async for event in runtime.decide_approval(
            approval_id=approval.id,
            decision="approved",
            decided_by="user-1",
        )
    ]

    assert executor.executed == []
    assert repository.get_tool_call("call-stale").status == "rejected"
    assert repository.get_run(run_id).status == "completed"
    assert provider.requests[-1].tool_results[0]["error_code"] == "action_not_available"
    assert any(item.event_type == "tool_execution_rejected" for item in resumed_events)


@pytest.mark.asyncio
async def test_model_cannot_use_operator_action_for_observer() -> None:
    runtime, repository, _, executor, _ = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-forbidden",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="当前角色没有完成任务的权限"),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务 10", session_id="session-1")
        )
    ]

    assert executor.executed == []
    assert repository.get_tool_call("call-forbidden").status == "rejected"
    assert repository.get_run(events[0].run_id).status == "completed"


@pytest.mark.asyncio
async def test_repeated_terminal_tool_call_id_is_not_executed_twice() -> None:
    runtime, repository, _, executor, _ = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(ToolCall(call_id="call-repeat", name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(
                tool_calls=(ToolCall(call_id="call-repeat", name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="上下文读取完成"),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看计划", session_id="session-1")
        )
    ]

    assert executor.executed == ["view_plan_context"]
    assert repository.get_tool_call("call-repeat").status == "completed"
    assert repository.get_run(events[0].run_id).status == "completed"


@pytest.mark.asyncio
async def test_independent_read_actions_execute_in_parallel_and_all_results_are_reinjected() -> None:
    runtime, repository, _, executor, provider = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(call_id="call-view", name="view_plan_context", arguments={}),
                    ToolCall(call_id="call-task", name="get_task_detail", arguments={"task_id": 10}),
                    ToolCall(
                        call_id="call-review",
                        name="get_review_request_detail",
                        arguments={"review_request_id": 20},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="查询完成"),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看全部详情", session_id="session-1")
        )
    ]

    assert repository.get_run(events[0].run_id).status == "completed"
    assert set(executor.executed) == {"view_plan_context", "get_task_detail", "get_review_request_detail"}
    assert executor.max_parallel_query_executions == 3
    assert [item["call_id"] for item in provider.requests[1].tool_results] == [
        "call-view",
        "call-task",
        "call-review",
    ]
    assert all(repository.get_tool_call(call_id).status == "completed" for call_id in (
        "call-view",
        "call-task",
        "call-review",
    ))


@pytest.mark.asyncio
async def test_mixed_query_and_side_effect_executes_queries_then_requires_write_replan() -> None:
    runtime, repository, context, executor, provider = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(call_id="call-task", name="get_task_detail", arguments={"task_id": 10}),
                    ToolCall(
                        call_id="call-mixed-write",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-replanned-write",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看并完成任务 10", session_id="session-1")
        )
    ]

    run_id = events[0].run_id
    assert repository.get_run(run_id).status == "waiting_approval"
    assert repository.get_tool_call("call-task").status == "completed"
    assert repository.get_tool_call("call-mixed-write").status == "rejected"
    assert repository.get_tool_call("call-mixed-write").error_code == "side_effect_requires_replan"
    assert repository.get_tool_call("call-replanned-write").status == "waiting_approval"
    assert [item["call_id"] for item in provider.requests[1].tool_results] == [
        "call-task",
        "call-mixed-write",
    ]
    assert executor.executed == ["get_task_detail"]
    assert context.task_status == "pending"


@pytest.mark.asyncio
async def test_multiple_side_effect_actions_only_prepare_first_and_reject_extras() -> None:
    runtime, repository, context, executor, _ = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-write-first",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                    ToolCall(
                        call_id="call-write-extra",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-19", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务 10", session_id="session-1")
        )
    ]

    run_id = events[0].run_id
    assert repository.get_run(run_id).status == "waiting_approval"
    assert repository.get_tool_call("call-write-first").status == "waiting_approval"
    assert repository.get_tool_call("call-write-extra").status == "rejected"
    assert repository.get_tool_call("call-write-extra").error_code == "serial_action_requires_replan"
    assert executor.executed == []
    assert context.task_status == "pending"


@pytest.mark.asyncio
async def test_parallel_query_batch_returns_partial_rejection_to_model() -> None:
    runtime, repository, _, executor, provider = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(call_id="call-view", name="view_plan_context", arguments={}),
                    ToolCall(call_id="call-out-of-scope", name="get_task_detail", arguments={"task_id": 999}),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="任务不在当前计划内"),
        ],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看任务 999", session_id="session-1")
        )
    ]

    assert repository.get_run(events[0].run_id).status == "completed"
    assert repository.get_tool_call("call-view").status == "completed"
    assert repository.get_tool_call("call-out-of-scope").status == "rejected"
    assert repository.get_tool_call("call-out-of-scope").error_code == "object_scope_mismatch"
    assert [item["status"] for item in provider.requests[1].tool_results] == ["completed", "rejected"]
    assert executor.max_parallel_query_executions == 2


@pytest.mark.asyncio
async def test_parallel_query_failure_is_reinjected_and_other_results_are_preserved() -> None:
    runtime, repository, _, executor, provider = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(call_id="call-view", name="view_plan_context", arguments={}),
                    ToolCall(call_id="call-failed-query", name="get_task_detail", arguments={"task_id": 10}),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="任务查询失败，但计划上下文读取成功"),
        ],
    )
    executor.fail_actions.add("get_task_detail")

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看计划和任务", session_id="session-1")
        )
    ]

    assert repository.get_run(events[0].run_id).status == "completed"
    assert repository.get_tool_call("call-view").status == "completed"
    assert repository.get_tool_call("call-failed-query").status == "failed"
    assert [item["status"] for item in provider.requests[1].tool_results] == ["completed", "failed"]
    assert provider.requests[1].tool_results[1]["error_code"] == "RuntimeError"
    assert "simulated get_task_detail failure" in provider.requests[1].tool_results[1]["error_message"]
    assert any(item.event_type == "tool_execution_failed" for item in events)


@pytest.mark.asyncio
async def test_approved_side_effect_failure_is_reinjected_as_unknown_outcome() -> None:
    runtime, repository, context, executor, provider = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-failed-write",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="动作结果不确定，需要人工核对后再处理"),
        ],
    )
    executor.fail_actions.add("complete_farming_task")

    first_events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务 10", session_id="session-1")
        )
    ]
    run_id = first_events[0].run_id
    approval = repository.list_pending_approvals(run_id)[0]

    resumed_events = [
        event
        async for event in runtime.decide_approval(
            approval_id=approval.id,
            decision="approved",
            decided_by="user-1",
        )
    ]

    tool_call = repository.get_tool_call("call-failed-write")
    assert tool_call.status == "unknown"
    assert tool_call.error_code == "action_outcome_unknown"
    assert tool_call.result == {"outcome": "unknown", "retry_allowed": False}
    assert repository.rollback_count == 1
    assert repository.get_run(run_id).status == "completed"
    assert context.task_status == "pending"
    assert provider.requests[-1].tool_results[0]["status"] == "unknown"
    assert provider.requests[-1].tool_results[0]["error_code"] == "action_outcome_unknown"
    assert any(item.event_type == "tool_execution_failed" for item in resumed_events)


@pytest.mark.asyncio
async def test_side_effect_is_not_automatically_retried_after_unknown_outcome() -> None:
    runtime, repository, _, executor, _ = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-unknown-write",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-unsafe-retry",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="已停止自动重试，等待人工核对"),
        ],
    )
    executor.fail_actions.add("complete_farming_task")

    first_events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务 10", session_id="session-1")
        )
    ]
    run_id = first_events[0].run_id
    approval = repository.list_pending_approvals(run_id)[0]

    await _collect(
        runtime.decide_approval(
            approval_id=approval.id,
            decision="approved",
            decided_by="user-1",
        )
    )

    assert repository.get_tool_call("call-unknown-write").status == "unknown"
    assert repository.get_tool_call("call-unsafe-retry").status == "rejected"
    assert repository.get_tool_call("call-unsafe-retry").error_code == "action_outcome_reconciliation_required"
    assert repository.list_pending_approvals(run_id) == []
    assert repository.get_run(run_id).status == "completed"


async def _collect(events):
    return [event async for event in events]


@pytest.mark.asyncio
async def test_truncated_model_output_fails_run_instead_of_completing_it() -> None:
    runtime, repository, _, _, _ = build_runtime(
        role="observer",
        turns=[ModelTurnResult(text="被截断的回答", finish_reason="length")],
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="分析计划", session_id="session-length")
        )
    ]

    run = repository.get_run(events[0].run_id)
    assert run.status == "failed"
    assert run.error_code == "model_output_truncated"
    assert not any(item.event_type == "message_completed" for item in events)


@pytest.mark.asyncio
async def test_token_budget_stops_tool_execution_after_model_usage_exceeds_limit() -> None:
    runtime, repository, _, executor, _ = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                tool_calls=(ToolCall(call_id="call-over-budget", name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
                provider_state={
                    "usage_totals": {
                        "prompt_tokens": 90,
                        "prompt_cache_hit_tokens": 0,
                        "prompt_cache_miss_tokens": 90,
                        "completion_tokens": 20,
                        "reasoning_tokens": 0,
                        "total_tokens": 110,
                    }
                },
            )
        ],
        budget_policy=RunBudgetPolicy(max_total_tokens=100),
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="查看计划", session_id="budget-token")
        )
    ]

    run = repository.get_run(events[0].run_id)
    assert run.status == "failed"
    assert run.error_code == "run_token_budget_exceeded"
    assert executor.executed == []
    assert repository.tool_calls == {}


@pytest.mark.asyncio
async def test_cost_budget_stops_run_using_provider_reported_usage() -> None:
    pricing = ModelPricing(
        input_cache_hit_per_million_usd=1,
        input_cache_miss_per_million_usd=2,
        output_per_million_usd=3,
    )
    runtime, repository, _, _, _ = build_runtime(
        role="observer",
        turns=[
            ModelTurnResult(
                text="完成",
                provider_state={
                    "usage_totals": {
                        "prompt_tokens": 1000,
                        "prompt_cache_hit_tokens": 0,
                        "prompt_cache_miss_tokens": 1000,
                        "completion_tokens": 1000,
                        "reasoning_tokens": 0,
                        "total_tokens": 2000,
                    }
                },
            )
        ],
        budget_policy=RunBudgetPolicy(
            max_total_tokens=None,
            max_estimated_cost_usd=0.004,
            pricing=pricing,
        ),
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="分析", session_id="budget-cost")
        )
    ]

    run = repository.get_run(events[0].run_id)
    assert run.status == "failed"
    assert run.error_code == "run_cost_budget_exceeded"
    assert run.provider_state["runtime_budget"]["estimated_cost_usd"] == pytest.approx(0.005)


@pytest.mark.asyncio
async def test_execution_timeout_fails_slow_model_call() -> None:
    class SlowProvider:
        name = "slow"

        async def complete_turn(self, request):
            await asyncio.sleep(0.02)
            return ModelTurnResult(text="too late")

    runtime, repository, _, _, _ = build_runtime(
        role="observer",
        turns=[],
        provider=SlowProvider(),
        budget_policy=RunBudgetPolicy(execution_timeout_seconds=0.001),
    )

    events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="分析", session_id="budget-time")
        )
    ]

    run = repository.get_run(events[0].run_id)
    assert run.status == "failed"
    assert run.error_code == "run_execution_timeout"


@pytest.mark.asyncio
async def test_approval_wait_does_not_consume_active_execution_timeout() -> None:
    runtime, repository, _, _, _ = build_runtime(
        role="operator",
        turns=[
            ModelTurnResult(
                tool_calls=(
                    ToolCall(
                        call_id="call-timeout-reset",
                        name="complete_farming_task",
                        arguments={"task_id": 10, "operation_date": "2026-07-18", "result_payload": {}},
                    ),
                ),
                finish_reason="tool_calls",
            ),
            ModelTurnResult(text="任务已经完成"),
        ],
        budget_policy=RunBudgetPolicy(execution_timeout_seconds=0.05),
    )
    first_events = [
        event
        async for event in runtime.run(
            RunCommand(user_id="user-1", planting_plan_id=1, message="完成任务", session_id="approval-timeout")
        )
    ]
    run_id = first_events[0].run_id
    approval = repository.list_pending_approvals(run_id)[0]
    await asyncio.sleep(0.06)

    resumed_events = [
        event
        async for event in runtime.decide_approval(
            approval_id=approval.id,
            decision="approved",
            decided_by="user-1",
        )
    ]

    assert repository.get_run(run_id).status == "completed"
    assert any(item.event_type == "run_completed" for item in resumed_events)
