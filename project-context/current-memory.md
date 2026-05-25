# Current Memory

## Current Phase

工作相位：`P2` - 核心工程骨架与最小实现  
Roadmap 对应阶段：已具备从 `T1` 设计收口进入 `T2` 工程实现的条件

## Phase Goal

在已冻结的杂草防治样板闭环契约基础上，启动后端工程骨架、数据库迁移和首条样板链路实现，优先打通杂草防治全链路的最小可运行后端闭环。

## Progress

- 后端工程骨架已搭建完毕：FastAPI + SQLAlchemy + Alembic + Uvicorn。
- 已建 16 个核心 ORM 模型（Farm / Field / CodeDict / User / RiceVariety / PlantingPlan / PlantingPlanFieldRelation / StagePredictionSnapshot / EventRecord / CalendarItem / TaskIntent / ReviewRequest / FarmingTask / OperationPlan / Execution / ExecutionRecord），对应 v1 migration 001~006。
- Repository 层已完成（PlantingPlanRepository / CalendarItemRepository / TaskIntentRepository / FarmingTaskRepository / OperationPlanRepository / ExecutionRepository / ExecutionRecordRepository / ReviewRequestRepository / EventRecordRepository 等）。
- Plan Orchestrator 已实现，注册 5 个 EventHandler：PlanCreated / PlanKeyInfoChanged → PlanCalendarRefreshHandler；TaskDueCheckTriggered → TaskDueCheckTriggeredHandler；SurveyResultRecorded → SurveyResultRecordedHandler（pre-treatment / rice-safety / control-effect 三条分支）；ReviewRequestResolved → ReviewRequestResolvedHandler（approve / reject / no_action / need_more_info 四种决策）；ExecutionCompleted → ExecutionCompletedHandler（post-treatment survey scheduling）。
- 杂草诊断算法 adapter 已实现 HttpWeedDiagnosisClient（含 soil_treatment_diagnosis 等 5 个核心算法入口）+ MockWeedDiagnosisClient + MockWeatherProvider，支持独立测试。
- SurveyDateRecommendationService 已完整实现（pre-treatment / post-treatment / recontrol / followup / service evaluation 五种日历项创建）。
- 土壤封闭链路已调整为 TaskIntent + ReviewRequest 人工审核，通过 ReviewRequestResolved 后再生成 FarmingTask / OperationPlan。
- TaskGenerationService 已实现；SurveyDateRecommendationJob / TaskDueCheckJob 已接入 BackgroundJobScheduler，可通过 `python -m app.jobs.runner` 或 `scripts/start-dev.ps1 -Mode scheduler` 独立运行。
- API handler 已实现：health / planting-plans / review-requests / tasks，已覆盖创建计划、计划查询更新、调查结果录入、复核决策、执行完成等首批业务入口。
- 已补本地开发数据脚本、端到端 trace 脚本和土壤封闭专项 trace 脚本；本 session 已完成土壤封闭完整链路验证。
- API / service / repository / job 首批测试已落地，最近一次全量测试通过为 `35 passed`。
- SQL 文件从 `src/sql/` 迁移到 `database/sql/`，已对齐所有文档引用路径。
- 已新增 Codex / Claude Code 共享上下文入口：`docs/ai/README.md`，并新增 `CLAUDE.md` 薄入口。

## Remaining

- 杂草真实算法接口仍需补完整集成测试和失败场景覆盖，尤其是外部 400 / 超时 / 字段缺失时的可排查日志。
- 目前缺少工程级接口调用日志、关键业务节点日志和外部算法请求/响应日志。
- 真实数据库 + 真实算法服务参与的端到端联调链路需整理为可重复执行说明。
- 更完整的单元测试 / 集成测试覆盖。
- DeviceCommand、InventoryItem / InventoryTransaction 落库（按第一版 deferred 处理）。
- stageCode 完整枚举和更广泛的 taskSubtype 收敛延后到后续扩展阶段。

## Blockers

- 已拿到杂草诊断联调地址 `http://47.99.129.235:3319`，但真实接口返回、异常语义、超时策略和日志留痕仍需收敛。
- 本地数据库已可用，但可复用的联调启动 / 验证说明还需要整理。

## Next Step

优先补统一日志能力：接口请求/响应摘要、400/500 完整上下文、外部杂草算法请求/响应、关键编排事件结果。随后整理本地联调说明，并补真实算法服务集成测试。

## Last Updated

`2026-05-25`
