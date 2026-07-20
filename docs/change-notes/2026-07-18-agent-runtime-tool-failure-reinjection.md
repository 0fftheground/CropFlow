# 2026-07-18 Agent Runtime Tool Failure Reinjection

## Summary

Agent Runtime 现在会把 Tool 的拒绝、确定失败和副作用结果不确定状态统一保存为 Tool Result，并在下一轮回注模型。Tool 失败不再默认直接终止整个 Run。

## Behavior Changes

```text
Query / no-side-effect Tool exception
  -> failed Tool Result
  -> error_code + error_message reinjected
  -> model may explain or choose another safe action

Side-effect Tool exception after execution starts
  -> unknown Tool Result
  -> retry_allowed=false
  -> model may query/reconcile, but Runtime blocks automatic write retry

Runtime infrastructure failure
  -> run_failed
```

## Code Changes

- `ToolCallStatus` 新增 `unknown` 终态。
- Repository 会将 `completed / rejected / failed / unknown` 全部提供给 Context Builder。
- 串行 Tool 使用数据库 savepoint 隔离业务执行和 Runtime 外层事务。
- 串行 Tool 异常会产生 `tool_execution_failed` Event 和对应 Audit，不再直接抛出终止 Run。
- Side-effect `unknown` 后的新写 Action 会被拒绝为 `action_outcome_reconciliation_required`。
- Provider System Prompt 明确要求解释失败、不得伪造成功、不得自动重试 unknown 写操作。

## Validation

新增确定性测试覆盖：

```text
并行 Query 一项异常时成功结果仍保留，failed 结果回注模型
批准后的 Side-effect 异常保存为 unknown 并回注模型
unknown 之后模型再次提出写 Action 时 Runtime 强制拒绝
OpenAI-compatible Provider 按 tool role 发送结构化失败字段
```

全量回归：

```text
227 passed, 1 skipped
Scripted Mock Eval: 6 / 6 passed, Hard Gate violations = 0
```

## Boundaries

- 本次没有调用真实模型，也没有连接目标数据库或真实业务数据。
- `unknown` 目前要求模型说明或人工核对；正式 reconciliation / resume API 尚未实现。
- 生产化前仍需补错误分类、敏感异常信息脱敏和真实模型失败恢复 Eval。

## Related Documents

- `docs/architecture/agent-runtime.md`
- `docs/api/agent_runtime_api.md`
- `docs/decisions/014-agent-runtime-tool-failure-reinjection.md`
