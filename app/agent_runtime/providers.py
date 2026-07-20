from __future__ import annotations

import asyncio
import json
import random
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import uuid4

import httpx

from app.agent_runtime.contracts import ModelRequest, ModelTurnResult, RuntimeRejected, ToolCall
from app.core.config import Settings


SYSTEM_PROMPT = """你是 CropFlow 的 Business Agent。你的职责是帮助业务人员理解并处理一个 PlantingPlan 内的农事流程。

必须遵守：
1. CropFlow 数据库中的 PlantingPlan、FarmingTask、OperationPlan、Execution、ReviewRequest 是权威业务状态。
2. 只能调用本轮提供的 actions；不可声称已完成未实际执行的动作。
3. 写操作只是 action proposal，Runtime 会在执行前做权限、对象范围、状态、审批和业务规则复核。
4. 不要要求用户重复提供 active PlantingPlan 或当前用户等 Runtime 已知参数。
5. 工具结果返回后，基于结果继续回答；工具为 rejected、failed 或 unknown 时解释原因，不要伪造成功。
6. 回答使用简洁、清楚的中文。
7. 可以在同一次响应中调用多个互相独立的只读查询工具。
8. 不要把查询工具和写 Action 放在同一个工具批次；先读取并等待工具结果，再基于结果提出一个写 Action。
9. 一次只提出一个会写入、需要审批或有副作用的 Action。
10. side-effect Tool 的 unknown 表示结果不确定；不得自动重试写 Action，应先查询权威业务状态或转人工核对。
11. 如果用户已明确要求一个可用写 Action，且必填参数齐全，应直接提出 Tool Call；不要再用自然语言要求用户确认，Runtime 会创建正式 Approval。
12. 如果用户意图或写 Action 必填参数不明确，应先提出一个具体澄清问题，不要猜测执行。
"""

USAGE_FIELDS = (
    "prompt_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
)
RETRYABLE_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
RETRYABLE_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


class OpenAICompatibleChatProvider:
    name = "openai_compatible_chat"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
        thinking: str = "enabled",
        reasoning_effort: str = "high",
        max_output_tokens: int = 4096,
        max_attempts: int = 3,
        retry_base_delay_seconds: float = 0.5,
        retry_max_delay_seconds: float = 4.0,
        retry_jitter_ratio: float = 0.2,
        retry_after_max_seconds: float = 10.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("Provider max_attempts must be at least one.")
        if min(retry_base_delay_seconds, retry_max_delay_seconds, retry_after_max_seconds) < 0:
            raise ValueError("Provider retry delays cannot be negative.")
        if not 0 <= retry_jitter_ratio <= 1:
            raise ValueError("Provider retry_jitter_ratio must be between zero and one.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.thinking = thinking
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.max_attempts = max_attempts
        self.retry_base_delay_seconds = retry_base_delay_seconds
        self.retry_max_delay_seconds = retry_max_delay_seconds
        self.retry_jitter_ratio = retry_jitter_ratio
        self.retry_after_max_seconds = retry_after_max_seconds
        self.sleep = sleep
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def complete_turn(self, request: ModelRequest) -> ModelTurnResult:
        state = dict(request.provider_state or {})
        transcript = list(state.get("transcript", []))
        consumed_call_ids = set(state.get("consumed_call_ids", []))
        new_tool_messages = [
            {
                "role": "tool",
                "tool_call_id": item["call_id"],
                "content": json.dumps(
                    {
                        "status": item["status"],
                        "result": item.get("result", {}),
                        "error_code": item.get("error_code"),
                        "error_message": item.get("error_message"),
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            }
            for item in request.tool_results
            if item["call_id"] not in consumed_call_ids
        ]
        context_payload = {
            "current_actor": request.actor,
            "active_object_view": request.object_view,
            "available_action_names": [item["name"] for item in request.available_actions],
        }
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n本轮业务上下文：\n{json.dumps(context_payload, ensure_ascii=False, default=str)}",
            }
        ]
        messages.extend(
            {"role": item["role"], "content": item["content"]}
            for item in request.recent_messages
            if item["role"] in {"user", "assistant"}
        )
        messages.extend(transcript)
        messages.extend(new_tool_messages)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": item["name"],
                    "description": item["description"],
                    "parameters": item["input_schema"],
                },
            }
            for item in request.available_actions
        ]
        runtime_budget = dict(state.get("runtime_budget") or {})
        remaining_tokens = runtime_budget.get("remaining_tokens")
        request_max_tokens = self.max_output_tokens
        if remaining_tokens is not None:
            request_max_tokens = max(1, min(request_max_tokens, int(remaining_tokens)))
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "thinking": {"type": self.thinking},
            "max_tokens": request_max_tokens,
        }
        if self.thinking == "enabled":
            payload["reasoning_effort"] = self.reasoning_effort
        response, attempt_count = await self._post_with_retry(payload)
        try:
            body = response.json()
        except ValueError as exc:
            raise RuntimeRejected(
                "Model provider returned a non-JSON completion payload.",
                code="provider_protocol_error",
                details={"attempts": attempt_count, "status_code": response.status_code, "retryable": False},
            ) from exc
        try:
            choice = body["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeRejected(
                "Model provider returned an invalid chat completion payload.",
                code="provider_protocol_error",
            ) from exc

        raw_tool_calls = list(message.get("tool_calls") or [])
        tool_calls: list[ToolCall] = []
        for raw in raw_tool_calls:
            function = dict(raw.get("function") or {})
            raw_arguments = function.get("arguments", "{}")
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
            except (json.JSONDecodeError, TypeError, ValueError):
                arguments = {"__invalid_json__": str(raw_arguments)}
            tool_calls.append(
                ToolCall(
                    call_id=str(raw.get("id") or f"call-{uuid4().hex}"),
                    name=str(function.get("name") or ""),
                    arguments=arguments,
                )
            )

        updated_transcript = [*transcript, *new_tool_messages]
        if raw_tool_calls:
            assistant_message = {
                key: value
                for key, value in message.items()
                if key in {"role", "content", "reasoning_content", "tool_calls"} and value is not None
            }
            assistant_message.setdefault("role", "assistant")
            updated_transcript.append(assistant_message)
        consumed_call_ids.update(item["call_id"] for item in request.tool_results)
        usage = _normalize_usage(body.get("usage"))
        usage_history = [*list(state.get("usage_history", [])), usage]
        usage_totals = _sum_usage(usage_history)
        attempts_history = [*list(state.get("provider_attempts_history", [])), attempt_count]
        provider_state = {
            **state,
            "transcript": updated_transcript,
            "consumed_call_ids": sorted(consumed_call_ids),
            "usage_history": usage_history,
            "usage_totals": usage_totals,
            "provider_attempts_history": attempts_history,
            "provider_request_count": len(attempts_history),
            "provider_http_attempt_count": sum(int(item) for item in attempts_history),
            "provider_retry_count": sum(max(0, int(item) - 1) for item in attempts_history),
        }
        return ModelTurnResult(
            text=str(message.get("content") or ""),
            tool_calls=tuple(tool_calls),
            finish_reason=str(choice.get("finish_reason") or ("tool_calls" if tool_calls else "stop")),
            provider_state=provider_state,
        )

    async def _post_with_retry(self, payload: dict[str, Any]) -> tuple[httpx.Response, int]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(1, self.max_attempts + 1):
            cause_code = "provider_unavailable"
            status_code: int | None = None
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            except RETRYABLE_TRANSPORT_ERRORS as exc:
                cause_code = "provider_timeout" if isinstance(exc, httpx.TimeoutException) else "provider_unavailable"
                if attempt >= self.max_attempts:
                    raise _retry_exhausted(cause_code=cause_code, attempts=attempt) from exc
                await self.sleep(self._retry_delay(attempt, retry_after=None))
                continue
            except httpx.RequestError as exc:
                raise RuntimeRejected(
                    "Model provider request could not be created or sent.",
                    code="provider_request_error",
                    details={"attempts": attempt, "retryable": False},
                ) from exc

            status_code = response.status_code
            if status_code < 400:
                return response, attempt

            cause_code, retryable = _classify_http_status(status_code)
            if retryable and attempt < self.max_attempts:
                await self.sleep(self._retry_delay(attempt, retry_after=response.headers.get("Retry-After")))
                continue
            if retryable:
                raise _retry_exhausted(
                    cause_code=cause_code,
                    attempts=attempt,
                    status_code=status_code,
                )
            raise RuntimeRejected(
                _provider_http_error_message(response, cause_code),
                code=cause_code,
                details={"attempts": attempt, "status_code": status_code, "retryable": False},
            )

        raise AssertionError("Provider retry loop exited unexpectedly.")

    def _retry_delay(self, attempt: int, *, retry_after: str | None) -> float:
        parsed_retry_after = _parse_retry_after(retry_after)
        if parsed_retry_after is not None:
            return min(self.retry_after_max_seconds, max(0.0, parsed_retry_after))
        base = min(
            self.retry_max_delay_seconds,
            self.retry_base_delay_seconds * (2 ** max(0, attempt - 1)),
        )
        if self.retry_jitter_ratio == 0:
            return base
        return base * random.uniform(1 - self.retry_jitter_ratio, 1 + self.retry_jitter_ratio)

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()


class ScriptedCropFlowProvider:
    """No-key provider for deterministic local development and runtime tests."""

    name = "scripted_cropflow"

    async def complete_turn(self, request: ModelRequest) -> ModelTurnResult:
        available = {item["name"] for item in request.available_actions}
        results = list(request.tool_results)
        if results:
            failed = [item for item in results if item["status"] in {"rejected", "failed", "unknown"}]
            if failed:
                names = "、".join(item["action_name"] for item in failed)
                return ModelTurnResult(text=f"工具 {names} 未成功，我会保留已成功的结果并说明失败原因。")
            plan_result = next((item for item in results if item["action_name"] == "view_plan_context"), None)
            task_result = next((item for item in results if item["action_name"] == "get_task_detail"), None)
            if plan_result and task_result:
                plan_tasks = plan_result["result"].get("current_tasks", [])
                plan_status = plan_tasks[0].get("status") if plan_tasks else None
                task_status = task_result["result"].get("farming_task", {}).get("status")
                if plan_status and task_status and plan_status != task_status:
                    return ModelTurnResult(text="计划摘要与任务详情存在状态冲突，应以任务权威详情为准并进行人工核对。")
            if "综合分析" in request.current_user_input and len(results) >= 3:
                return ModelTurnResult(
                    text="当前处于关键生育期且积温接近下一阶段阈值，未来降雨风险较高，应结合任务与复核证据关注作业窗口。"
                )
            latest = results[-1]
            if latest["status"] == "completed":
                return ModelTurnResult(
                    text=(
                        f"动作 {latest['action_name']} 已完成。"
                        f"结果：{json.dumps(latest['result'], ensure_ascii=False, default=str)}"
                    )
                )
            return ModelTurnResult(
                text=(
                    f"动作 {latest['action_name']} 未执行成功："
                    f"{latest.get('error_message') or latest.get('error_code') or latest['status']}。"
                )
            )

        message = request.current_user_input
        task_id = _extract_id(message, ("任务", "task"))
        review_id = _extract_id(message, ("复核", "review"))
        iso_date = _extract_iso_date(message)

        if task_id is not None and "处理任务" in message and not any(
            word in message for word in ("查看", "完成", "取消", "执行", "详情")
        ):
            return ModelTurnResult(text="请确认你是要查看任务详情，还是要申请完成该任务？")

        if any(word in message for word in ("综合分析", "一起读取", "对比计划", "同时核实")):
            calls: list[ToolCall] = []
            if "view_plan_context" in available:
                calls.append(ToolCall(name="view_plan_context", arguments={}))
            if task_id is not None and "get_task_detail" in available:
                calls.append(ToolCall(name="get_task_detail", arguments={"task_id": task_id}))
            if review_id is not None and "get_review_request_detail" in available:
                calls.append(
                    ToolCall(name="get_review_request_detail", arguments={"review_request_id": review_id})
                )
            if calls:
                return ModelTurnResult(text="我先并行读取相关权威状态。", tool_calls=tuple(calls), finish_reason="tool_calls")

        if (
            task_id is not None
            and any(word in message for word in ("完成", "执行结果"))
            and not any(word in message for word in ("不要完成", "不执行", "只查看"))
            and "complete_farming_task" in available
        ):
            return ModelTurnResult(
                text="我会先提交任务完成动作，等待你明确批准后再写入业务状态。",
                tool_calls=(
                    ToolCall(
                        name="complete_farming_task",
                        arguments={
                            "task_id": task_id,
                            "operation_date": iso_date or date.today().isoformat(),
                            "result_payload": {"source": "agent", "user_message": message},
                        },
                    ),
                ),
                finish_reason="tool_calls",
            )
        if review_id is not None and any(word in message for word in ("批准", "通过", "同意", "驳回", "拒绝")) and "resolve_review_request" in available:
            decision = "approve" if any(word in message for word in ("批准", "通过", "同意")) else "reject"
            return ModelTurnResult(
                text="我会先提交复核处理动作，等待你明确批准后再改变复核状态。",
                tool_calls=(
                    ToolCall(
                        name="resolve_review_request",
                        arguments={
                            "review_request_id": review_id,
                            "decision": decision,
                            "decision_payload": {},
                            "decision_note": message,
                        },
                    ),
                ),
                finish_reason="tool_calls",
            )
        if task_id is not None and "get_task_detail" in available:
            return ModelTurnResult(
                text="我先读取该任务的权威详情。",
                tool_calls=(ToolCall(name="get_task_detail", arguments={"task_id": task_id}),),
                finish_reason="tool_calls",
            )
        if review_id is not None and "get_review_request_detail" in available:
            return ModelTurnResult(
                text="我先读取该复核事项的证据和当前状态。",
                tool_calls=(
                    ToolCall(name="get_review_request_detail", arguments={"review_request_id": review_id}),
                ),
                finish_reason="tool_calls",
            )
        if "view_plan_context" in available:
            return ModelTurnResult(
                text="我先读取当前种植计划的运行上下文。",
                tool_calls=(ToolCall(name="view_plan_context", arguments={}),),
                finish_reason="tool_calls",
            )
        return ModelTurnResult(text="当前没有可用于处理该请求的动作。")


def build_agent_model_provider(settings: Settings):
    provider = settings.agent_model_provider.strip().lower()
    if provider == "scripted":
        if settings.require_real_integrations:
            raise RuntimeError(
                "Agent model requires CROPFLOW_AGENT_MODEL_PROVIDER=openai_compatible "
                "when CROPFLOW_REQUIRE_REAL_INTEGRATIONS=true."
            )
        return ScriptedCropFlowProvider()
    if provider in {"openai_compatible", "openai-compatible", "chat_completions"}:
        base_url = (settings.agent_model_base_url or "").strip()
        api_key = (settings.agent_model_api_key or "").strip()
        model = settings.agent_model_name.strip()
        missing = [
            name
            for name, value in (
                ("CROPFLOW_AGENT_MODEL_BASE_URL", base_url),
                ("CROPFLOW_AGENT_MODEL_API_KEY", api_key),
                ("CROPFLOW_AGENT_MODEL_NAME", model),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Agent model configuration is missing: {', '.join(missing)}.")
        return OpenAICompatibleChatProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=settings.agent_model_timeout_seconds,
            thinking=settings.agent_model_thinking,
            reasoning_effort=settings.agent_model_reasoning_effort,
            max_output_tokens=settings.agent_model_max_output_tokens,
            max_attempts=settings.agent_model_max_attempts,
            retry_base_delay_seconds=settings.agent_model_retry_base_delay_seconds,
            retry_max_delay_seconds=settings.agent_model_retry_max_delay_seconds,
            retry_jitter_ratio=settings.agent_model_retry_jitter_ratio,
            retry_after_max_seconds=settings.agent_model_retry_after_max_seconds,
        )
    raise RuntimeError(f"Unsupported CROPFLOW_AGENT_MODEL_PROVIDER: {settings.agent_model_provider}.")


def _extract_id(message: str, labels: tuple[str, ...]) -> int | None:
    for label in labels:
        match = re.search(rf"{re.escape(label)}\s*[#:]?\s*(\d+)", message, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_iso_date(message: str) -> str | None:
    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", message)
    return match.group(0) if match else None


def _normalize_usage(raw_usage: Any) -> dict[str, int]:
    raw = dict(raw_usage or {})
    completion_details = dict(raw.get("completion_tokens_details") or {})
    prompt_tokens = int(raw.get("prompt_tokens") or 0)
    cache_hit_tokens = int(raw.get("prompt_cache_hit_tokens") or 0)
    if "prompt_cache_miss_tokens" in raw:
        cache_miss_tokens = int(raw.get("prompt_cache_miss_tokens") or 0)
    else:
        cache_miss_tokens = max(0, prompt_tokens - cache_hit_tokens)
    completion_tokens = int(raw.get("completion_tokens") or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "prompt_cache_hit_tokens": cache_hit_tokens,
        "prompt_cache_miss_tokens": cache_miss_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": int(completion_details.get("reasoning_tokens") or 0),
        "total_tokens": int(raw.get("total_tokens") or prompt_tokens + completion_tokens),
    }


def _sum_usage(history: list[dict[str, Any]]) -> dict[str, int]:
    return {
        field: sum(int(item.get(field) or 0) for item in history)
        for field in USAGE_FIELDS
    }


def _classify_http_status(status_code: int) -> tuple[str, bool]:
    if status_code == 408:
        return "provider_timeout", True
    if status_code == 429:
        return "provider_rate_limited", True
    if status_code in {500, 502, 503, 504}:
        return "provider_unavailable", True
    if status_code in {401, 403}:
        return "provider_authentication_error", False
    if status_code == 402:
        return "provider_quota_exhausted", False
    if status_code in {400, 404, 422}:
        return "provider_request_error", False
    return "provider_http_error", False


def _retry_exhausted(
    *,
    cause_code: str,
    attempts: int,
    status_code: int | None = None,
) -> RuntimeRejected:
    details: dict[str, Any] = {
        "attempts": attempts,
        "cause_code": cause_code,
        "retryable": True,
    }
    if status_code is not None:
        details["status_code"] = status_code
    return RuntimeRejected(
        f"Model provider retry budget exhausted after {attempts} attempts ({cause_code}).",
        code="provider_retry_exhausted",
        details=details,
    )


def _provider_http_error_message(response: httpx.Response, code: str) -> str:
    provider_message = ""
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            provider_message = str(error.get("message") or "")
        elif error:
            provider_message = str(error)
    except ValueError:
        provider_message = ""
    suffix = f": {provider_message[:500]}" if provider_message else ""
    return f"Model provider request failed with HTTP {response.status_code} ({code}){suffix}."


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
