# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入  
Roadmap 对应阶段：`T2` 工程实现后段，并已进入 `T3` 植保 / 气象 / 生育期扩展联调

## Phase Goal

在已冻结的杂草样板闭环基础上，收口植保后端主链路、真实天气 / 生育期运行期支撑，并补齐可复用的远程数据库初始化与 Docker 部署路径。

## Progress

- 后端主链路已稳定：Plan Orchestrator、Task / Review / Execution、病虫日更、天气 / 生育期运行期支撑都已接通。
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

## Remaining

- 把远程部署用的 `.env`、镜像源和拉起顺序沉淀为稳定运维说明，避免下次再走本地 tunnel 连接串。
- 如需正式修复历史脏数据，在目标环境执行 `scripts/repair_merged_disease_pest_controls.py --apply` 并核对生成的 repair event。
- 气象运行期管理还没完全产品化，缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。
- 农场 / 地块接口还未经过真实前端联调，尤其要确认前端创建计划时继续使用内部 `field_id`，只把 `external_field_id` 当外部映射字段展示或透传。
- 杂草防治接口仍需在真实联调环境再确认一次 `再生稻 -> 早稻` 的外部映射是否已覆盖土壤封闭、药前调查、茎叶除草和补防四条调用链。

## Blockers

当前无明确阻塞项。

## Next Step

下个 session 优先做三件事：

1. 继续确认农场 / 地块与计划创建链路的真实前端使用方式，重点看内部 `field_id`、`external_field_id` 展示和删除保护是否符合页面预期。
2. 在真实联调环境再确认一次杂草防治 `再生稻 -> 早稻` 的外部映射是否已覆盖土壤封闭、药前调查、茎叶除草和补防四条调用链。
3. 再视联调环境决定是否执行 `repair_merged_disease_pest_controls.py --apply`，并继续补天气异常展示、前端状态表达和真实计划脏数据清理策略。

## Last Updated

`2026-06-25`
