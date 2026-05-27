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
- 已补本地开发数据脚本、端到端 trace 脚本和土壤封闭专项 trace 脚本；本 session 已完成真实数据库 + 真实杂草算法服务下的杂草主链路和土壤封闭专项 trace 验证，记录位于 `project-context/session-log/e2e-traces/`。
- 最近一次全量测试通过为 `57 passed, 1 skipped`。
- SQL 文件从 `src/sql/` 迁移到 `database/sql/`，已对齐所有文档引用路径。
- 已新增 Codex / Claude Code 共享上下文入口：`docs/ai/README.md`，并新增 `CLAUDE.md` 薄入口。
- P3 病虫害调查任务生成已开始接入：当前按 `docs/api/pestDisease_survey_window_api.md` 契约解析 `init-regular-survey`，新增 client / mock client，按计划 metadata 中的 `pestDisease.growth_stage` 与 `pestDisease.level1_of_year` 生成 `plant_protection.regular_disease_pest_survey` CalendarItem；到期后沿用 TaskDueCheckJob 生成正式调查 FarmingTask。
- 已开始接入生育期管理能力：新增 `docs/api/growth_stage_prediction_api.md`，补齐 `CropStageState` / `CropThermalTimeState` ORM 与 repository，新增 `StageManagementService`、mock / http stage prediction client，并在 `PlanCreated / PlanKeyInfoChanged` 链路先刷新生育期快照后再刷新日历；病虫害常规调查在缺少 `growth_stage` metadata 时可回退读取最新 `StagePredictionSnapshot.stageTimeline`。

## Remaining

- 前端页面尚未开发，真实前后端联调还未开始。
- 仍需由前端负责人基于 handoff 和 API contract 开始真实页面联调；当前不由后端侧直接开发前端页面。
- 如继续开发植保病虫害相关农事任务，应作为 `P3` 多方向扩展启动，而不再并入当前 `P2`。
- P3 病虫害调查每日更新尚未接入；需要继续把气象接口映射到逐日天气、72 小时逐小时天气和台风预警输入后，再调用 `/pestDisease/survey/daily-update-survey` 生成突发或合并调查 CalendarItem。
- 生育期管理当前只完成初始化 / 计划关键字段变更两条触发链路；`WeatherUpdated`、`ActualStageRecorded`、`StageChanged` 的完整事件回路和后台 job 还未实现。
- DeviceCommand、InventoryItem / InventoryTransaction 落库（按第一版 deferred 处理）。
- stageCode 完整枚举和更广泛的 taskSubtype 收敛延后到后续扩展阶段。

## Blockers

- 前端尚未进入实现，当前无法完成真实页面联调验收。
- 真实杂草算法服务已通过本地集成测试和 trace 脚本验证；后续仍需在前后端真实联调中继续观察返回语义稳定性。

## Next Step

后端侧如继续推进 P3，下一步优先把生育期链路补到运行期：先接 `WeatherUpdated` / `ActualStageRecorded` 的 stage refresh 与 `StageChanged` 事件，再继续接入病虫害每日更新调查窗口所需的 weather provider / typhoon alert 映射；前端联调仍由前端负责人基于 P2 handoff 推进。

## Last Updated

`2026-05-27`
