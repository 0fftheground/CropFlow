# ADR 013 - Agent Runtime Tool 并发策略

状态：Accepted
日期：2026-07-18

## Context

模型可能在一个 Model Turn 中返回多个 Tool Calls。旧 Runtime 无论 Tool 类型如何，只处理第一个调用，其余统一拒绝为 `parallel_actions_not_supported`。

该策略能够保护写操作，但会让互相独立的只读查询产生不必要的多轮模型调用和延迟。另一方面，查询与写 Action、相互依赖的调用或多个副作用 Action 不能直接并行，否则会产生旧状态写入、审批语义不清和部分成功问题。

## Decision

Runtime 按 Action Contract 和当前批次动态调度：

```text
全部是 parallel_safe Query
  -> 有上限地并行执行
  -> 每个 Query 使用独立数据库 Session
  -> 结果按模型原始 Tool Call 顺序回注

Query + Side Effect 混合
  -> 并行执行 Query
  -> Side Effect 标记 side_effect_requires_replan
  -> 模型看到查询结果后重新提出一个写 Action

多个 Serial / Side Effect Action
  -> 只处理第一个
  -> 其余标记 serial_action_requires_replan
  -> 第一个完成或审批后，重新加载状态再决定下一步
```

`ActionContract.parallel_safe` 默认是 `false`。只有明确满足以下条件的 Action 才能设为 `true`：

```text
无业务副作用
不需要 Approval
不依赖同批次其他 Tool Result
可以在同一业务状态快照上执行
使用隔离且线程安全的资源
```

当前允许并行的 Query：

```text
view_plan_context
get_task_detail
get_review_request_detail
```

并发数由 `CROPFLOW_AGENT_MAX_PARALLEL_QUERIES` 控制，默认 `4`。

Provider 的 `parallel_tool_calls=true` 只允许模型提出多个调用，不代表这些调用一定会并行执行；最终策略由 Runtime 强制决定。

## Consequences

优点：

- 独立查询减少模型往返和整体延迟。
- 写 Action 继续保持单 Action、PreAction、Approval 和最新状态复核。
- 查询部分失败不会取消整个批次；成功和失败结果都会回注模型。
- ToolCall、Event 和 Audit 仍按单调用记录，结果顺序稳定。

代价：

- 并行数据库查询需要额外连接和独立 Session。
- Runtime 需要处理部分成功、批次错误和 bounded concurrency。
- Action 只有显式声明 `parallel_safe` 才能并行，新增 Query 默认仍走保守串行策略。

## Rejected Alternatives

### 所有 Tool 永远只执行第一个

安全但查询延迟高，也无法利用模型一次产生多个独立查询的能力。

### 模型返回的所有 Tool Calls 全部并行

无法保护数据依赖、Approval、对象状态和副作用 Action，拒绝采用。

### 混合批次按模型顺序直接串行执行 Query 和 Write

Write Proposal 生成时模型还没有看到同批次 Query 的真实结果，可能基于错误假设；因此必须回注结果后重新提出。
