# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入  
Roadmap 对应阶段：`T2` 工程实现后段，并已进入 `T3` 植保 / 气象 / 生育期扩展联调

## Phase Goal

在已冻结的杂草样板闭环基础上，收口植保后端主链路、真实天气 / 生育期运行期支撑，以及前端联调所需的 handoff / API contract。

## Progress

- 后端主链路已稳定：Plan Orchestrator、Task / Review / Execution、病虫日更、天气 / 生育期运行期支撑都已接通。
- 今天继续补完了前端联调契约和运行期修正：
  - `PlantingPlanResponse` / debug snapshot 已补 `farm_name`
  - `execution-completions`、`task_detail.execution_records` 和 `PATCH latest execution record` 已正式暴露 `operation_date`
  - `PATCH /api/tasks/{taskId}/execution-records/latest` 现已支持编辑 `operation_date`
- 取消状态任务现在不能再提交调查结果或执行记录，避免 `cancelled` 任务继续落执行数据。
- 病虫防治合并逻辑已增强：不仅能合并当前 pending recommendation，也能识别并合并“已转任务的对向防治建议”，同时取消陈旧的 `FarmingTask` / `ReviewRequest`。
- 已补 `scripts/repair_merged_disease_pest_controls.py`，用于对存量 plan 批量修复常规/突发病虫防治未合并的数据。
- 天气小时级预报已切到最新接口 `/weather/v1/getForecast10DaysBeforeAnd15DaysAfter`，相关 fallback 测试已更新。
- `/api/planting-plans/{id}/actual-stages` 已移除“实际生育期不能晚于今天”的限制，允许按联调需要录入未来日期。
- 今天新增/更新过的相关测试均已通过：`test_planting_plan_service`、`test_planting_plans`、`test_tasks`、`test_task_details`、`test_task_executions`、`test_survey_results`、`test_weather_provider`。

## Remaining

- 继续做前端真实联调验收，优先 `plan_detail / task_detail / survey_entry / review_request / execution_feedback`。
- 如需正式修复历史脏数据，在目标环境执行 `scripts/repair_merged_disease_pest_controls.py --apply` 并核对生成的 repair event。
- 继续补病虫日更的 `new_emergency` 稳定复现方式和前端展示口径。
- 气象运行期管理还没完全产品化，缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。

## Blockers

当前无明确阻塞项。

## Next Step

下个 session 优先做三件事：

1. 继续和前端一起把植保页面联调跑完，重点验 `farm_name`、`survey-results`、`execution-completions`、`execution-record update(operation_date)`、`review resolve` 的页面流转。
2. 视联调环境需要决定是否执行 `repair_merged_disease_pest_controls.py --apply`，并抽查 `plan 36` 一类历史 plan 的合并结果和取消任务是否已阻止继续提执行记录。
3. 继续按已冻结的生育期 / 气象 MVP 规则联调，重点补天气异常展示、前端状态表达和真实计划脏数据清理策略。

## Last Updated

`2026-06-09`
