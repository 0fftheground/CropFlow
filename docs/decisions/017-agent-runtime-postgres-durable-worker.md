# ADR 017 - Agent Runtime PostgreSQL Durable Worker

状态：Proposed  
日期：2026-07-18

## Context

当前 Agent Runtime 在 FastAPI 请求进程中执行。客户端断开、API 实例重启或进程崩溃会中断活跃 Run；等待 Approval 后的恢复也依赖新的 API 请求。多实例环境需要共享的 Job 领取、超时恢复和事件交付机制。

## Proposed Decision

第一版使用 PostgreSQL 持久 Job Queue，而不是立即引入 Celery、Redis 或 Kafka：

1. 新增 `cf_agent_job` 和 migration 016。
2. API 在同一数据库事务中创建 `AgentRun + AgentJob` 后立即返回。
3. 独立 Worker 使用 `FOR UPDATE SKIP LOCKED` 和有限 Lease 领取 Job。
4. Worker 使用 Heartbeat 续租；Watchdog 扫描过期 Lease 并按 Side Effect 状态决定重排或转人工核对。
5. Approval 决定后创建 `resume_run` Job，不保持原 Worker 常驻。
6. `AgentEvent` 继续作为事件 Source of Truth；多实例 SSE 按 sequence 从数据库重放，`LISTEN / NOTIFY` 只作为可选唤醒优化。
7. Job 交付采用 at-least-once；通过 Tool idempotency、状态复核和 unknown reconciliation 获得业务安全，不声称 exactly-once。

## Why Proposed

该方案复用 CropFlow 已有 PostgreSQL 和事务边界，运维增量最小，足以支撑当前规模。进入高吞吐、跨服务编排或更复杂调度后，再评估外部队列。

完整定义、状态机、故障矩阵和实施步骤见 `docs/architecture/agent-runtime-durable-execution.md`。本 ADR 尚未实现，待确认后进入 migration 和 Worker 开发。
