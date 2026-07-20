# CropFlow Agent Runtime API

## 1. 创建并执行 Run

```http
POST /api/agent/runs
Content-Type: application/json
```

```json
{
  "user_id": "user-001",
  "planting_plan_id": 1001,
  "session_id": "optional-stable-session-id",
  "role": "observer",
  "message": "查看当前计划和待办任务"
}
```

`role` 可省略。传入时必须已经配置在 `cf_user.metadata.agent_roles` 中；不允许客户端借此提升权限。

返回：

```json
{
  "run_id": "run-...",
  "session_id": "session-...",
  "status": "completed",
  "iteration": 2,
  "pending_approvals": [],
  "events_url": "/api/agent/runs/run-.../events"
}
```

Run 状态：

```text
pending
running
waiting_approval
completed
failed
```

## 2. SSE 执行

```http
POST /api/agent/runs/stream
```

请求体与创建 Run 相同。响应为 `text/event-stream`。

```text
event: run_started
data: {...}

event: approval_required
data: {"approval_id":"approval-...", ...}
```

当 Run 进入 `waiting_approval` 时，本次流结束。批准或拒绝后可通过 events API 获取后续事件。

## 3. 查询 Run

```http
GET /api/agent/runs/{runId}
```

## 4. 重放事件

```http
GET /api/agent/runs/{runId}/events?after=0
```

`after` 是 Run 内的事件 `sequence`。返回值是已持久化事件的 SSE 快照，不会永久保持连接。

## 5. 批准或拒绝 Action

```http
POST /api/agent/approvals/{approvalId}/decide
Content-Type: application/json
```

```json
{
  "decision": "approved",
  "decided_by": "user-001",
  "decision_note": "确认执行"
}
```

约束：

```text
1. decision 只能是 approved 或 denied。
2. decided_by 必须是当前 AgentSession 的真实用户。
3. approval 只能决定一次。
4. approved 后仍会重新加载最新业务状态并再次执行 PreAction。
5. Action 最终通过既有 CropFlow Service / PlanOrchestrator 执行。
```

当前 CropFlow API 尚未接入正式认证中间件，因此 `user_id / decided_by` 只代表受信调用方传入的执行上下文，不能作为生产身份凭证。生产部署必须由认证层注入当前用户，并移除客户端任意指定身份的能力。

## 6. 查询 Runtime Ontology

```http
GET /api/agent/ontology
```

返回当前角色、Object Type 与 Action Contract，便于前端、测试和 eval 核对 Runtime 实际暴露面。

## 7. 错误格式

Runtime 边界错误使用：

```json
{
  "detail": {
    "code": "role_not_assigned",
    "message": "User user-001 is not assigned agent role reviewer."
  }
}
```

Tool 执行边界使用结构化结果：

```text
rejected  Runtime 拒绝执行
failed    无副作用 Tool 确定失败
unknown   Side-effect Tool 结果不确定，禁止自动重试
```

上述结果会写入 ToolCall、AgentEvent 与 AuditRecord，并在下一轮作为 Tool Result 回注模型。Tool 失败不一定导致 Run 失败；只有 Provider、Context、持久化或迭代上限等 Runtime 自身无法继续的错误才写入 `run_failed`。

Provider 与 Run 保护错误包括：

```text
provider_authentication_error / provider_quota_exhausted
provider_request_error / provider_protocol_error
provider_retry_exhausted
run_execution_timeout
run_token_budget_exceeded
run_cost_budget_exceeded
```

`run_failed` Event 增加 `details`，例如重试耗尽时包含 `attempts / cause_code / status_code / retryable`，预算失败时包含使用量和预算快照。`model_call_completed` 包含 `usage_totals / provider_attempt_count / runtime_budget`。这些字段用于审计和监控，不应把 Provider 错误消息原样展示给普通用户。

当前 `POST /runs` 和 `/runs/stream` 仍在 API 请求进程中执行。目标态 202 Accepted + Durable Job API 仅记录在 `docs/architecture/agent-runtime-durable-execution.md`，尚未实现。
