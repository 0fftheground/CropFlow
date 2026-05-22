# Current Memory

## Current Phase

工作相位：`P2` - 核心工程骨架与最小实现  
Roadmap 对应阶段：已具备从 `T1` 设计收口进入 `T2` 工程实现的条件

## Phase Goal

在已冻结的杂草防治样板闭环契约基础上，启动后端工程骨架、数据库迁移和首条样板链路实现，优先打通杂草防治全链路的最小可运行后端闭环。

## Progress

- 后端工程骨架已搭建完毕：FastAPI + SQLAlchemy + Alembic + Uvicorn。
- 已建 15 个核心 ORM 模型（Farm / Field / CodeDict / User / RiceVariety / PlantingPlan / PlantingPlanFieldRelation / StagePredictionSnapshot / EventRecord / CalendarItem / TaskIntent / ReviewRequest / FarmingTask / OperationPlan / Execution / ExecutionRecord），对应 v1 migration 001~006。
- Repository 层已完成（PlantingPlanRepository / CalendarItemRepository / TaskIntentRepository / FarmingTaskRepository / OperationPlanRepository / ExecutionRepository / ExecutionRecordRepository / ReviewRequestRepository / EventRecordRepository 等）。
- Plan Orchestrator 已实现，注册 5 个 EventHandler：PlanCreated / PlanKeyInfoChanged → PlanCalendarRefreshHandler；TaskDueCheckTriggered → TaskDueCheckTriggeredHandler；SurveyResultRecorded → SurveyResultRecordedHandler（pre-treatment / rice-safety / control-effect 三条分支）；ReviewRequestResolved → ReviewRequestResolvedHandler（approve / reject / no_action / need_more_info 四种决策）；ExecutionCompleted → ExecutionCompletedHandler（post-treatment survey scheduling）。
- 杂草诊断算法 adapter 已实现 HttpWeedDiagnosisClient（5 个算法接口）+ MockWeedDiagnosisClient + MockWeatherProvider，支持独立测试。
- SurveyDateRecommendationService 已完整实现（pre-treatment / post-treatment / recontrol / followup / service evaluation 五种日历项创建）。
- TaskGenerationService 已实现，支持后台作业触发任务生成。
- API 路由骨架已搭建：health / planting-plans / review-requests / tasks。
- SQL 文件从 `src/sql/` 迁移到 `database/sql/`，已对齐所有文档引用路径。

## Remaining

- API 路由具体 handler 实现（planting_plans / review_requests / tasks 的 CRUD 和业务接口）。
- 杂草 6 个算法接口的真实集成测试与容错处理。
- 后台作业调度接入（SurveyDateRecommendationJob / TaskDueCheckJob）。
- 完整的单元测试 / 集成测试覆盖。
- DeviceCommand、InventoryItem / InventoryTransaction 落库（按第一版 deferred 处理）。
- stageCode 完整枚举和更广泛的 taskSubtype 收敛延后到后续扩展阶段。

## Blockers

- 杂草诊断算法服务需要外部部署或模拟端点才能完整端到端验证。
- API handler 层尚未实现，前端尚无法调用。
- 后台作业（cron / scheduler）未接入。

## Next Step

优先完成 API handler 层的核心路由实现（planting_plans CRUD + review_requests 提交/审批 + tasks 查询），然后打通第一条端到端测试链路（创建计划 → 生成日历 → 调查结果事件 → TaskIntent → 复核 → FarmingTask → OperationPlan）。

## Last Updated

`2026-05-22`
