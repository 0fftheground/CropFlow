# 2026-07-18 CropFlow Agent Runtime Integration

## Summary

将原先只存在于独立 `business-agent-slice` 的 Runtime 机制真正接入 CropFlow 后端。新的 Runtime 使用真实 `PlantingPlan` 及关联业务对象构建上下文，并通过现有 QueryService、Domain Service 和 `PlanOrchestrator` 执行业务 Action。

## Code Changes

- 新增 `app/agent_runtime/`：Action Contract、Context Builder、provider adapter、执行 loop、PreAction、approval 和 tool result 回注。
- 新增 `app/models/agent_runtime.py` 与 `AgentRuntimeRepository`。
- 新增 Alembic / SQL migration `015_create_agent_runtime_tables`。
- 新增 `/api/agent` 下的 Run、SSE、event replay、approval 和 ontology API。
- 新增 `scripted` 本地 provider 和 `openai_compatible` Chat Completions provider。
- 新增用户 `agent_roles`、context limit、provider 和 max iteration 配置。
- 增加 tool call id 冲突校验、终态调用幂等和 approval 行锁，避免重复模型输出或并发批准触发二次执行。

## Business Logic Changes

```text
1. Business Agent 现在可以读取真实计划、任务和复核上下文。
2. 模型只能在 Runtime 计算出的 available actions 中选择动作。
3. complete_farming_task 和 resolve_review_request 在批准前不产生业务副作用。
4. 批准后重新读取最新业务状态并再次 PreAction。
5. ReviewRequest 处理仍通过 PlanOrchestrator 回到原业务闭环。
6. Agent Runtime 不成为第二套 PlantingPlan / Task / Review 状态系统。
```

## Affected Areas

```text
FastAPI routes and dependencies
SQLAlchemy metadata and repositories
PostgreSQL migrations
PlantingPlan / FarmingTask / ReviewRequest query projection
TaskExecutionService / ReviewRequestService adapters
runtime configuration and deployment environment
```

## Tests

```text
227 passed, 1 skipped
```

覆盖：

```text
查询 Action loop 和 tool result 回注
写 Action 等待批准
批准后执行
批准后的最新业务状态复核
observer 越权动作拒绝
OpenAI-compatible tool call 解析与 tool role 回注
Tool failed / unknown 结果回注与副作用自动重试阻断
Run API、Approval API、SSE 和 event replay
ORM metadata 注册
既有 CropFlow 全量回归
Eval Dataset 唯一性、Approval Grader 和审批前副作用 Hard Gate
```

## DeepSeek Live Verification

2026-07-18 使用 `.env` 中的真实 DeepSeek API key 和 `deepseek-v4-pro` 完成：

```text
普通 Chat Completion：通过
真实 get_task_detail tool call：通过
tool call id / reasoning_content 保留：通过
tool result 回注并生成最终回答：通过
真实模型 + AgentRuntime 只读两轮 Action loop：通过
真实模型提出 complete_farming_task 后进入 waiting_approval：通过
批准前业务副作用：0
```

联调使用内存业务 Repository 验证 Runtime 协议与安全门；没有连接或修改目标 CropFlow 数据库。

## Model Eval Evidence

同日补充可复现的模型 Eval：

```text
Dataset: evals/agent_runtime/scenarios.json
Runner: scripts/run_agent_runtime_eval.py
Business Data: Mock
Target Database: not connected
Models: deepseek-v4-flash / deepseek-v4-pro
```

本文件中的六场景首轮结果已被后续 Eval V2 扩展取代。当前正式 Regression 为 7 个 P0 场景、每场景 10 次，并显式记录 Thinking、Token usage、成本、p50 / p95 延迟和多 Tool Calls；详细当前结果见 `docs/change-notes/2026-07-18-agent-runtime-eval-v2.md`。

历史六场景首轮结果：

| Model | Pass | Hard Gate Violation | Avg Latency | p95 Latency |
|---|---:|---:|---:|---:|
| deepseek-v4-flash | 5 / 6 | 0 | 5,968 ms | 8,523 ms |
| deepseek-v4-pro | 5 / 6 | 0 | 6,843 ms | 11,264 ms |

在 parallel query batch 版本上，对 `operator_completion_requires_approval` 追加 3 次重复后，两模型均为 2 / 3；合并首轮同场景后 V4-Flash 为 3 / 4、V4-Pro 为 2 / 4。所有真实模型运行均保持审批前副作用为 0。

详细过程、严格轨迹失败解释、复现命令和原始 JSON 报告见 `docs/development/agent-runtime-model-eval.md`。

## Remaining Assumptions

- 当前未在真实数据库执行 migration 015，避免在未指定目标环境时修改已有数据环境。
- DeepSeek V4-Pro 基础 tool-calling 和 Runtime approval gate 已使用真实 API 验证；目标数据库真实业务数据 eval 尚未执行。
- DeepSeek V4-Flash / V4-Pro 已使用相同 Mock Dataset 做初步对比，但样本量和任务类型仍不足以形成全局模型选型结论。
- `scripted` provider 只用于本地开发和测试，不代表真实 Agent 智能效果。
- 当前 SSE 在请求进程内执行；durable worker 和 stuck-run recovery 仍是生产演进项。
- 当前角色来自 `cf_user.metadata.agent_roles`，正式部署仍需接入真实 IAM 和数据范围。

## Manual Review Checklist

```text
1. 在目标数据库执行 alembic upgrade head，并核对 7 张 cf_agent_* 表。
2. 给联调用户配置 observer / operator / reviewer 角色。
3. 在目标数据库配置联调用户后，分别回放查询、任务完成和复核处理；批准前后核对真实业务状态。
4. 核对 approval 前后 FarmingTask / ReviewRequest 没有越权或提前变化。
5. 检查 AgentEvent、AgentToolCall 和 AgentAuditRecord 的 trace 是否完整。
```

## Related Documents

- `docs/architecture/agent-runtime.md`
- `docs/api/agent_runtime_api.md`
- `docs/decisions/012-agent-runtime-business-state-boundary.md`
