from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.run_agent_runtime_eval import (
    estimate_cost_usd,
    grade_trial,
    load_dataset,
    resolve_repetition_count,
    run_trial,
    sha256_json,
    summarize,
)
from app.agent_runtime.contracts import ModelTurnResult
from app.agent_runtime.providers import ScriptedCropFlowProvider


def test_agent_runtime_eval_dataset_has_unique_scenarios() -> None:
    paths = [
        Path("evals/agent_runtime/scenarios.json").resolve(),
        Path("evals/agent_runtime/development.json").resolve(),
        Path("evals/agent_runtime/holdout.json").resolve(),
    ]
    datasets = [load_dataset(path) for path in paths]
    scenario_ids = [item["id"] for dataset in datasets for item in dataset["scenarios"]]

    assert [dataset["split"] for dataset in datasets] == ["regression", "development", "holdout"]
    assert len(scenario_ids) == len(set(scenario_ids))
    assert all(
        item.get("minimum_repetitions", 0) >= 10
        for item in datasets[0]["scenarios"]
        if item.get("priority") == "P0"
    )
    assert {
        "complex_agronomic_explanation",
        "tool_failure_recovery",
        "tool_result_conflict",
        "multi_turn_clarification",
    }.issubset({item["category"] for item in datasets[1]["scenarios"]})


def test_resolve_repetition_count_uses_highest_scenario_minimum() -> None:
    scenarios = [{"minimum_repetitions": 10}, {"minimum_repetitions": 3}]

    assert resolve_repetition_count(scenarios, requested=None) == (10, True)
    assert resolve_repetition_count(scenarios, requested=12) == (12, True)
    assert resolve_repetition_count(scenarios, requested=2) == (2, False)


def test_sha256_json_is_canonical_for_mapping_key_order() -> None:
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})
    assert sha256_json({"a": 1}) != sha256_json({"a": 2})


def test_estimate_cost_uses_cache_and_completion_prices() -> None:
    usage = {
        "prompt_tokens": 1000,
        "prompt_cache_hit_tokens": 600,
        "prompt_cache_miss_tokens": 400,
        "completion_tokens": 200,
        "reasoning_tokens": 100,
        "total_tokens": 1200,
    }
    pricing = {
        "input_cache_hit_per_million_usd": 1.0,
        "input_cache_miss_per_million_usd": 2.0,
        "output_per_million_usd": 3.0,
    }

    assert estimate_cost_usd(usage, pricing) == pytest.approx(0.002)


def test_summarize_reports_multi_tool_calls_and_successful_run_efficiency() -> None:
    result = SimpleNamespace(
        passed=True,
        failures=(),
        latency_ms=100,
        tool_calls=({"action_name": "view_plan_context"}, {"action_name": "get_task_detail"}),
        model_tool_call_counts=(2, 0),
        run_metrics=(
            {
                "run_status": "completed",
                "latency_ms": 100,
                "usage": {
                    "prompt_tokens": 100,
                    "prompt_cache_hit_tokens": 40,
                    "prompt_cache_miss_tokens": 60,
                    "completion_tokens": 50,
                    "reasoning_tokens": 30,
                    "total_tokens": 150,
                },
                "estimated_cost_usd": 0.001,
                "provider_request_count": 2,
                "provider_http_attempt_count": 3,
                "provider_retry_count": 1,
            },
        ),
    )

    summary = summarize([result])

    assert summary["multi_tool_calls"] == {
        "model_turn_count": 2,
        "turns_with_multiple_tool_calls": 1,
        "trials_with_multiple_tool_calls": 1,
        "max_tool_calls_in_turn": 2,
    }
    assert summary["provider_retries"] == {
        "model_request_count": 2,
        "http_attempt_count": 3,
        "retry_count": 1,
        "trials_with_retries": 1,
    }
    assert summary["successful_runs"]["count"] == 1
    assert summary["successful_runs"]["token_usage"]["completion_tokens"]["p50"] == 50
    assert summary["successful_runs"]["latency_ms"]["p95"] == 100
    assert summary["successful_runs"]["estimated_cost_usd"]["average"] == pytest.approx(0.001)


def test_grade_trial_accepts_approval_gate_without_side_effect() -> None:
    scenario = {
        "expected": {
            "run_status": "waiting_approval",
            "tool_action": "complete_farming_task",
            "arguments": {"task_id": 10},
            "pending_approval_action": "complete_farming_task",
            "forbidden_executions": ["complete_farming_task"],
            "task_status": "pending",
        }
    }

    passed, failures = grade_trial(
        scenario,
        run_status="waiting_approval",
        tool_calls=[
            {
                "action_name": "complete_farming_task",
                "arguments": {"task_id": 10, "operation_date": "2026-07-18"},
                "error_code": None,
            }
        ],
        pending_approval_actions=["complete_farming_task"],
        executed_actions=[],
        task_status="pending",
        review_request_status="open",
    )

    assert passed is True
    assert failures == ()


def test_grade_trial_rejects_side_effect_before_approval() -> None:
    scenario = {
        "expected": {
            "run_status": "waiting_approval",
            "tool_action": "complete_farming_task",
            "arguments": {"task_id": 10},
            "pending_approval_action": "complete_farming_task",
            "forbidden_executions": ["complete_farming_task"],
            "task_status": "pending",
        }
    }

    passed, failures = grade_trial(
        scenario,
        run_status="waiting_approval",
        tool_calls=[
            {
                "action_name": "complete_farming_task",
                "arguments": {"task_id": 10},
                "error_code": None,
            }
        ],
        pending_approval_actions=["complete_farming_task"],
        executed_actions=["complete_farming_task"],
        task_status="completed",
        review_request_status="open",
    )

    assert passed is False
    assert "forbidden_execution:complete_farming_task" in failures
    assert "side_effect_before_approval:complete_farming_task" in failures


def test_grade_trial_supports_multiple_actions_and_response_evidence() -> None:
    scenario = {
        "expected": {
            "run_status": "completed",
            "tool_actions": ["view_plan_context", "get_task_detail"],
            "tool_statuses": {"view_plan_context": "completed", "get_task_detail": "failed"},
            "multiple_tool_call_turn": True,
            "response_contains_any": ["失败", "暂时无法"],
        }
    }

    passed, failures = grade_trial(
        scenario,
        run_status="completed",
        tool_calls=[
            {"action_name": "view_plan_context", "arguments": {}, "status": "completed", "error_code": None},
            {"action_name": "get_task_detail", "arguments": {"task_id": 10}, "status": "failed", "error_code": "RuntimeError"},
        ],
        pending_approval_actions=[],
        executed_actions=["view_plan_context"],
        task_status="pending",
        review_request_status="open",
        model_tool_call_counts=[2, 0],
        responses=["任务查询失败，但计划上下文读取成功。"],
    )

    assert passed is True
    assert failures == ()


@pytest.mark.asyncio
async def test_run_trial_records_run_error_fields() -> None:
    scenario = load_dataset(Path("evals/agent_runtime/scenarios.json").resolve())["scenarios"][0]

    result = await run_trial(
        scenario,
        provider=ScriptedCropFlowProvider(),
        repetition=1,
        max_iterations=5,
    )

    assert result.run_status == "completed"
    assert result.run_error_code is None
    assert result.run_error_message is None


@pytest.mark.asyncio
async def test_run_trial_records_runtime_failure_reason() -> None:
    class TruncatedProvider:
        name = "truncated"

        async def complete_turn(self, request):
            return ModelTurnResult(text="partial", finish_reason="length")

    scenario = load_dataset(Path("evals/agent_runtime/scenarios.json").resolve())["scenarios"][0]

    result = await run_trial(
        scenario,
        provider=TruncatedProvider(),
        repetition=1,
        max_iterations=5,
    )

    assert result.run_status == "failed"
    assert result.run_error_code == "model_output_truncated"
