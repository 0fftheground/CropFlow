# Current Memory

## Current Phase

工作相位：`P2` - 核心工程骨架与最小实现  
Roadmap 对应阶段：已具备从 `T1` 设计收口进入 `T2` 工程实现的条件

## Phase Goal

在已冻结的杂草防治样板闭环契约基础上，启动后端工程骨架、数据库迁移和首条样板链路实现，优先打通杂草防治全链路的最小可运行后端闭环。

## Progress

- 杂草主链路的接口契约、返回分支承接对象、复核规则和追溯字段已同步到 `docs/api`、`docs/model`、`docs/workflow`。
- `CalendarItem / TaskIntent / FarmingTask` 的 `parentTaskId / sourceExecutionId / sourceExecutionRecordId`，以及 `ReviewRequest.decisionPayload.contextRefs` 已冻结为正式口径。
- 已补齐 `docs/model/er-diagram.md`、`src/sql/20260521_core_schema_consolidated.sql`、`src/sql/migrations/v1/001~006` 和 `docs/planning/p2-v1-migration-*.md`，第一版 migration 边界已明确。
- 第一条样板链路范围已确认覆盖杂草防治整个环节，不只茎叶除草。
- 已新增 `docs/planning/p2-backend-weed-implementation-breakdown.md`，P2 后端实现拆分已形成。

## Remaining

- 搭建 `FastAPI + SQLAlchemy + Alembic` 最小后端工程骨架。
- 将第一版核心对象落成 ORM 和 Repository。
- 接入杂草 6 个算法接口的 adapter、入参组装和结果映射。
- 实现 `SurveyResultRecorded`、`ReviewRequestResolved` 等关键 handler，并打通 `TaskIntent -> ReviewRequest -> FarmingTask -> OperationPlan`。

## Blockers

- 当前仓库仍只有文档和 SQL，尚未创建后端工程和代码层数据模型。
- `DeviceCommand`、`InventoryItem / InventoryTransaction`、`workflowKey*` 落库仍按第一版 deferred 处理。
- `stageCode` 完整枚举和更广泛的 `taskSubtype` 收敛延后到后续扩展阶段统一处理。

## Next Step

优先按 `docs/planning/p2-backend-weed-implementation-breakdown.md` 启动后端工程骨架，先完成 Alembic 环境、核心 ORM、调查结果事件入口和杂草诊断 adapter 的第一批实现。

## Last Updated

`2026-05-21`
