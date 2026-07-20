from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent_runtime.contracts import RuntimeRejected


@dataclass(frozen=True, slots=True)
class ModelPricing:
    input_cache_hit_per_million_usd: float
    input_cache_miss_per_million_usd: float
    output_per_million_usd: float

    def __post_init__(self) -> None:
        if min(
            self.input_cache_hit_per_million_usd,
            self.input_cache_miss_per_million_usd,
            self.output_per_million_usd,
        ) < 0:
            raise ValueError("Model pricing values cannot be negative.")


@dataclass(frozen=True, slots=True)
class RunBudgetPolicy:
    execution_timeout_seconds: float = 180.0
    max_total_tokens: int | None = 16_000
    max_estimated_cost_usd: float | None = None
    pricing: ModelPricing | None = None

    def __post_init__(self) -> None:
        if self.execution_timeout_seconds <= 0:
            raise ValueError("Run execution timeout must be greater than zero.")
        if self.max_total_tokens is not None and self.max_total_tokens <= 0:
            raise ValueError("Run max total tokens must be greater than zero when configured.")
        if self.max_estimated_cost_usd is not None and self.max_estimated_cost_usd <= 0:
            raise ValueError("Run max estimated cost must be greater than zero when configured.")
        if self.max_estimated_cost_usd is not None and self.pricing is None:
            raise ValueError("Model pricing is required when a run cost budget is configured.")

    def snapshot(self, provider_state: dict[str, Any] | None) -> dict[str, Any]:
        state = dict(provider_state or {})
        usage = dict(state.get("usage_totals") or {})
        total_tokens = int(usage.get("total_tokens") or 0)
        estimated_cost = estimate_cost_usd(usage, self.pricing) if self.pricing else None
        return {
            "execution_timeout_seconds": self.execution_timeout_seconds,
            "total_tokens": total_tokens,
            "max_total_tokens": self.max_total_tokens,
            "remaining_tokens": (
                max(0, self.max_total_tokens - total_tokens)
                if self.max_total_tokens is not None
                else None
            ),
            "estimated_cost_usd": estimated_cost,
            "max_estimated_cost_usd": self.max_estimated_cost_usd,
            "remaining_estimated_cost_usd": (
                max(0.0, self.max_estimated_cost_usd - (estimated_cost or 0.0))
                if self.max_estimated_cost_usd is not None
                else None
            ),
        }

    def enforce(self, provider_state: dict[str, Any] | None, *, before_model_call: bool = False) -> dict[str, Any]:
        snapshot = self.snapshot(provider_state)
        total_tokens = snapshot["total_tokens"]
        max_tokens = snapshot["max_total_tokens"]
        token_exceeded = max_tokens is not None and (
            total_tokens > max_tokens or (before_model_call and total_tokens >= max_tokens)
        )
        if token_exceeded:
            raise RuntimeRejected(
                f"Agent run token budget exceeded: {total_tokens} / {max_tokens}.",
                code="run_token_budget_exceeded",
                details=snapshot,
            )

        estimated_cost = snapshot["estimated_cost_usd"]
        max_cost = snapshot["max_estimated_cost_usd"]
        cost_exceeded = max_cost is not None and estimated_cost is not None and (
            estimated_cost > max_cost or (before_model_call and estimated_cost >= max_cost)
        )
        if cost_exceeded:
            raise RuntimeRejected(
                f"Agent run estimated cost budget exceeded: ${estimated_cost:.12f} / ${max_cost:.12f}.",
                code="run_cost_budget_exceeded",
                details=snapshot,
            )
        return snapshot


def estimate_cost_usd(usage: dict[str, Any], pricing: ModelPricing | None) -> float | None:
    if pricing is None:
        return None
    cache_hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    if "prompt_cache_miss_tokens" in usage:
        cache_miss = int(usage.get("prompt_cache_miss_tokens") or 0)
    else:
        cache_miss = max(0, prompt_tokens - cache_hit)
    completion = int(usage.get("completion_tokens") or 0)
    cost = (
        cache_hit * pricing.input_cache_hit_per_million_usd
        + cache_miss * pricing.input_cache_miss_per_million_usd
        + completion * pricing.output_per_million_usd
    ) / 1_000_000
    return round(cost, 12)


def build_run_budget_policy(settings: Any) -> RunBudgetPolicy:
    price_values = (
        settings.agent_model_input_cache_hit_price_per_million_usd,
        settings.agent_model_input_cache_miss_price_per_million_usd,
        settings.agent_model_output_price_per_million_usd,
    )
    pricing = None
    if all(value is not None for value in price_values):
        pricing = ModelPricing(
            input_cache_hit_per_million_usd=price_values[0],
            input_cache_miss_per_million_usd=price_values[1],
            output_per_million_usd=price_values[2],
        )
    elif any(value is not None for value in price_values):
        raise RuntimeError("All three Agent model pricing fields must be configured together.")

    try:
        return RunBudgetPolicy(
            execution_timeout_seconds=settings.agent_run_execution_timeout_seconds,
            max_total_tokens=settings.agent_run_max_total_tokens,
            max_estimated_cost_usd=settings.agent_run_max_estimated_cost_usd,
            pricing=pricing,
        )
    except ValueError as exc:
        raise RuntimeError(f"Invalid Agent Runtime budget configuration: {exc}") from exc
