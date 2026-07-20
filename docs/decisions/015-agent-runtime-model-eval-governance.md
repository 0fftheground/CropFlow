# ADR 015 - Agent Runtime 模型 Eval 治理

状态：Accepted  
日期：2026-07-18

## Context

单次模型调用无法证明 Tool 选择、Approval、安全边界或复杂场景稳定。Prompt、Tool Schema、模型配置和 Grader 如果同时在同一批样本上反复调整，也会造成评估集泄漏。生产化还需要 Token、成本和长尾延迟，而不只是 Pass Rate。

## Decision

1. Dataset 分为 `development / regression / holdout`：Development 用于迭代，Regression 用于持续回归，Holdout 仅在配置冻结后运行。
2. P0 Regression 每个场景至少采样 10 次；Runner 默认采用场景声明的最高最小采样值，低于要求必须显式声明为 smoke。
3. Runtime 不依赖 Strict Tool Calls：所有 arguments 继续通过本地 Schema、角色、Scope、状态和 Approval 校验。
4. Adapter 显式配置 Thinking、Reasoning Effort 和输出 Token 上限，并保存 prompt、cache hit/miss、completion、reasoning 和 total usage。
5. 报告同时保存确定性轨迹、Hard Gate、多 Tool Calls、错误、每成功 Run Token、按版本化价格快照估算的成本，以及 latency average / p50 / p95 / max。
6. 用户已经明确写 Action 且必填参数齐全时，模型应直接提出 Tool Call，由 Runtime 创建 Approval；只有意图或必填参数缺失时才自然语言澄清。
7. `finish_reason=length` 是失败终态 `model_output_truncated`，不能作为完成回答。
8. Eval 报告必须标明 Model Provider、Business Data Source、是否连接目标数据库和是否使用 Strict Tool Calls，并保存 Dataset 与选中场景的 SHA-256。

## Consequences

优点：

- 安全、轨迹质量和效率指标可以独立检查。
- 多次采样能暴露模型波动，Holdout 能减少针对测试集调参。
- Token、缓存、成本和尾延迟具备可审计证据。
- 正式 Runtime Approval 不再与模型自然语言确认混淆。

代价与限制：

- 真实模型回归有时间和 API 成本。
- Mock Business State 不能证明真实数据、IAM、多租户、生产并发或用户采用。
- 价格只是带日期的估算快照；Provider 失败且未返回 completion 时可能没有 usage。
- Holdout 纪律目前由流程约束，后续可在 CI / 权限层进一步隔离。

## Alternatives Considered

- 只运行单次 smoke：成本低，但无法识别模型输出波动。
- 只看最终文本：无法发现审批前副作用、越权或错误 Tool 轨迹。
- 用一个 Dataset 同时开发和验收：实现简单，但会造成评估集泄漏。
- 依赖模型自然语言确认：不可持久化、不可审计，也不能替代 Runtime Approval。

## Related

- `docs/development/agent-runtime-model-eval.md`
- `evals/agent_runtime/README.md`
- `docs/decisions/013-agent-runtime-tool-concurrency-policy.md`
- `docs/decisions/014-agent-runtime-tool-failure-reinjection.md`
