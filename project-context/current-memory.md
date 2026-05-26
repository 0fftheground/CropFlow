# Current Memory

## Current Phase

工作相位：`P2` - 核心工程骨架与最小实现  
Roadmap 对应阶段：`T2` 工程实现；后端样板闭环已基本收口，前端联调待启动

## Phase Goal

在已冻结的杂草防治样板闭环契约基础上，完成后端工程骨架、数据库迁移、杂草防治最小可运行闭环和前端联调所需的 API / contract。

## Progress

- 后端工程骨架已搭建完毕：FastAPI + SQLAlchemy + Alembic + Uvicorn。
- 已建 16 个核心 ORM 模型（Farm / Field / CodeDict / User / RiceVariety / PlantingPlan / PlantingPlanFieldRelation / StagePredictionSnapshot / EventRecord / CalendarItem / TaskIntent / ReviewRequest / FarmingTask / OperationPlan / Execution / ExecutionRecord），对应 v1 migration 001~006。
- Repository 层已完成（PlantingPlanRepository / CalendarItemRepository / TaskIntentRepository / FarmingTaskRepository / OperationPlanRepository / ExecutionRepository / ExecutionRecordRepository / ReviewRequestRepository / EventRecordRepository 等）。
- Plan Orchestrator 已实现，注册 5 个 EventHandler：PlanCreated / PlanKeyInfoChanged → PlanCalendarRefreshHandler；TaskDueCheckTriggered → TaskDueCheckTriggeredHandler；SurveyResultRecorded → SurveyResultRecordedHandler（pre-treatment / rice-safety / control-effect 三条分支）；ReviewRequestResolved → ReviewRequestResolvedHandler（approve / reject / no_action / need_more_info 四种决策）；ExecutionCompleted → ExecutionCompletedHandler（post-treatment survey scheduling）。
- 杂草诊断算法 adapter 已实现 HttpWeedDiagnosisClient（含 soil_treatment_diagnosis 等 5 个核心算法入口）+ MockWeedDiagnosisClient + MockWeatherProvider，支持独立测试。
- SurveyDateRecommendationService 已完整实现（pre-treatment / post-treatment / recontrol / followup / service evaluation 五种日历项创建）。
- 土壤封闭链路已调整为 TaskIntent + ReviewRequest 人工审核，通过 ReviewRequestResolved 后再生成 FarmingTask / OperationPlan。
- TaskGenerationService 已实现；SurveyDateRecommendationJob / TaskDueCheckJob 已接入 BackgroundJobScheduler，可通过 `python -m app.jobs.runner` 或 `scripts/start-dev.ps1 -Mode scheduler` 独立运行。
- API handler 已覆盖创建计划、计划查询更新、调查结果录入、复核决策、执行完成，并补齐了计划事件记录、任务详情聚合、复核详情聚合、字典查询和品种模糊查询等前端联调入口。
- `plan_code` 已改为后端生成；`culti_type_code`、`planting_method_code`、`variety_id` 已有对应查询或选择口径。
- 已补统一日志能力：API 请求摘要、`X-Request-ID`、400/500 上下文、编排事件日志和外部杂草算法请求/响应摘要。
- 服务效果评估最小链路已完成：`service_effect_evaluation` 不满意时直接生成 `service_effect_survey` 正式任务，现场确认录入后结束链路，不单独引入 `Evaluation` 对象。
- 已补真实杂草算法失败场景覆盖、可选真实接口集成测试骨架、P2 后端 runbook 和 trace 脚本。
- 已整理前端专项 handoff 和 API contract，并对 docs / planning / project-context 做了一轮精简和重组。
- 已补本地开发数据脚本、端到端 trace 脚本和土壤封闭专项 trace 脚本；本 session 已完成土壤封闭完整链路验证。
- 最近一次全量测试通过为 `54 passed, 1 skipped`。
- SQL 文件从 `src/sql/` 迁移到 `database/sql/`，已对齐所有文档引用路径。
- 已新增 Codex / Claude Code 共享上下文入口：`docs/ai/README.md`，并新增 `CLAUDE.md` 薄入口。

## Remaining

- 前端页面尚未开发，真实前后端联调还未开始。
- 仍需基于真实数据库 + 真实杂草算法服务跑一次完整演示链路，并沉淀最终联调结论。
- 如继续开发植保病虫害相关农事任务，应作为 `P3` 多方向扩展启动，而不再并入当前 `P2`。
- DeviceCommand、InventoryItem / InventoryTransaction 落库（按第一版 deferred 处理）。
- stageCode 完整枚举和更广泛的 taskSubtype 收敛延后到后续扩展阶段。

## Blockers

- 前端尚未进入实现，当前无法完成真实页面联调验收。
- 真实杂草算法服务虽然已有联调地址 `http://47.99.129.235:3319`，但仍需要最终确认线上返回语义与样例数据的稳定性。

## Next Step

优先启动前端样板页开发与联调；如果继续做纯后端业务扩展，则将病虫害相关农事任务作为 `P3` 的第一条植保扩展链路单独推进。

## Last Updated

`2026-05-26`
