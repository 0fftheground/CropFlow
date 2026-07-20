# ADR 016 - Agent Runtime Provider 重试与 Run Budget

状态：Accepted  
日期：2026-07-18

## Context

真实模型 Development Eval 暴露了长尾 Provider 失败。此前 Runtime 只有单请求 timeout 和 `max_iterations`，没有统一的错误分类、有限重试、活跃执行时限或累计 Token / 成本预算。

## Decision

1. Model Provider 最多尝试 3 次，采用指数退避、20% jitter，并尊重被 10 秒上限裁剪的 `Retry-After`。
2. 只重试网络/协议传输瞬态异常与 HTTP `408 / 429 / 500 / 502 / 503 / 504`；请求格式、认证、余额、参数和 Provider 协议错误不重试。
3. 重试只包围模型 HTTP 请求，不自动重放任何业务 Tool 或 Side Effect。
4. 每个活跃执行段默认最多 180 秒；等待人工 Approval 的时间不计入，恢复执行时创建新 deadline。
5. 每个 Run 默认最多累计 16,000 个 Provider-reported tokens。每轮调用完成后检查预算，超限时不处理该轮 Tool Calls。
6. Adapter 使用剩余 Token 缩小下一次 `max_tokens`，但由于调用前无法精确知道输入 Token，单次请求仍可能轻微超过累计预算。
7. 成本预算只有在显式配置三类价格和 Run 上限后启用。价格变化频繁，不能把 Eval 快照静默当作生产价格。
8. `model_call_completed` 记录 usage、attempt count 和 budget snapshot；`run_failed` 与 Audit 保存结构化错误 details。

## Error Codes

```text
provider_authentication_error
provider_quota_exhausted
provider_request_error
provider_http_error
provider_protocol_error
provider_retry_exhausted
run_execution_timeout
run_token_budget_exceeded
run_cost_budget_exceeded
```

`provider_retry_exhausted.details.cause_code` 保留最终根因，例如 `provider_timeout / provider_rate_limited / provider_unavailable`。

## Consequences

- 瞬态 Provider 故障可自动恢复，永久错误可以快速失败。
- 重试次数、Token、成本和超时都有可审计边界。
- HTTP 请求仍然绑定当前 API 进程；进程崩溃和多实例恢复需要后续 Durable Worker。
- 同步业务 Action 无法被 asyncio 强制中断；Runtime 会在 Action 前后检查 deadline。真正的硬隔离需要 Worker 进程与外部调用 timeout。

## Related

- `docs/architecture/agent-runtime.md`
- `docs/architecture/agent-runtime-durable-execution.md`
- `docs/development/agent-runtime-model-eval.md`
