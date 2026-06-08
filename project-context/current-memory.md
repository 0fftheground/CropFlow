# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入  
Roadmap 对应阶段：`T2` 工程实现后段，并已进入 `T3` 植保 / 气象 / 生育期扩展联调

## Phase Goal

在已冻结的杂草样板闭环基础上，收口植保后端主链路、真实天气 / 生育期运行期支撑，以及前端联调所需的 handoff / API contract。

## Progress

- 后端主链路已稳定：Plan Orchestrator、Task / Review / Execution、病虫日更、天气 / 生育期运行期支撑都已接通。
- 今天把植保方向的文档入口做了收口：`planning` 下的方向文档已拆到 `docs/planning/directions/*`，历史内容归档到 `docs/planning/archive/*`，原始资料集中到 `docs/**/raw/`。
- 今天补了三类面向接入方的文档：FDE 标准工作流程、农事项接入所需文档清单与填写说明、docs 治理与目录整理说明。
- 今天把 `/api/planting-plans/{id}/actual-stages` 的实际接口链路跑通并修掉了重复问题：
  - 实际生育期录入后会触发 `StageChanged` 和日历刷新
  - 常规病虫调查现在会优先复用 `generated + pending` 的现有项
  - 旧的重复 `active` / `invalidated` 项不会再把 `generated` 项顶掉或复活
  - 相关 pending 任务会同步更新计划时间
- `plan 36` 已用真实接口回放验证，当前状态是 `BBCH89 / 2026-06-08`，常规病虫调查没有 active 重复项。
- 已跑过的相关测试集全部通过：`test_calendar_tasks`、`test_plan_calendar_refresh`、`test_pest_disease_daily_update`、`test_deps`。

## Remaining

- 继续做前端真实联调验收，优先 `plan_detail / task_detail / survey_entry / review_request / execution_feedback`。
- 继续补病虫日更的 `new_emergency` 稳定复现方式和前端展示口径。
- 气象运行期管理还没完全产品化，缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。

## Blockers

- 外部天气接口契约仍有漂移：平均接口使用 `farmId`，逐日预报接口使用 `farmID`，小时级接口 `/algBaseDataApi/v1/getForecast10DaysBeforeAndAfter` 仍可能返回 `Api not exists`，目前依赖 fallback。
- 本地真实联调仍依赖 `Farm.external_farm_id`，缺失时天气链路直接不可用。
- 前端页面级真实验收还没跑完，尤其是执行结果展示 / 编辑和病虫调查提交流程。

## Next Step

下个 session 优先做三件事：

1. 继续和前端一起把植保页面联调跑完，重点验 `survey-results` / `execution-completions` / `execution-record update` / `review resolve` 的页面流转。
2. 继续补病虫调查 / 防治的调试支撑，必要时把 `daily-update-survey` 的 replay 固化成更明确的 `merged / emergency` 模式。
3. 继续按已冻结的生育期 / 气象 MVP 规则联调，重点补天气异常展示、前端状态表达和真实计划脏数据清理策略。

## Last Updated

`2026-06-08`
