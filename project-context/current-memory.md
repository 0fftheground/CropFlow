# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入  
Roadmap 对应阶段：`T2` 工程实现后段，并已进入 `T3` 植保 / 气象 / 生育期扩展联调

## Phase Goal

在已冻结的杂草样板闭环基础上，收口植保后端主链路、真实天气 / 生育期运行期支撑，并补齐可复用的远程数据库初始化与 Docker 部署路径。

## Progress

- 后端主链路已稳定：Plan Orchestrator、Task / Review / Execution、病虫日更、天气 / 生育期运行期支撑都已接通。
- 前端联调所需的关键契约与运行期修正已补齐，包括 `farm_name`、`operation_date` 暴露、取消任务禁止继续提交执行数据，以及未来日期实际生育期录入口径。
- 远程数据库初始化与迁移路径已补齐：
  - 新增 `bootstrap-db.ps1`、`seed_reference_data.py`、`migrate_farm_field_data.py`
  - 支持先建表，再初始化基础参考数据，并按需把本地真实 `cf_farm / cf_field / cf_farm_field_relation` 迁到远程库
- Docker 部署路径已补齐并跑通：
  - 已补 `Dockerfile`、`docker-compose.yml`、`docker/entrypoint.sh`、`.env.docker.example`
  - 已补远程数据库初始化与 Docker 部署文档
  - 远程机器已通过镜像源调整成功完成容器部署

## Remaining

- 继续做前端真实联调验收，优先 `plan_detail / task_detail / survey_entry / review_request / execution_feedback`。
- 把远程部署用的 `.env`、镜像源和拉起顺序沉淀为稳定运维说明，避免下次再走本地 tunnel 连接串。
- 如需正式修复历史脏数据，在目标环境执行 `scripts/repair_merged_disease_pest_controls.py --apply` 并核对生成的 repair event。
- 气象运行期管理还没完全产品化，缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。

## Blockers

当前无明确阻塞项。

## Next Step

下个 session 优先做三件事：

1. 继续和前端一起把植保页面联调跑完，重点验 `farm_name`、`survey-results`、`execution-completions`、`execution-record update(operation_date)`、`review resolve` 的页面流转。
2. 抽查远程部署环境的 API / scheduler 日志与关键接口，确认数据库连接串、镜像源和 migration-on-start 行为已稳定。
3. 视联调环境需要决定是否执行 `repair_merged_disease_pest_controls.py --apply`，并继续补天气异常展示、前端状态表达和真实计划脏数据清理策略。

## Last Updated

`2026-06-11`
