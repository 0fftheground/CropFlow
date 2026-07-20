from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from app.agent_runtime.contracts import ModelRequest, RuntimeRejected
from app.agent_runtime.providers import OpenAICompatibleChatProvider, SYSTEM_PROMPT
from app.agent_runtime.resilience import build_run_budget_policy
from app.core.config import Settings


def test_settings_accept_deepseek_api_key_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret")

    settings = Settings(_env_file=None)

    assert settings.agent_model_api_key == "test-secret"


def test_settings_accept_explicit_agent_reasoning_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_THINKING", "disabled")
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_REASONING_EFFORT", "max")
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_MAX_OUTPUT_TOKENS", "8192")

    settings = Settings(_env_file=None)

    assert settings.agent_model_thinking == "disabled"
    assert settings.agent_model_reasoning_effort == "max"
    assert settings.agent_model_max_output_tokens == 8192


def test_settings_accept_agent_resilience_and_budget_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_RETRY_BASE_DELAY_SECONDS", "0.25")
    monkeypatch.setenv("CROPFLOW_AGENT_RUN_EXECUTION_TIMEOUT_SECONDS", "240")
    monkeypatch.setenv("CROPFLOW_AGENT_RUN_MAX_TOTAL_TOKENS", "20000")
    monkeypatch.setenv("CROPFLOW_AGENT_RUN_MAX_ESTIMATED_COST_USD", "0.02")
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_INPUT_CACHE_HIT_PRICE_PER_MILLION_USD", "0.1")
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_INPUT_CACHE_MISS_PRICE_PER_MILLION_USD", "0.2")
    monkeypatch.setenv("CROPFLOW_AGENT_MODEL_OUTPUT_PRICE_PER_MILLION_USD", "0.3")

    settings = Settings(_env_file=None)

    assert settings.agent_model_max_attempts == 4
    assert settings.agent_model_retry_base_delay_seconds == 0.25
    assert settings.agent_run_execution_timeout_seconds == 240
    assert settings.agent_run_max_total_tokens == 20000
    assert settings.agent_run_max_estimated_cost_usd == 0.02
    policy = build_run_budget_policy(settings)
    assert policy.max_estimated_cost_usd == 0.02
    assert policy.pricing is not None


def test_cost_budget_requires_complete_pricing_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CROPFLOW_AGENT_RUN_MAX_ESTIMATED_COST_USD", "0.01")

    with pytest.raises(RuntimeError, match="pricing is required"):
        build_run_budget_policy(Settings(_env_file=None))


def test_system_prompt_routes_explicit_actions_to_runtime_approval() -> None:
    assert "不要再用自然语言要求用户确认" in SYSTEM_PROMPT
    assert "Runtime 会创建正式 Approval" in SYSTEM_PROMPT
    assert "必填参数不明确" in SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_openai_compatible_provider_parses_tool_call_and_reinjects_result() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "role": "assistant",
                                "content": "读取任务",
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {"name": "get_task_detail", "arguments": "{\"task_id\":10}"},
                                    }
                                ],
                            },
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "完成"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example/v1",
        api_key="secret",
        model="test-model",
        thinking="enabled",
        reasoning_effort="high",
        max_output_tokens=4096,
        client=client,
    )
    base_request = ModelRequest(
        run_id="run-1",
        current_user_input="查看任务 10",
        recent_messages=({"role": "user", "content": "查看任务 10"},),
        actor={"user_id": "user-1", "role": "observer"},
        object_view={"object_type": "PlantingPlan", "object_id": 1},
        available_actions=(
            {
                "name": "get_task_detail",
                "description": "read task",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "integer"}},
                    "required": ["task_id"],
                },
            },
        ),
        tool_results=(),
        provider_state={},
    )

    first = await provider.complete_turn(base_request)
    second = await provider.complete_turn(
        replace(
            base_request,
            tool_results=(
                {
                    "call_id": "call-1",
                    "action_name": "get_task_detail",
                    "status": "completed",
                    "result": {"task_id": 10},
                    "error_code": None,
                    "error_message": None,
                },
            ),
            provider_state=first.provider_state,
        )
    )

    assert first.tool_calls[0].name == "get_task_detail"
    assert first.tool_calls[0].arguments == {"task_id": 10}
    assert second.text == "完成"
    tool_message = next(item for item in requests[1]["messages"] if item.get("role") == "tool")
    assert tool_message["tool_call_id"] == "call-1"
    assert requests[0]["parallel_tool_calls"] is True
    assert requests[0]["thinking"] == {"type": "enabled"}
    assert requests[0]["reasoning_effort"] == "high"
    assert requests[0]["max_tokens"] == 4096
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_accumulates_usage_in_provider_state() -> None:
    responses = [
        {
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "第一轮"}}],
            "usage": {
                "prompt_tokens": 100,
                "prompt_cache_hit_tokens": 60,
                "prompt_cache_miss_tokens": 40,
                "completion_tokens": 30,
                "total_tokens": 130,
                "completion_tokens_details": {"reasoning_tokens": 20},
            },
        },
        {
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "第二轮"}}],
            "usage": {
                "prompt_tokens": 80,
                "prompt_cache_hit_tokens": 50,
                "prompt_cache_miss_tokens": 30,
                "completion_tokens": 20,
                "total_tokens": 100,
                "completion_tokens_details": {"reasoning_tokens": 10},
            },
        },
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example/v1",
        api_key="secret",
        model="test-model",
        thinking="enabled",
        reasoning_effort="high",
        max_output_tokens=4096,
        client=client,
    )
    request = ModelRequest(
        run_id="run-usage",
        current_user_input="分析",
        recent_messages=({"role": "user", "content": "分析"},),
        actor={"user_id": "user-1", "role": "observer"},
        object_view={"object_type": "PlantingPlan", "object_id": 1},
        available_actions=(),
        tool_results=(),
        provider_state={},
    )

    first = await provider.complete_turn(request)
    second = await provider.complete_turn(replace(request, provider_state=first.provider_state))

    assert len(second.provider_state["usage_history"]) == 2
    assert second.provider_state["usage_totals"] == {
        "prompt_tokens": 180,
        "prompt_cache_hit_tokens": 110,
        "prompt_cache_miss_tokens": 70,
        "completion_tokens": 50,
        "reasoning_tokens": 30,
        "total_tokens": 230,
    }
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_retries_rate_limit_and_records_attempts() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"error": {"message": "busy"}})
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "完成"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example",
        api_key="secret",
        model="test-model",
        client=client,
        max_attempts=3,
        retry_jitter_ratio=0,
        retry_after_max_seconds=1,
        sleep=fake_sleep,
    )

    result = await provider.complete_turn(_simple_model_request())

    assert result.text == "完成"
    assert attempts == 2
    assert delays == [1]
    assert result.provider_state["provider_attempts_history"] == [2]
    assert result.provider_state["provider_retry_count"] == 1
    assert result.provider_state["provider_http_attempt_count"] == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_does_not_retry_authentication_error() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example",
        api_key="secret",
        model="test-model",
        client=client,
        max_attempts=3,
    )

    with pytest.raises(RuntimeRejected) as exc_info:
        await provider.complete_turn(_simple_model_request())

    assert exc_info.value.code == "provider_authentication_error"
    assert exc_info.value.details == {"attempts": 1, "status_code": 401, "retryable": False}
    assert attempts == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_classifies_retry_exhaustion_after_timeouts() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("simulated timeout", request=request)

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example",
        api_key="secret",
        model="test-model",
        client=client,
        max_attempts=3,
        retry_base_delay_seconds=0.5,
        retry_jitter_ratio=0,
        sleep=fake_sleep,
    )

    with pytest.raises(RuntimeRejected) as exc_info:
        await provider.complete_turn(_simple_model_request())

    assert exc_info.value.code == "provider_retry_exhausted"
    assert exc_info.value.details == {
        "attempts": 3,
        "cause_code": "provider_timeout",
        "retryable": True,
    }
    assert attempts == 3
    assert delays == [0.5, 1.0]
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_caps_output_tokens_to_runtime_remaining_budget() -> None:
    payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "完成"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example",
        api_key="secret",
        model="test-model",
        max_output_tokens=4096,
        client=client,
    )
    request = replace(
        _simple_model_request(),
        provider_state={"runtime_budget": {"remaining_tokens": 123}},
    )

    await provider.complete_turn(request)

    assert payloads[0]["max_tokens"] == 123
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_reinjects_structured_tool_failure() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "已处理失败"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example/v1",
        api_key="secret",
        model="test-model",
        client=client,
    )
    request = ModelRequest(
        run_id="run-1",
        current_user_input="查看任务 10",
        recent_messages=({"role": "user", "content": "查看任务 10"},),
        actor={"user_id": "user-1", "role": "observer"},
        object_view={"object_type": "PlantingPlan", "object_id": 1},
        available_actions=(),
        tool_results=(
            {
                "call_id": "call-failed",
                "action_name": "get_task_detail",
                "status": "failed",
                "result": {},
                "error_code": "query_unavailable",
                "error_message": "Task query is temporarily unavailable.",
            },
        ),
        provider_state={
            "transcript": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call-failed",
                            "type": "function",
                            "function": {"name": "get_task_detail", "arguments": "{\"task_id\":10}"},
                        }
                    ],
                }
            ]
        },
    )

    await provider.complete_turn(request)

    tool_message = next(item for item in requests[0]["messages"] if item.get("role") == "tool")
    assert json.loads(tool_message["content"]) == {
        "status": "failed",
        "result": {},
        "error_code": "query_unavailable",
        "error_message": "Task query is temporarily unavailable.",
    }
    await client.aclose()


def _simple_model_request() -> ModelRequest:
    return ModelRequest(
        run_id="run-resilience",
        current_user_input="分析计划",
        recent_messages=({"role": "user", "content": "分析计划"},),
        actor={"user_id": "user-1", "role": "observer"},
        object_view={"object_type": "PlantingPlan", "object_id": 1},
        available_actions=(),
        tool_results=(),
        provider_state={},
    )
