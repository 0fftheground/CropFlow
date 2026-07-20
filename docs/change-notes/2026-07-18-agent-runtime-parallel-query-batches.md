# 2026-07-18 Agent Runtime Parallel Query Batches

## Summary

CropFlow Agent Runtime 现在允许一个 Model Turn 中互相独立的只读 Query Tool 受控并行执行；有依赖、需要 Approval 或存在副作用的 Action 仍然串行，并在查询结果回注后重新规划。

## Behavior Changes

```text
parallel_safe Query batch
  -> bounded parallel execution
  -> isolated SQLAlchemy Session per query
  -> stable Tool Result order

Query + Side Effect
  -> Query executes
  -> old write proposal is rejected with side_effect_requires_replan
  -> model replans after seeing Query Results

multiple Side Effects
  -> first action may enter PreAction / Approval
  -> extra actions are rejected with serial_action_requires_replan
```

Provider 请求现在设置 `parallel_tool_calls=true`，但 Runtime 仍是并发策略的权威边界。

## Code Changes

- `ActionContract` 新增 `parallel_safe`，默认关闭。
- 三个现有只读 Query 标记为可并行。
- `AgentRuntime` 新增 parallel query batch、partial result 和 mixed-batch replan。
- FastAPI Runtime dependency 为每个并行 Query 创建独立 SQLAlchemy Session。
- 新增 `CROPFLOW_AGENT_MAX_PARALLEL_QUERIES`，默认 `4`。
- Tool Result 按模型原始 Tool Call 顺序回注。

## Validation

新增测试覆盖：

```text
三个独立 Query 实际并发并全部回注
Query + Write 先查询再要求写动作 replan
多个写动作只允许第一个进入 Approval
并行 Query 部分被 scope 拒绝时仍回注全部结果
Provider parallel_tool_calls=true
```

真实 DeepSeek + Mock Business State 报告已在新调度策略下重新生成。两模型六场景首轮均为 `5 / 6`，Hard Gate 违规均为 `0`。

全量回归：

```text
223 passed, 1 skipped
```

## Boundaries

- 不允许共享同一个 SQLAlchemy Session 并行查询。
- 当前只并行明确声明 `parallel_safe` 的 Query。
- 写 Action 没有并行化，也没有改变 Approval、幂等和批准后重新 PreAction 规则。
- 本次仍未连接目标数据库或执行真实业务数据 Pilot。
