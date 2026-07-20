# 2026-07-18 Agent Runtime Resilience And Budgets

## Summary

为 Agent Runtime 增加 Provider 瞬态错误恢复、结构化错误分类、活跃执行段 timeout、累计 Token 和可选成本预算，并补 Durable Worker / Job / Watchdog 的目标态设计。

## Code Changes

- OpenAI-compatible Provider 最多尝试 3 次，支持 exponential backoff、jitter 和 capped `Retry-After`。
- 仅重试网络瞬态错误与 408 / 429 / 5xx；认证、余额、请求和协议问题快速失败。
- Provider state 记录每轮 attempts、累计 HTTP attempts 和 retry count。
- Runtime 默认使用 180 秒活跃执行段；Approval 等待后重新计时。
- Runtime 默认限制 16,000 total tokens，成本预算通过显式价格配置启用。
- 超过预算后不处理该轮模型提出的 Tool Calls；Adapter 使用剩余 Token 缩小下一轮 `max_tokens`。
- `model_call_completed` 和 `run_failed` 增加 usage、budget、attempt 和 error details。
- Eval v4 报告记录 retry 和 run-budget 配置。

## Tests

覆盖：

```text
429 + Retry-After 后成功
401 快速失败且不重试
网络 timeout 重试耗尽与 cause_code
Provider attempt/retry 持久化
剩余 Token 裁剪 max_tokens
Token 超限不执行 Tool
成本预算终止 Run
慢模型调用触发 run_execution_timeout
Approval 等待不消耗活跃执行时间
```

验证结果：

```text
249 passed, 1 skipped, 1 warning
scripted Regression: 70 / 70, Hard Gate 0
scripted Development: 12 / 12, Hard Gate 0
deepseek-v4-pro resilience smoke: 1 / 1, HTTP attempts 2, retries 0
```

真实 smoke 使用真实 DeepSeek Provider + 真实 Runtime + Mock Business State，没有连接目标数据库。

## Durable Execution Design

新增 `docs/architecture/agent-runtime-durable-execution.md`，详细解释 Worker、Job、Queue、Lease、Heartbeat、Watchdog、多实例 SSE、at-least-once 与 Side Effect unknown recovery。该设计尚未实现，ADR 017 状态为 Proposed。

## Remaining

- 用真实模型重新运行 Development，验证新 retry/timeout 策略对长尾失败的影响。
- 第 6 项需确认 Proposed ADR 017 后新增 `cf_agent_job`、migration 016 和 Worker。
