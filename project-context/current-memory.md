# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入 + `P4` Agent Runtime 后端 MVP
Roadmap 对应阶段：`T2` 工程实现后段，并已进入 `T3` 植保 / 气象 / 生育期扩展联调

## Phase Goal

在已冻结的杂草样板闭环基础上，收口植保后端主链路、真实天气 / 生育期运行期支撑，并继续收口施肥方向 FDE / workflow / model 契约，为 `P3` 扩展接入准备稳定文档口径。

## Progress

- CropFlow 已接入真实 Business Agent Runtime 后端 MVP：
  - 新增 Session / Message / AgentRun / ToolCall / ApprovalRequest / AgentEvent / AuditRecord 持久化与 migration 015
  - Context Builder 每轮从真实 PlantingPlan、Stage、FarmingTask 和 ReviewRequest 构建 Object View
  - Available Action Resolver 按 observer / operator / reviewer、计划状态和当前任务 / 复核状态裁剪动作
  - 查询 Action 已接入真实 QueryService；完成任务与处理复核已接入现有 Service / PlanOrchestrator
  - 两个写 Action 均会进入 waiting_approval，批准后重新加载状态并再次 PreAction
  - Tool call 终态幂等、call id 冲突保护和 approval 行锁已补齐，避免重复模型输出或并发批准造成二次执行
  - 已提供 OpenAI-compatible provider、Run / SSE / approval / ontology API 和自动化测试
  - DeepSeek V4-Pro 真实 completion、tool call、tool result 回注、只读 Runtime loop 和写 Action approval gate 已完成基础联调
  - Agent Runtime Eval 已拆为 Development / Regression / Holdout；7 个 P0 Regression 场景各完成 10 次真实 DeepSeek V4-Flash / V4-Pro + Mock Business State 采样，结果为 67/70 与 70/70，Hard Gate 均为 0；修正 reviewer 必填参数提示后两模型各 10/10
  - Adapter 已显式配置 Thinking、Reasoning Effort 和 max output tokens，并在 AgentRun provider state 记录 prompt / cache hit / cache miss / completion / reasoning / total usage；Eval 报告计算多 Tool Calls、每成功 Run Token、估算成本和 latency average / p50 / p95 / max
  - Development Dataset 已覆盖复杂农艺解释、失败恢复、Tool Result 冲突和多轮澄清；两模型原结果均为 11/12，复杂分析各出现一次约 63 秒的第二次 Provider 调用失败；因此已补 retry、错误分类和单 Run budget，待新策略复测；Holdout 已创建但在配置冻结前不运行
  - Agent Runtime 已补 Provider retry/error classification：timeout、429、瞬态 5xx 最多 3 次并使用 backoff / jitter / capped Retry-After；请求、认证、余额和协议错误快速失败，重试不会重放业务 Tool
  - Run 已补默认 180 秒活跃执行段和 16k cumulative Token budget；Approval 等待不计时，成本预算需显式价格和上限后启用；新策略尚未重新运行真实模型 Development
  - Durable Worker / Job / Lease / Heartbeat / Watchdog / 多实例 SSE 已形成 Proposed PostgreSQL Queue 目标设计，尚未实现 migration 016 和 Worker
  - Agent Runtime 已支持一个 Model Turn 中独立只读 Query 的 bounded parallel execution；每个并行数据库 Query 使用独立 SQLAlchemy Session，结果按原 Tool Call 顺序回注；Query + Write 混合批次要求模型基于查询结果重新提出写 Action，多个副作用 Action 继续一次一个
  - Agent Runtime 已统一回注 `completed / rejected / failed / unknown` Tool Result；只读失败可继续推理，写 Action 异常保守标为结果不确定并禁止自动重试，串行 Tool 通过数据库 savepoint 隔离本地事务
  - 当前尚未在目标数据库执行 migration、使用真实业务数据完成 eval 或生产部署

- 后端主链路已稳定：Plan Orchestrator、Task / Review / Execution、病虫日更、天气 / 生育期运行期支撑都已接通。
- 生育期或日历刷新导致 `CalendarItem` 更新时，通用 `_upsert_calendar_item` 路径现在会同步已生成且仍为 pending 的关联 `FarmingTask` 标题、描述、计划时间和目标生育期；非 pending 任务、已审核方案和执行记录不自动改动。
- 病虫害防治复核契约已收口到“只审核理论方案”：
  - `/api/review-requests/{reviewRequestId}/resolve` 对 `plant_protection.disease_pest_control` 仅接收 `decision_payload.proposedPlan.theoryPlan`
  - `theoryPlan.rounds` 支持直接提交用户编辑后的完整轮次列表；数量变化即表示新增 / 删除，后端自动重排轮次并重算天气修正后的实际窗口
  - 最终 `recommendedControlDate`、`operationWindow`、正式 `controlPlan` 都从审核后的 `theoryPlan` 派生
- 病虫害防治详情 / 复核详情返回口径已补齐：
  - `source_task_intent.rule_result.proposedPlan`、`operation_plans[].parameters`、`operation_plans[].prescription_map` 中的病虫害 `targets` key 统一返回中文对象名
  - 复核详情补充完整 `reviewContext.availableTargets`，便于前端做人工补选
- 上述改动的后端测试与接口测试已补齐并通过：
  - `tests/services/test_review_request_service.py`
  - `tests/api/test_review_requests.py`
  - `tests/api/test_task_details.py`
- 前端联调所需的关键契约与运行期修正已补齐，包括 `farm_name`、`operation_date` 暴露、取消任务禁止继续提交执行数据，以及未来日期实际生育期录入口径。
- 远程数据库初始化与迁移路径已补齐：
  - 新增 `bootstrap-db.ps1`、`seed_reference_data.py`、`migrate_farm_field_data.py`
  - 支持先建表，再初始化基础参考数据，并按需把本地真实 `cf_farm / cf_field / cf_farm_field_relation` 迁到远程库
  - 已新增 `sync-remote-db.ps1` + `sync_table_data.py` 作为远程库一键同步入口，支持显式配置要全量同步的表，并统一串起 migration、reference seed 和本地表数据同步
  - 现已补 `compare_table_data.py` 作为差异预检入口，支持先看 source / target 的新增、缺失和业务字段变化，再决定同步哪些基础表
  - `sync-remote-db.ps1` 默认同步模式已从 `exact` 调整为保守的 `merge`；只有显式传 `-TableSyncMode exact` 才覆盖目标表
  - 已通过 SSH tunnel 在真实远程 `cropflow_deploy` 上完成一次落库验证：schema 升级到 `cf014_scope_field_external_id`，并以 `merge + SkipSeed` 同步 `cf_administrative_division`、`cf_farm`、`cf_field`、`cf_farm_field_relation`
- Docker 部署路径已补齐并跑通：
  - 已补 `Dockerfile`、`docker-compose.yml`、`docker/entrypoint.sh`、`.env.docker.example`
  - 已补远程数据库初始化与 Docker 部署文档
  - 远程机器已通过镜像源调整成功完成容器部署
- 项目文档与 AI workflow 入口已完成一轮结构收口：
  - `docs/planning/` 已退出默认入口，方向知识、FDE、前端 handoff、历史材料分别沉淀到 `docs/domain/`、`docs/fde/`、`docs/frontend/`、`docs/history/`
  - 已补 `docs/change-notes/`、`docs/decisions/`、`docs/wiki-index.md` 和 `docs/ai/codex-skill-workflow.md`
  - 已补并同步本地可用 skill：`cropflow-start-work`、`cropflow-task-planning`、`cropflow-task-closing`、`cropflow-wrap-up`、`cropflow-wiki-maintenance`
- 农场 / 地块基础管理能力已补齐一轮后端实现：
  - 新增 `Field.external_field_id` 作为外部系统映射字段
  - 补齐农场删除接口，以及农场下地块单条和批量 `GET/POST/PATCH/DELETE` 接口
  - `Field.id` 继续作为系统内部主键和 `PlantingPlan.field_ids` 的引用 id
  - `PlantingPlan` 创建 / 更新时会校验 `farm_id` 存在，且 `field_ids` 全部属于该农场
  - 农场 / 地块可选字段支持在 `PATCH` 中显式传 `null` 清空，并新增经纬度 / 面积基础校验
  - 删除农场 / 地块时会阻止删除已被 `PlantingPlan` / `PlantingPlanFieldRelation` 引用的数据
- 农场创建联调所需的行政区划查询能力已补齐：
  - 新增 `GET /api/administrative-divisions`，支持按 `parent_code + parent_level` 查询子节点
  - 行政区划数据已从仓库内 `docs/references/raw/china_administrative.xlsx` 导入 `cf_administrative_division`
  - 运行期接口只查数据库，不再逐次读取 xlsx
  - 对直辖市补充虚拟二级节点，保证前端仍可按“省 -> 市 -> 区县”统一级联交互
- 杂草防治外部接口兼容口径已修正：
  - 系统内部 `PlantProtectionPlanContext` 保留 `PlantingPlan` 的原始种植制度，不再提前归一化
  - 仅在调用杂草防治外部接口时，如种植制度为 `再生稻`，请求参数里的 `cultivation_system` 映射为 `早稻`
  - `PlantingPlan` 创建时的地块存在性校验优先走 `Field.id` 轻量查询，避免仅校验 id 时加载完整地块对象
- `app/models/core.py` 已完成一次文件级拆分：
  - 新增 `master_data / planning / tasks / execution` 四个模型模块
  - `app.models` 和 `app.models.core` 继续保留兼容导出，避免全仓导入路径大范围改动
  - 当前拆分只处理文件组织，不改变 ORM 注册结果和业务语义
- 未来日期实际生育期的天气边界口径已修正：
  - `HttpWeatherProvider.get_daily_weather()` 在传入未来 `as_of_date` 时，observed 只截到真实今天的前一天
  - forecast 改为从真实今天开始补齐，避免向历史观测接口请求“今天尚未落库”的数据
  - `tests/services/test_weather_provider.py` 已补回归用例并通过
- 生育期 GDD 阈值消费口径已修正：
  - 外部接口返回阈值包含移栽返青期积温；直播计划在后端按 `BBCH21 - BBCH13` 扣除返青期积温，并从 `BBCH21` 及后续阈值中扣减
  - 非直播早稻且存在 `transplant_date` 时，系统继续把移栽日期作为 `BBCH13` 锚点，再按阈值差推导后续阶段
- 前端联调与上层回放已继续完成一轮验证：
  - 病虫害复核页按新的 `theoryPlan.rounds` 整表提交模式联调已通过，`/api/review-requests/{id}` 的中文 `targets` 回显、轮次增删改提交，以及 `/api/review-requests/{id}/resolve` 返回后的正式任务刷新已确认正常
  - `task_detail / execution_feedback / survey_entry / plan_detail` 当前联调可用，相关聚合详情与执行反馈流转未发现阻塞问题
  - 未来日期实际生育期修复已完成一轮更上层的阶段重算 / API 回放验证，天气边界修复在上层流程中成立
  - 行政区划查询与农场创建相关级联链路联调已通过，`/api/administrative-divisions` 的根节点、省市区查询、直辖市虚拟二级节点和最终 `adcode` 回填已确认正常
- AI 协作与 FDE 文档入口已继续收口：
  - `AGENTS.md` 已补“编码前检查”“通用 agent-skills 路由”“Never”约束，明确当前仓库默认工作流
  - `docs/fde/task-flow-fde-output-template.md` 已补通用任务 / 流程 FDE 输出模板
  - `docs/fde/plant-protection-fde-output-template.md` 已补为完整植保参考样例，覆盖杂草和病虫害两条主线
  - `docs/workflow/checklists/plant-protection-task-checklist.md` 已调整为植保农事项梳理入口页
  - 施肥方向文档今天继续收口了一轮：`docs/workflow/checklists/fertilization-task-checklist.md`、`docs/fde/fertilization-fde-draft.md`、`docs/workflow/task-workflow-matrix.md`、`docs/domain/fertilization.md`、`docs/model/data-model.md`、`docs/model/data-model-validation.md` 已开始同步
  - 施肥主链路已基本对齐：采样点默认取 `PlantingPlan` 各地块中心，采土 / 测土拆成两个任务，土壤检测结果独立表按原始检测样表格式存储，施肥算法调用时再按需提取必要字段
  - 施肥处方与方案口径已基本对齐：所有施肥处方和变量穗肥处方都先人工审核；施肥处方生成结果优先挂在对应任务下的 `OperationPlan`；基肥 / 分蘖肥 / 穗肥处方统一按“地块 -> 施肥量”表达
  - 穗肥变量处方图口径已收口到“系统内只保存远程 URL”；施肥效果评估已统一覆盖基肥、施蘖肥和施穗肥；评估异常当前口径是触发人工处理农事，而不是直接走 `ReviewRequest`
  - 施肥方向 `FER-OPEN-05/06/08` 已继续冻结：变量处方图 URL 第一版直接公开；施肥效果评估异常后的人工处理结果目前仅记录并结束；算法只给样本点单位面积施肥量，系统侧映射 / 补充为地块维度单位面积施肥量，不要求算法返回地块绝对施肥总量
  - 施肥 FDE 继续冻结：再生稻发苗肥 / 促芽肥暂不纳入本轮；土样采集第一版不生成二维码；长势监测按业务人员到场执行无人机监测、完成后录入执行记录和遥感后续任务 id（影像上传、影像拼接）处理；M3 / healthy 必需字段已确认；当前以 `docs/fde/fertilization-fde-draft.md` 为施肥事实源
  - 施肥开发口径已继续补齐：`taskSubtype` 以 FDE draft 为准，正式文档已同步为 `soil_sampling / soil_testing / base_fertilizer / tillering_fertilizer / tillering_growth_monitoring / panicle_fertilizer / effect_evaluation / manual_follow_up`；新增 `docs/api/fertilization_prescription_algorithm_api.md` 作为 `POST /run` 开发 contract；审核页最小上下文明确为土壤检测数据、算法处方、穗肥变量处方图
  - 只服务历史排查的 `run_e2e_trace.py`、`run_soil_treatment_trace.py`、`replay_pest_disease_daily_update.py` 已从正式 `scripts/` 迁到 `docs/history/scripts/`；`scripts/migrate-up.ps1` 已删除

## Remaining

- Agent Runtime 仍需在目标环境完成 migration 015，并基于真实业务数据继续 provider eval、异常回放和端到端验收；先用新 resilience 策略复跑 Development，再在模型配置冻结后运行 Holdout。
- 需要为真实用户配置 `cf_user.metadata.agent_roles`，并在生产化前接入正式 IAM / 数据范围。
- 当前 SSE 在 API 请求进程内执行；Durable Worker 的 PostgreSQL Job Queue、Lease、Heartbeat、Watchdog、stuck-run recovery、多实例事件交付和 Agent 前端仍待补齐。

- 把远程部署用的 `.env`、镜像源和拉起顺序沉淀为稳定运维说明，避免下次再走本地 tunnel 连接串。
- 施肥方向文档还未最终收口，当前主要剩余点：
  - 后续如进入真实前端 / 算法联调，再补变量处方图服务、效果评估、库存映射等扩展 API contract；当前处方算法开发入口已补齐
  - 如要正式开发施肥闭环，先按 FDE draft 和 `docs/api/fertilization_prescription_algorithm_api.md` 拆任务与测试，再落数据表和服务实现
- 如需正式修复历史脏数据，在目标环境执行 `scripts/repair_merged_disease_pest_controls.py --apply` 并核对生成的 repair event。
- 气象运行期管理还没完全产品化，缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。
- 农场 / 地块接口还未经过真实前端联调，尤其要确认前端创建计划时继续使用内部 `field_id`，只把 `external_field_id` 当外部映射字段展示或透传。
- 杂草防治接口仍需在真实联调环境再确认一次 `再生稻 -> 早稻` 的外部映射是否已覆盖土壤封闭、药前调查、茎叶除草和补防四条调用链。

## Blockers

当前无明确阻塞项。

## Next Step

下个 session 优先做三件事：

1. Agent Runtime 下一步先用新 retry/timeout/budget 策略复跑 Development；确认 Proposed ADR 017 后可进入 `cf_agent_job + migration 016 + Worker` 的 6A 开发，再冻结 Prompt、Tool Schema、Grader 和模型配置运行 Holdout。进入指定目标环境后执行 migration 015/016、配置测试用户 agent_roles，并回放查询 / 完成任务 / 处理复核三条真实数据链路。
2. 如继续推进施肥，优先基于 FDE draft 和 `docs/api/fertilization_prescription_algorithm_api.md` 拆后端任务、数据表和测试。
3. 变量处方图服务、施肥效果评估和库存映射可作为后续扩展 contract 单独补。
4. 后续如重新纳入再生稻发苗肥 / 促芽肥，应另起 FDE 补充，不回填到本轮已冻结主链路。

## Last Updated

`2026-07-18`
