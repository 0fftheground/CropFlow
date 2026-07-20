# ADR 014 - Agent Runtime Tool 失败回注与副作用结果不确定性

状态：Accepted
日期：2026-07-18

## Context

Tool 执行失败也是模型下一步决策所需的权威执行事实。旧 Runtime 已能把并行 Query 的单项异常保存为 `failed`，但串行 Tool、尤其人工批准后的写 Action，遇到异常会直接终止 Run；模型无法看到失败原因，也无法解释、改用查询或转人工处理。

写 Action 还有一个额外风险：调用抛出异常不一定代表副作用没有发生。外部系统可能已接收请求，但响应超时或连接中断。如果把这种情况简单标为 `failed` 并允许模型重试，可能重复完成任务或重复处理复核。

## Decision

Tool Result 统一使用以下终态：

```text
completed
  已得到确定成功结果，可以正常继续推理。

rejected
  Runtime 在权限、Schema、对象范围、业务状态、审批或调度边界拒绝执行。

failed
  无副作用 Tool 执行异常，失败原因作为 Tool Result 回注，Run 可继续。

unknown
  Side-effect Tool 已开始执行但抛出异常，最终业务结果不确定。
  必须回注模型，但禁止自动重试写 Action。
```

每个串行 Tool 在独立数据库 savepoint 中执行。异常时回滚本地 savepoint，再持久化 Tool Result、Event 和 Audit：

```text
read-only failure
  status = failed
  error_code = exception type
  error_message = failure message
  -> reinject to model

side-effect failure
  status = unknown
  error_code = action_outcome_unknown
  result = {"outcome": "unknown", "retry_allowed": false}
  -> reinject to model
  -> reject later side-effect proposals with action_outcome_reconciliation_required
```

`unknown` 采用保守语义。数据库 savepoint 可以回滚 CropFlow 本地事务，但无法证明外部系统没有接受请求。模型可以继续调用只读 Query 核对权威业务状态，或明确要求人工处理；不能自动再次写入。

只有 Runtime 自身无法继续的错误，例如持久化状态缺失、Provider 协议错误、Context Builder 不可用或超过最大迭代次数，才进入 `run_failed`。

## Consequences

优点：

- 模型能看到查询失败、拒绝和副作用不确定结果，不会把无结果当成功。
- 并行 Query 部分失败与串行 Tool 失败具有一致回注语义。
- 写 Action 的不确定结果不会被模型自动重试，降低重复副作用风险。
- ToolCall、Event 和 Audit 保存同一失败事实，便于回放和排查。

代价：

- `unknown` 需要后续增加人工 reconciliation / resume 能力。
- 当前异常消息仍来自执行器，生产化前还需按错误分类补脱敏和用户可见文案。
- 真实模型 Eval 尚未覆盖失败恢复轨迹，本次证据是确定性 Runtime 与 Provider Contract 测试。

## Rejected Alternatives

### 任意 Tool 异常都直接失败 Run

会丢失模型解释、降级查询和人工引导能力，也让可恢复查询失败变成整个会话失败。

### 任意 Tool 异常都标为 failed 并允许重试

不能保护外部副作用结果不确定的场景，可能造成重复写入。

### 仅在日志中保存异常

日志不是模型协议的一部分，模型仍会缺少上一动作的真实结果。
