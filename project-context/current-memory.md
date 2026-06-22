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
- Docker 部署路径已补齐并跑通：
  - 已补 `Dockerfile`、`docker-compose.yml`、`docker/entrypoint.sh`、`.env.docker.example`
  - 已补远程数据库初始化与 Docker 部署文档
  - 远程机器已通过镜像源调整成功完成容器部署
- 项目文档与 AI workflow 入口已完成一轮结构收口：
  - `docs/planning/` 已退出默认入口，方向知识、FDE、前端 handoff、历史材料分别沉淀到 `docs/domain/`、`docs/fde/`、`docs/frontend/`、`docs/history/`
  - 已补 `docs/change-notes/`、`docs/decisions/`、`docs/wiki-index.md` 和 `docs/ai/codex-skill-workflow.md`
  - 已补并同步本地可用 skill：`cropflow-start-work`、`cropflow-task-planning`、`cropflow-task-closing`、`cropflow-wrap-up`、`cropflow-wiki-maintenance`

## Remaining

- 继续做前端真实联调验收，优先 `review_request / task_detail / execution_feedback / survey_entry / plan_detail`，重点确认病虫害复核页按新的 `theoryPlan.rounds` 整表提交模式工作正常。
- 把远程部署用的 `.env`、镜像源和拉起顺序沉淀为稳定运维说明，避免下次再走本地 tunnel 连接串。
- 如需正式修复历史脏数据，在目标环境执行 `scripts/repair_merged_disease_pest_controls.py --apply` 并核对生成的 repair event。
- 气象运行期管理还没完全产品化，缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。

## Blockers

当前无明确阻塞项。

## Next Step

下个 session 优先做三件事：

1. 和前端一起实跑病虫害复核场景，重点验 `/api/review-requests/{id}` 的中文 `targets` 回显、`theoryPlan.rounds` 的增删改提交流程，以及 `/api/review-requests/{id}/resolve` 返回后的正式任务刷新。
2. 继续抽查植保任务详情与执行反馈流转，确认 `operation_plans.parameters / prescription_map` 的中文对象名口径不会影响现有页面逻辑。
3. 视联调环境需要决定是否执行 `repair_merged_disease_pest_controls.py --apply`，并继续补天气异常展示、前端状态表达和真实计划脏数据清理策略。

## Last Updated

`2026-06-22`
