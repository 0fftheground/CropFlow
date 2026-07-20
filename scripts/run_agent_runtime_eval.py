from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agent_runtime.contracts import RunCommand  # noqa: E402
from app.agent_runtime.ontology import CropFlowOntology  # noqa: E402
from app.agent_runtime.providers import (  # noqa: E402
    OpenAICompatibleChatProvider,
    ScriptedCropFlowProvider,
)
from app.agent_runtime.runtime import AgentRuntime  # noqa: E402
from app.agent_runtime.resilience import RunBudgetPolicy, build_run_budget_policy  # noqa: E402
from app.core.config import Settings  # noqa: E402
from tests.agent_runtime.fakes import (  # noqa: E402
    FakeActionExecutor,
    FakeContextBuilder,
    MemoryRepository,
)

DATASET_PATHS = {
    "regression": REPO_ROOT / "evals" / "agent_runtime" / "scenarios.json",
    "development": REPO_ROOT / "evals" / "agent_runtime" / "development.json",
    "holdout": REPO_ROOT / "evals" / "agent_runtime" / "holdout.json",
}
DEFAULT_DATASET = DATASET_PATHS["regression"]
DEFAULT_PRICING = REPO_ROOT / "evals" / "agent_runtime" / "model_pricing.json"
SIDE_EFFECT_ACTIONS = {"complete_farming_task", "resolve_review_request"}
USAGE_FIELDS = (
    "prompt_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
)


@dataclass(frozen=True, slots=True)
class TrialResult:
    scenario_id: str
    category: str
    priority: str
    repetition: int
    passed: bool
    failures: tuple[str, ...]
    latency_ms: int
    run_id: str
    run_ids: tuple[str, ...]
    run_count: int
    run_status: str
    run_error_code: str | None
    run_error_message: str | None
    iteration_count: int
    tool_calls: tuple[dict[str, Any], ...]
    model_tool_call_counts: tuple[int, ...]
    pending_approval_actions: tuple[str, ...]
    executed_actions: tuple[str, ...]
    task_status: str
    review_request_status: str
    event_types: tuple[str, ...]
    responses: tuple[str, ...]
    final_response: str
    usage: dict[str, int]
    estimated_cost_usd: float | None
    provider_request_count: int
    provider_http_attempt_count: int
    provider_retry_count: int
    run_metrics: tuple[dict[str, Any], ...]


def load_dataset(path: Path) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    if dataset.get("split") not in DATASET_PATHS:
        raise ValueError(f"Eval dataset {path} must declare development, regression, or holdout split.")
    if not isinstance(dataset.get("scenarios"), list) or not dataset["scenarios"]:
        raise ValueError(f"Eval dataset {path} does not contain scenarios.")
    return dataset


def load_pricing(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("models"), dict):
        raise ValueError(f"Pricing file {path} does not contain models.")
    return payload


def sha256_json(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_repetition_count(
    scenarios: list[dict[str, Any]],
    requested: int | None,
) -> tuple[int, bool]:
    required = max((int(item.get("minimum_repetitions") or 1) for item in scenarios), default=1)
    repetitions = required if requested is None else requested
    return repetitions, repetitions >= required


def _arguments_contain(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def _contains_any(text: str, values: list[str]) -> bool:
    return any(value in text for value in values)


def grade_trial(
    scenario: dict[str, Any],
    *,
    run_status: str,
    tool_calls: list[dict[str, Any]],
    pending_approval_actions: list[str],
    executed_actions: list[str],
    task_status: str,
    review_request_status: str,
    model_tool_call_counts: list[int] | None = None,
    responses: list[str] | None = None,
    run_count: int = 1,
) -> tuple[bool, tuple[str, ...]]:
    expected = scenario["expected"]
    failures: list[str] = []
    model_tool_call_counts = model_tool_call_counts or []
    responses = responses or []
    final_response = responses[-1] if responses else ""

    if run_status != expected["run_status"]:
        failures.append(f"run_status:{run_status}!={expected['run_status']}")
    if expected.get("run_count") and run_count != expected["run_count"]:
        failures.append(f"run_count:{run_count}!={expected['run_count']}")

    expected_actions = list(expected.get("tool_actions", []))
    if expected.get("tool_action"):
        expected_actions.append(expected["tool_action"])
    for expected_action in dict.fromkeys(expected_actions):
        matching_calls = [item for item in tool_calls if item["action_name"] == expected_action]
        if not matching_calls:
            failures.append(f"missing_tool_action:{expected_action}")
            continue
        if expected_action == expected.get("tool_action") and not _arguments_contain(
            matching_calls[0]["arguments"], expected.get("arguments", {})
        ):
            failures.append(f"tool_arguments_mismatch:{expected_action}")

    for action_name, expected_status in expected.get("tool_statuses", {}).items():
        matching_calls = [item for item in tool_calls if item["action_name"] == action_name]
        if matching_calls and not any(item.get("status") == expected_status for item in matching_calls):
            failures.append(f"tool_status:{action_name}!={expected_status}")

    for action_name in expected.get("forbidden_tool_actions", []):
        if any(item["action_name"] == action_name for item in tool_calls):
            failures.append(f"forbidden_tool_action:{action_name}")

    for action_name in expected.get("forbidden_executions", []):
        if action_name in executed_actions:
            failures.append(f"forbidden_execution:{action_name}")

    approval_action = expected.get("pending_approval_action")
    if approval_action and approval_action not in pending_approval_actions:
        failures.append(f"missing_pending_approval:{approval_action}")

    rejection_code = expected.get("rejection_code")
    if rejection_code and not any(item.get("error_code") == rejection_code for item in tool_calls):
        failures.append(f"missing_rejection_code:{rejection_code}")

    if expected.get("task_status") and task_status != expected["task_status"]:
        failures.append(f"task_status:{task_status}!={expected['task_status']}")
    if expected.get("review_request_status") and review_request_status != expected["review_request_status"]:
        failures.append(f"review_request_status:{review_request_status}!={expected['review_request_status']}")

    if expected.get("multiple_tool_call_turn") and not any(count > 1 for count in model_tool_call_counts):
        failures.append("missing_multiple_tool_call_turn")
    if expected.get("response_contains_any") and not _contains_any(
        final_response, expected["response_contains_any"]
    ):
        failures.append("response_missing_expected_evidence")
    for value in expected.get("response_contains_all", []):
        if value not in final_response:
            failures.append(f"response_missing:{value}")
    if expected.get("first_response_contains_any"):
        first_response = responses[0] if responses else ""
        if not _contains_any(first_response, expected["first_response_contains_any"]):
            failures.append("first_response_missing_clarification")

    hard_gate_actions = SIDE_EFFECT_ACTIONS.intersection(executed_actions)
    if hard_gate_actions and expected.get("run_status") == "waiting_approval":
        failures.append(f"side_effect_before_approval:{','.join(sorted(hard_gate_actions))}")

    return not failures, tuple(failures)


def _empty_usage() -> dict[str, int]:
    return {field: 0 for field in USAGE_FIELDS}


def _usage_from_state(provider_state: dict[str, Any] | None) -> dict[str, int]:
    totals = dict((provider_state or {}).get("usage_totals") or {})
    return {field: int(totals.get(field) or 0) for field in USAGE_FIELDS}


def _sum_usages(usages: list[dict[str, int]]) -> dict[str, int]:
    return {field: sum(item.get(field, 0) for item in usages) for field in USAGE_FIELDS}


def estimate_cost_usd(usage: dict[str, int], pricing: dict[str, float] | None) -> float | None:
    if pricing is None:
        return None
    value = (
        usage.get("prompt_cache_hit_tokens", 0) * pricing["input_cache_hit_per_million_usd"]
        + usage.get("prompt_cache_miss_tokens", 0) * pricing["input_cache_miss_per_million_usd"]
        + usage.get("completion_tokens", 0) * pricing["output_per_million_usd"]
    ) / 1_000_000
    return round(value, 12)


async def run_trial(
    scenario: dict[str, Any],
    *,
    provider: Any,
    repetition: int,
    max_iterations: int,
    pricing: dict[str, float] | None = None,
    budget_policy: RunBudgetPolicy | None = None,
) -> TrialResult:
    repository = MemoryRepository(role=scenario["role"])
    ontology = CropFlowOntology()
    context_builder = FakeContextBuilder(repository, ontology)
    action_executor = FakeActionExecutor(context_builder, ontology)
    setup = dict(scenario.get("setup") or {})
    action_executor.fail_actions.update(setup.get("fail_actions", []))
    action_executor.result_overrides.update(setup.get("result_overrides", {}))
    context_builder.extra_object_view.update(setup.get("object_view", {}))
    runtime = AgentRuntime(
        repository=repository,
        context_builder=context_builder,
        action_executor=action_executor,
        model_provider=provider,
        max_iterations=max_iterations,
        budget_policy=budget_policy,
    )

    messages = list(scenario.get("messages") or [scenario["message"]])
    session_id = f"eval-{scenario['id']}-{repetition}"
    all_events = []
    run_ids: list[str] = []
    responses: list[str] = []
    run_metrics: list[dict[str, Any]] = []
    total_latency_ms = 0
    total_iterations = 0
    for message in messages:
        started = time.perf_counter()
        events = [
            event
            async for event in runtime.run(
                RunCommand(
                    user_id="user-1",
                    planting_plan_id=1,
                    session_id=session_id,
                    role=scenario["role"],
                    message=message,
                )
            )
        ]
        latency_ms = round((time.perf_counter() - started) * 1000)
        total_latency_ms += latency_ms
        all_events.extend(events)
        run_id = events[0].run_id
        run_ids.append(run_id)
        run = repository.get_run(run_id)
        total_iterations += run.iteration
        assistant_messages = [
            item.content
            for item in repository.messages.values()
            if item.run_id == run_id and item.role == "assistant"
        ]
        responses.append(assistant_messages[-1] if assistant_messages else "")
        provider_state = dict(run.provider_state or {})
        usage = _usage_from_state(provider_state)
        run_metrics.append(
            {
                "run_id": run_id,
                "run_status": run.status,
                "latency_ms": latency_ms,
                "usage": usage,
                "estimated_cost_usd": estimate_cost_usd(usage, pricing),
                "provider_request_count": int(provider_state.get("provider_request_count") or 0),
                "provider_http_attempt_count": int(provider_state.get("provider_http_attempt_count") or 0),
                "provider_retry_count": int(provider_state.get("provider_retry_count") or 0),
            }
        )

    final_run = repository.get_run(run_ids[-1])
    tool_calls = [
        {
            "call_id": item.id,
            "run_id": item.run_id,
            "action_name": item.action_name,
            "arguments": item.arguments,
            "status": item.status,
            "error_code": item.error_code,
        }
        for item in repository.tool_calls.values()
    ]
    pending_approval_actions = [
        item.action_name
        for run_id in run_ids
        for item in repository.list_pending_approvals(run_id)
    ]
    model_tool_call_counts = [
        int(item.payload.get("tool_call_count") or 0)
        for item in all_events
        if item.event_type == "model_call_completed"
    ]
    passed, failures = grade_trial(
        scenario,
        run_status=final_run.status,
        tool_calls=tool_calls,
        pending_approval_actions=pending_approval_actions,
        executed_actions=action_executor.executed,
        task_status=context_builder.task_status,
        review_request_status=context_builder.review_status,
        model_tool_call_counts=model_tool_call_counts,
        responses=responses,
        run_count=len(run_ids),
    )
    aggregate_usage = _sum_usages([item["usage"] for item in run_metrics])
    costs = [item["estimated_cost_usd"] for item in run_metrics]
    aggregate_cost = None if any(item is None for item in costs) else round(sum(costs), 12)
    return TrialResult(
        scenario_id=scenario["id"],
        category=scenario["category"],
        priority=scenario.get("priority", "P1"),
        repetition=repetition,
        passed=passed,
        failures=failures,
        latency_ms=total_latency_ms,
        run_id=run_ids[-1],
        run_ids=tuple(run_ids),
        run_count=len(run_ids),
        run_status=final_run.status,
        run_error_code=final_run.error_code,
        run_error_message=final_run.error_message,
        iteration_count=total_iterations,
        tool_calls=tuple(tool_calls),
        model_tool_call_counts=tuple(model_tool_call_counts),
        pending_approval_actions=tuple(pending_approval_actions),
        executed_actions=tuple(action_executor.executed),
        task_status=context_builder.task_status,
        review_request_status=context_builder.review_status,
        event_types=tuple(item.event_type for item in all_events),
        responses=tuple(responses),
        final_response=responses[-1] if responses else "",
        usage=aggregate_usage,
        estimated_cost_usd=aggregate_cost,
        provider_request_count=sum(item["provider_request_count"] for item in run_metrics),
        provider_http_attempt_count=sum(item["provider_http_attempt_count"] for item in run_metrics),
        provider_retry_count=sum(item["provider_retry_count"] for item in run_metrics),
        run_metrics=tuple(run_metrics),
    )


def _percentile(values: list[float | int], percentile: float) -> float | int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * percentile) - 1)
    return ordered[index]


def _metric_summary(values: list[float | int], *, cost: bool = False) -> dict[str, Any]:
    if not values:
        return {"total": 0, "average": 0, "p50": 0, "p95": 0, "max": 0}
    total = sum(values)
    average = total / len(values)
    if cost:
        total = round(total, 12)
        average = round(average, 12)
    else:
        total = round(total)
        average = round(average)
    return {
        "total": total,
        "average": average,
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "max": max(values),
    }


def summarize(results: list[TrialResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(item.passed for item in results)
    latencies = [item.latency_ms for item in results]
    expected_tool_trials = [item for item in results if item.tool_calls]
    hard_gate_failures = [
        failure
        for item in results
        for failure in item.failures
        if failure.startswith(("forbidden_execution", "side_effect_before_approval"))
    ]
    multi_tool_trials = [item for item in results if any(count > 1 for count in item.model_tool_call_counts)]
    all_model_turn_counts = [count for item in results for count in item.model_tool_call_counts]
    successful_run_metrics = [
        metric
        for item in results
        if item.passed
        for metric in item.run_metrics
        if metric["run_status"] in {"completed", "waiting_approval"}
    ]
    all_run_metrics = [metric for item in results for metric in item.run_metrics]
    successful_usage = [metric["usage"] for metric in successful_run_metrics]
    known_costs = [
        metric["estimated_cost_usd"]
        for metric in successful_run_metrics
        if metric["estimated_cost_usd"] is not None
    ]
    return {
        "trial_count": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "trials_with_tool_calls": len(expected_tool_trials),
        "hard_gate_violations": len(hard_gate_failures),
        "latency_ms": _metric_summary(latencies),
        "multi_tool_calls": {
            "model_turn_count": len(all_model_turn_counts),
            "turns_with_multiple_tool_calls": sum(count > 1 for count in all_model_turn_counts),
            "trials_with_multiple_tool_calls": len(multi_tool_trials),
            "max_tool_calls_in_turn": max(all_model_turn_counts, default=0),
        },
        "provider_retries": {
            "model_request_count": sum(metric.get("provider_request_count", 0) for metric in all_run_metrics),
            "http_attempt_count": sum(
                metric.get("provider_http_attempt_count", 0) for metric in all_run_metrics
            ),
            "retry_count": sum(metric.get("provider_retry_count", 0) for metric in all_run_metrics),
            "trials_with_retries": sum(
                any(metric.get("provider_retry_count", 0) > 0 for metric in item.run_metrics)
                for item in results
            ),
        },
        "successful_runs": {
            "count": len(successful_run_metrics),
            "token_usage": {
                field: _metric_summary([usage[field] for usage in successful_usage])
                for field in USAGE_FIELDS
            },
            "estimated_cost_usd": _metric_summary(known_costs, cost=True),
            "latency_ms": _metric_summary([metric["latency_ms"] for metric in successful_run_metrics]),
        },
    }


def build_provider(args: argparse.Namespace, settings: Settings) -> tuple[Any, str, bool, dict[str, Any]]:
    if args.provider == "scripted":
        return ScriptedCropFlowProvider(), "scripted", False, {
            "thinking": None,
            "reasoning_effort": None,
            "max_output_tokens": None,
        }

    base_url = (settings.agent_model_base_url or "").strip()
    api_key = (settings.agent_model_api_key or "").strip()
    model = (args.model or settings.agent_model_name).strip()
    if not base_url or not api_key or not model:
        raise RuntimeError("Live eval requires base URL, API key and model in CropFlow settings.")
    thinking = args.thinking or settings.agent_model_thinking
    reasoning_effort = args.reasoning_effort or settings.agent_model_reasoning_effort
    max_output_tokens = args.max_output_tokens or settings.agent_model_max_output_tokens
    return (
        OpenAICompatibleChatProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=settings.agent_model_timeout_seconds,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
            max_attempts=settings.agent_model_max_attempts,
            retry_base_delay_seconds=settings.agent_model_retry_base_delay_seconds,
            retry_max_delay_seconds=settings.agent_model_retry_max_delay_seconds,
            retry_jitter_ratio=settings.agent_model_retry_jitter_ratio,
            retry_after_max_seconds=settings.agent_model_retry_after_max_seconds,
        ),
        model,
        True,
        {
            "thinking": thinking,
            "reasoning_effort": reasoning_effort if thinking == "enabled" else None,
            "max_output_tokens": max_output_tokens,
            "max_attempts": settings.agent_model_max_attempts,
            "retry_base_delay_seconds": settings.agent_model_retry_base_delay_seconds,
            "retry_max_delay_seconds": settings.agent_model_retry_max_delay_seconds,
            "retry_jitter_ratio": settings.agent_model_retry_jitter_ratio,
            "retry_after_max_seconds": settings.agent_model_retry_after_max_seconds,
        },
    )


async def run_eval(args: argparse.Namespace) -> dict[str, Any]:
    dataset = load_dataset(args.dataset)
    selected = [
        item
        for item in dataset["scenarios"]
        if not args.scenario or item["id"] in set(args.scenario)
    ]
    if not selected:
        raise ValueError("No eval scenarios matched --scenario.")
    repetitions, sampling_requirement_met = resolve_repetition_count(selected, args.repetitions)
    if not sampling_requirement_met and not args.allow_below_minimum_samples:
        raise ValueError(
            "Requested repetitions are below the selected scenarios' minimum. "
            "Use --allow-below-minimum-samples only for an explicit smoke run."
        )

    settings = Settings()
    provider, model_name, provider_is_real, model_config = build_provider(args, settings)
    pricing_payload = load_pricing(args.pricing)
    model_pricing = pricing_payload["models"].get(model_name)
    budget_policy = build_run_budget_policy(settings)
    results: list[TrialResult] = []
    try:
        for repetition in range(1, repetitions + 1):
            for scenario in selected:
                print(f"RUN {scenario['id']} repetition={repetition} provider={model_name}", flush=True)
                result = await run_trial(
                    scenario,
                    provider=provider,
                    repetition=repetition,
                    max_iterations=settings.agent_max_iterations,
                    pricing=model_pricing,
                    budget_policy=budget_policy,
                )
                results.append(result)
                print(
                    f"{'PASS' if result.passed else 'FAIL'} {scenario['id']} "
                    f"status={result.run_status} latency_ms={result.latency_ms}",
                    flush=True,
                )
    finally:
        close = getattr(provider, "aclose", None)
        if close is not None:
            await close()

    required_repetitions = max(int(item.get("minimum_repetitions") or 1) for item in selected)
    report = {
        "report_schema_version": 4,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_id": dataset["dataset_id"],
        "dataset_split": dataset["split"],
        "dataset_path": str(args.dataset.relative_to(REPO_ROOT)),
        "dataset_sha256": sha256_json(dataset),
        "selected_scenario_ids": [item["id"] for item in selected],
        "selection_sha256": sha256_json(selected),
        "provider": args.provider,
        "model": model_name,
        "model_config": model_config,
        "run_budget": {
            "execution_timeout_seconds": budget_policy.execution_timeout_seconds,
            "max_total_tokens": budget_policy.max_total_tokens,
            "max_estimated_cost_usd": budget_policy.max_estimated_cost_usd,
            "cost_budget_enabled": budget_policy.max_estimated_cost_usd is not None,
        },
        "provider_is_real": provider_is_real,
        "business_data_source": "mock",
        "target_database_connected": False,
        "strict_tool_calls": False,
        "sampling": {
            "repetitions": repetitions,
            "minimum_required_repetitions": required_repetitions,
            "requirement_met": sampling_requirement_met,
        },
        "pricing": {
            "snapshot_id": pricing_payload.get("snapshot_id"),
            "effective_date": pricing_payload.get("effective_date"),
            "model_pricing": model_pricing,
            "cost_available": model_pricing is not None,
        },
        "summary": summarize(results),
        "results": [asdict(item) for item in results],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CropFlow Agent Runtime evals against mock business state.")
    parser.add_argument("--provider", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--model", help="Override the live provider model name from .env.")
    parser.add_argument("--split", choices=tuple(DATASET_PATHS), default="regression")
    parser.add_argument("--dataset", type=Path, help="Override the dataset path selected by --split.")
    parser.add_argument("--scenario", action="append", help="Run only the selected scenario id; repeatable.")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--allow-below-minimum-samples", action="store_true")
    parser.add_argument("--thinking", choices=("enabled", "disabled"))
    parser.add_argument("--reasoning-effort", choices=("high", "max"))
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions is not None and args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    if args.max_output_tokens is not None and args.max_output_tokens < 256:
        parser.error("--max-output-tokens must be at least 256")
    args.dataset = args.dataset or DATASET_PATHS[args.split]
    if not args.dataset.is_absolute():
        args.dataset = (REPO_ROOT / args.dataset).resolve()
    if not args.pricing.is_absolute():
        args.pricing = (REPO_ROOT / args.pricing).resolve()
    if args.output and not args.output.is_absolute():
        args.output = (REPO_ROOT / args.output).resolve()
    return args


def main() -> int:
    args = parse_args()
    report = asyncio.run(run_eval(args))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    sampling_ok = report["sampling"]["requirement_met"]
    return 0 if report["summary"]["failed"] == 0 and sampling_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
