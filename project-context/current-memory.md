# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入  
Roadmap 对应阶段：`T2` 工程实现后段并开始进入 `T3` 扩展接入；后端样板闭环已基本收口，当前重点转为气象 / 生育期运行期支撑与 P3 病虫害输入链路补齐

## Phase Goal

在已冻结的杂草防治样板闭环契约基础上，完成后端工程骨架、数据库迁移、杂草防治最小可运行闭环和前端联调所需的 API / contract。

## Progress

- 后端工程骨架已搭建完毕：FastAPI + SQLAlchemy + Alembic + Uvicorn。
- 已建 19 个核心 ORM 模型（Farm / Field / CodeDict / User / RiceVariety / PlantingPlan / PlantingPlanFieldRelation / StagePredictionSnapshot / CropStageState / CropThermalTimeState / WeatherSnapshot / EventRecord / CalendarItem / TaskIntent / ReviewRequest / FarmingTask / OperationPlan / Execution / ExecutionRecord），对应 v1 migration 001~009。
- Repository 层已完成（PlantingPlanRepository / CalendarItemRepository / TaskIntentRepository / FarmingTaskRepository / OperationPlanRepository / ExecutionRepository / ExecutionRecordRepository / ReviewRequestRepository / EventRecordRepository 等）。
- Plan Orchestrator 已实现核心事件处理：PlanCreated / PlanKeyInfoChanged / WeatherUpdated / ActualStageRecorded → StageRefreshHandler + PlanCalendarRefreshHandler；StageChanged → PlanCalendarRefreshHandler；TaskDueCheckTriggered → TaskDueCheckTriggeredHandler；SurveyResultRecorded → SurveyResultRecordedHandler（pre-treatment / rice-safety / control-effect 三条分支）；ReviewRequestResolved → ReviewRequestResolvedHandler（approve / reject / no_action / need_more_info 四种决策）；ExecutionCompleted → ExecutionCompletedHandler（post-treatment survey scheduling）。
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
- 最近一次全量测试通过为 `83 passed, 1 skipped`。
- SQL 文件从 `src/sql/` 迁移到 `database/sql/`，已对齐所有文档引用路径。
- 已新增 Codex / Claude Code 共享上下文入口：`docs/ai/README.md`，并新增 `CLAUDE.md` 薄入口。
- P3 病虫害调查任务生成已开始接入：当前按 `docs/api/pestDisease_survey_window_api.md` 契约解析 `init-regular-survey`，新增 client / mock client，按计划 metadata 中的 `pestDisease.growth_stage` 与 `pestDisease.level1_of_year` 生成 `plant_protection.regular_disease_pest_survey` CalendarItem；到期后沿用 TaskDueCheckJob 生成正式调查 FarmingTask。
- 已开始接入生育期管理能力：新增 `docs/api/growth_stage_prediction_api.md`，补齐 `CropStageState` / `CropThermalTimeState` ORM 与 repository，新增 `StageManagementService`、mock / http stage prediction client，并在 `PlanCreated / PlanKeyInfoChanged` 链路先刷新生育期快照后再刷新日历；病虫害常规调查在缺少 `growth_stage` metadata 时可回退读取最新 `StagePredictionSnapshot.stageTimeline`。
- 已补 `Farm` 维护能力：新增 `/api/farms` 的创建 / 列表 / 详情 / 更新接口，以及 `FarmService` / `FarmQueryService`；`Farm` 结构化字段现包含 `province`、`city`、`district_county`、`adcode`、`external_farm_id`。
- 已补 `cf_farm` 新字段迁移：`cf007_farm_region`、`cf008_farm_external_id`；本地库已升级并写入两个真实农场（岳麓基地、峨桥基地）的区域信息和 `external_farm_id`。
- 已接入真实 `HttpWeatherProvider`：后端现在会按 `observed / forecast / climatology` 组装逐日天气；`getAvgTemAndPre` 用 `farmId`，`getForecast10DaysBeforeAnd15DaysAfter` 当前联调确认仍需 `farmID`。
- 已完成岳麓基地真实天气接口联调：`getAvgTemAndPre` 在短日期范围下可返回逐日结果，但不包含“今天”数据；`as_of_date` 当天已改由逐日预报接口补齐。相关 weather/farm/stage 回归已通过。
- 已补运行期天气驱动骨架：新增 `DailyWeatherCheckJob`、scheduler 接线和 `WeatherUpdated` 事件幂等生成；天气变化现在可进入 Plan Orchestrator。
- 已补病虫害每日更新所需的气象输入拼装：逐日天气继续走农场逐日预报，72 小时逐小时天气改走 `getForecast10DaysBeforeAndAfter`，台风预警使用 `weather_api.pdf` 中的 `/Zoomlion/alert`；`daily-update-survey` payload / client / mock / 测试已补齐，但还未把返回结果真正落成新的 CalendarItem。
- 已把生育期 handoff 文档改成“规则包驱动”的 vNext 草案：算法接口建议只返回 `threshold_rule`，后端负责积温累计、生育期推进和业务阶段日期推导；并新增 `docs/生育期code_list.xlsx` 作为原始阶段 code 参考。
- 已开始把后端实现切到新生育期口径：`StageManagementService` 现支持 `PlanCreated / PlanKeyInfoChanged` 时调算法拿规则包，`WeatherUpdated` 时复用已有规则包在后端本地重算累计积温、当前阶段和派生 `stage_timeline`；相关定向测试已通过。
- 已确认当前业务阶段 raw code 映射：`tillering=21`、`pokou=51`、`heading=58`、`maturity=89`；后端 `stage_timeline` 已开始保留这些 raw code，解析侧兼容 raw/business 两种阶段标识。
- 已确认算法若补充阶段点返回，只承诺返回当前业务必需的部分节点，不承诺完整生育期时间线；后续可随新增农事需求继续扩展。
- 已补农场年度 `WeatherSnapshot` 存储与 migration 009；同一 Farm 同一年同一天气行可跨 PlantingPlan 复用；`WeatherUpdated` 幂等维度改为包含 `dataHash`，同一 `dataVersion` 下 payload 变化也能触发新事件。
- 已补最小气象治理审计：同一 Farm / 年 / 日期 / sourceType 只保留一个 active `WeatherSnapshot`，旧快照保留并记录 superseded 链路；`WeatherUpdated.payload` 记录 `weatherChangeType` 与上一版快照引用。
- 已补 `ActualStageRecorded` / `StageChanged` 最小事件闭环：人工阶段录入接口 `POST /api/planting-plans/{plantingPlanId}/actual-stages` 按 `code: date` 生成事件，编排链路更新 `CropStageState`，阶段变化会记录 `StageChanged`，并进入日历刷新 handler。
- 已补 `DailyWeatherCheckJob` 失败重试 2 次；`WeatherUpdated` 对新的 observed 日期可走基于 `lastCalculatedDate` 的增量积温更新，历史修正或 forecast 变化仍回退全量重算。
- 已完成病虫害防治方案 4 个接口接入：`generate-theory-control-plan`、`adjust-control-window`、`get-merge-spray-suitability-range`、`merge-control-plan`。调查结果录入后，单类型场景会生成待审核 `TaskIntent + ReviewRequest`，常规与突发并存时会走合并链路。
- 已补病虫害防治的 `spray_suitability_data` 组装能力；`dy_ws` 由后端基于天气接口返回的 `wins / pre / rh / tAvg` 自行计算。
- 已补 `cf_crop_stage_dict` 支撑的生育期 raw stage 字典读取；`StageManagementService` 现在优先读表，查不到再回退默认常量。
- 已补生育期阈值算法新契约适配：后端现调用 `growth-stage-gdd-thresholds`，并按本地品种码值到算法码值做映射（`cultiType / apprCultiType / subsType / maturType`）。
- 已补第一版可观察性：日志正式落盘到 `logs/`，上游生育期算法错误可语义化提示，且新增 `GET /api/planting-plans/{plantingPlanId}/debug-snapshot` 聚合排障接口。
- 已补前端 handoff 文档收口：`plan_detail` 直接承载预备农事项 / 正式任务 / 待审核事项 / 生育期区块，`calendar_list` 下调为可选页，`task_detail` / `survey_entry` / `review_request` 的页面流转和页面职责已重新梳理。
- 已修正真实天气联调口径：本地联调农场需依赖 `Farm.external_farm_id` 调真实天气；`HttpWeatherProvider` 已按真实接口行为将 daily forecast 窗口收口为“当天起 14 天”，并对 observed `temAvg=null` 增加邻近日回退。
- 本地联调用 `planting_plan_id=9` 已补齐预备农事项、正式任务、待审核事项和生育期数据；当前可用真实天气回填的最新生育期快照为 `prediction_source=manual_backfill_real_weather`。

## Remaining

- 前端页面尚未开发，真实前后端联调还未开始。
- 仍需由前端负责人基于 handoff 和 API contract 开始真实页面联调；当前不由后端侧直接开发前端页面。
- 如继续开发植保病虫害相关农事任务，应作为 `P3` 多方向扩展启动，而不再并入当前 `P2`。
- P3 病虫害调查每日更新仍未彻底验收；接口和 `CalendarItem` 闭环已接入，但还需要在真实算法和前端联调中继续验证 `new_emergency / merged_into_regular / no_new_event` 语义与页面展示。
- 气象运行期管理仍不完整：
  - 现在已有农场年度 `WeatherSnapshot`，支持同 Farm 同年跨计划复用，但还不是全局气象主数据；
  - `observed / forecast / climatology` 的回刷窗口、历史修正策略还未完整自动化；
  - `climatology` 当前仍是 provider 侧按需拼装，尚未单独定义低频缓存或版本策略；
  - `forecast` 真实接口的日期边界与文档存在差异，当前已按返回行为修正 provider，但仍需继续确认上游契约是否稳定。
- 积温管理只做到第一版：
  - 当前已能对新的 observed 日期按 `last_calculated_date` 增量推进；同日修正、历史回刷和 forecast 变化仍走全量回放；
  - `CropThermalTimeState` 还未补充逐日积温明细、跨阈值命中记录和更细的审计信息；
  - 规则版本切换后的重算策略、历史天气修正后的全量回放策略还未单独收口。
- 生育期管理仍未彻底完成：
  - `ActualStageRecorded` 已有正式 API 入口并能修正 `CropStageState`，但人工录入表单联调还未开始；
  - `StageChanged` 已作为事件记录落地，但其影响策略当前仍复用日历刷新 handler，尚未拆独立 StageChangeImpactPolicy；
- 当前内部主口径仍是 `seedling / tillering / pokou / heading / maturity` 业务阶段；完整 raw stage points 已进入 snapshot 和对外接口，但更多业务节点与更多规则消费场景还未扩展；
  - 当前实现仍由后端派生 `stage_timeline`；若后续算法侧实际返回必要原始阶段点，snapshot 合并策略和字段结构还要再收敛。
- DeviceCommand、InventoryItem / InventoryTransaction 落库（按第一版 deferred 处理）。
- stageCode 完整枚举、业务阶段映射配置和更广泛的 taskSubtype 收敛延后到后续扩展阶段。

## Blockers

- 前端尚未进入实现，当前无法完成真实页面联调验收。
- 真实杂草算法服务已通过本地集成测试和 trace 脚本验证；后续仍需在前后端真实联调中继续观察返回语义稳定性。
- 外部气象接口当前仍存在契约偏差：平均接口使用 `farmId` 且不返回“今天”数据；逐日预报接口真实服务当前仍要求 `farmID`，且实际覆盖窗口为“前10天 + 当天起14天”。
- 本地联调若未配置 `Farm.external_farm_id`，真实天气接口会直接返回空数组；后续 seed / runbook 仍需继续收口这条依赖。

## Next Step

下个 session 优先做三件事：一是继续跟前端按新的 handoff 文档做真实页面联调，优先验证 `plan_detail / task_detail / review_request / survey_entry`；二是继续收口生育期运行期策略和完整 raw stage code 消费边界；三是继续验证病虫害调查每日更新与防治方案链路在真实算法下的返回语义和页面展示。

## Last Updated

`2026-06-02`
