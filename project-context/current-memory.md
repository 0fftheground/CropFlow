# Current Memory

## Current Phase

工作相位：`P2` - 核心工程骨架与最小实现  
Roadmap 对应阶段：`T2` 工程实现；后端样板闭环已基本收口，当前重点转为气象 / 生育期运行期支撑与 P3 病虫害输入链路补齐

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
- 已补 `Farm` 维护能力：新增 `/api/farms` 的创建 / 列表 / 详情 / 更新接口，以及 `FarmService` / `FarmQueryService`；`Farm` 结构化字段现包含 `province`、`city`、`district_county`、`adcode`、`external_farm_id`。
- 已补 `cf_farm` 新字段迁移：`cf007_farm_region`、`cf008_farm_external_id`；本地库已升级并写入两个真实农场（岳麓基地、峨桥基地）的区域信息和 `external_farm_id`。
- 已接入真实 `HttpWeatherProvider`：后端现在会按 `observed / forecast / climatology` 组装逐日天气；`getAvgTemAndPre` 用 `farmId`，`getForecast10DaysBeforeAnd15DaysAfter` 当前联调确认仍需 `farmID`。
- 已完成岳麓基地真实天气接口联调：`getAvgTemAndPre` 在短日期范围下可返回逐日结果，但不包含“今天”数据；`as_of_date` 当天已改由逐日预报接口补齐。相关 weather/farm/stage 回归已通过。
- 已补运行期天气驱动骨架：新增 `DailyWeatherCheckJob`、scheduler 接线和 `WeatherUpdated` 事件幂等生成；天气变化现在可进入 Plan Orchestrator。
- 已补病虫害每日更新所需的气象输入拼装：逐日天气继续走农场逐日预报，72 小时逐小时天气改走 `getForecast10DaysBeforeAndAfter`，台风预警使用 `weather_api.pdf` 中的 `/Zoomlion/alert`；`daily-update-survey` payload / client / mock / 测试已补齐，但还未把返回结果真正落成新的 CalendarItem。
- 已把生育期 handoff 文档改成“规则包驱动”的 vNext 草案：算法接口建议只返回 `threshold_rule`，后端负责积温累计、生育期推进和业务阶段日期推导；并新增 `docs/生育期code_list.xlsx` 作为原始阶段 code 参考。
- 已开始把后端实现切到新生育期口径：`StageManagementService` 现支持 `PlanCreated / PlanKeyInfoChanged` 时调算法拿规则包，`WeatherUpdated` 时复用已有规则包在后端本地重算累计积温、当前阶段和派生 `stage_timeline`；相关定向测试已通过。

## Remaining

- 前端页面尚未开发，真实前后端联调还未开始。
- 仍需由前端负责人基于 handoff 和 API contract 开始真实页面联调；当前不由后端侧直接开发前端页面。
- 如继续开发植保病虫害相关农事任务，应作为 `P3` 多方向扩展启动，而不再并入当前 `P2`。
- P3 病虫害调查每日更新仍未闭环；当前只完成气象输入拼装和 `/pestDisease/survey/daily-update-survey` 调用能力，仍需把返回的 `new_emergency / merged_into_regular / no_new_event` 映射成具体的病虫调查 CalendarItem / taskSubtype。
- 气象运行期管理仍不完整：
  - 现在的 `DailyWeatherCheckJob` 还只是按天气行生成 `WeatherUpdated`，尚未落独立的计划级天气快照表；
  - `observed / forecast / climatology` 的存储、回刷窗口、历史修正策略还未设计成正式数据结构；
  - `climatology` 当前仍是 provider 侧按需拼装，尚未单独定义低频缓存或版本策略；
  - 天气变化检测还未区分“仅未来 forecast 变化”和“历史 observed 回刷修正”两种重算路径。
- 积温管理只做到第一版：
  - 当前已能基于规则包和天气序列重算累计积温，但仍是从 `sowing_date` 重扫天气，不是真正按 `last_calculated_date` 的增量引擎；
  - `CropThermalTimeState` 还未补充逐日积温明细、跨阈值命中记录和更细的审计信息；
  - 规则版本切换后的重算策略、历史天气修正后的全量回放策略还未单独收口。
- 生育期管理仍未彻底完成：
  - `ActualStageRecorded` 还没有接入新的“规则包 + 本地积温”路径；
  - `StageChanged` 还未作为独立业务事件落地；
  - 当前内部仍临时沿用 `seedling / tillering / pokou / heading / maturity` 粗粒度 code；
  - 算法端后续若按 `docs/生育期code_list.xlsx` 返回原始阶段 code，后端还需新增“raw stage code -> business milestone(`tillering/pokou/heading/maturity`)" 的映射层；
  - 当前实现默认可派生完整 `stage_timeline`，但算法侧已确认后续可能只返回必要原始阶段点，因此 snapshot 结构和映射规则还要再收敛。
- DeviceCommand、InventoryItem / InventoryTransaction 落库（按第一版 deferred 处理）。
- stageCode 完整枚举、业务阶段映射配置和更广泛的 taskSubtype 收敛延后到后续扩展阶段。

## Blockers

- 前端尚未进入实现，当前无法完成真实页面联调验收。
- 真实杂草算法服务已通过本地集成测试和 trace 脚本验证；后续仍需在前后端真实联调中继续观察返回语义稳定性。
- 外部气象接口当前存在契约不一致：平均接口使用 `farmId` 且不返回“今天”数据；逐日预报接口文档已更新为 `farmId`，但真实服务当前仍要求 `farmID`。
- 生育期接口契约刚切到 vNext 草案：后端代码已开始按“规则包驱动”调整，但算法侧最终是否返回完整时间线、必要原始阶段点集合以及 `生育期code_list.xlsx` 对应 code 映射规则还未最终冻结。

## Next Step

后端侧下个 session 优先做两件事：一是把生育期 raw stage code 方案收口，明确算法到底返回“完整时间线”还是“必要阶段点”，再设计 `raw code -> business milestone` 映射与 snapshot 结构；二是把气象 / 积温运行期做成正式方案，补天气快照存储、增量积温更新、历史回刷重算和 `daily-update-survey` 结果落 CalendarItem 的闭环。

## Last Updated

`2026-05-29`
