# Current Memory

## Current Phase

工作相位：`P2` 收尾 + `P3` 前置扩展接入  
Roadmap 对应阶段：`T2` 工程实现后段，并已进入 `T3` 植保 / 气象 / 生育期扩展联调

## Phase Goal

在已冻结的杂草样板闭环基础上，收口植保后端主链路、真实天气 / 生育期运行期支撑，以及前端联调所需的 handoff / API contract。

## Progress

- 后端工程骨架、核心 ORM / migration、Repository、Plan Orchestrator、Task / Review / Execution 主链路已落地。
- 杂草主链路已跑通：药前调查 -> 审核 -> 正式除草任务 -> 作业反馈 -> 安全性 / 防效调查 -> 服务评价 / 现场确认。
- 病虫主链路已跑通：常规调查 -> 审核 -> 正式防治任务 -> 作业反馈；`service_effect_evaluation` / `service_effect_survey` 也已接入正式任务链路。
- 病虫 `daily-update-survey` 已完成 `CalendarItem` 映射，`new_emergency / merged_into_regular / no_new_event` 三种状态的本地语义已接通；其中 `merged_into_regular` 已用真实 `plan 19` + 合成天气真实打通。
- 真实联调中修复了几类关键问题：杂草天气入参归一化、病虫 `level1_window` payload 形状、soil-treatment 幂等性复用、病虫打药适宜度天气拼装、72h 小时天气 fallback、任务完成状态更新、执行记录挂接 active `OperationPlan`、`resolved_by` 前置校验。
- 当前最近一次后端测试结果为 `105 passed, 1 skipped`。
- 前端已开始真实调试；`plan 19` 上已补 `service_effect_evaluation` / `service_effect_survey` 调试任务，便于页面联调。
- 前端联调文档已从 weed 命名收口为 plant protection 命名：
  - `docs/planning/team-work-division/frontend-plant-protection-handoff.md`
  - `docs/api/frontend-plant-protection-api-contract.md`
- 新文档已补病虫调查 / 病虫防治的页面说明、payload 示例、对象字段对照表和前端组装建议。
- 新增 `scripts/replay_pest_disease_daily_update.py`，可基于真实计划回放 `daily-update-survey` 并复现 `merged_into_regular`。

## Remaining

- 继续做前端真实联调验收，优先 `plan_detail / task_detail / survey_entry / review_request / execution_feedback`。
- 病虫调查表单仍只有第一版字段建议；如前端需要更多病虫对象或更细字段，还要继续补 contract。
- 病虫日更虽然已能回放 `merged_into_regular`，但 `new_emergency` 的稳定复现方式还值得继续收口。
- 气象运行期管理仍未完全产品化：`observed / forecast / climatology` 的缓存、历史修正和更细审计仍待补齐。
- 生育期运行期策略仍需继续收口，尤其是人工录入后的影响边界、raw stage code 消费范围和历史天气回刷口径。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。

## Blockers

- 外部天气接口契约仍有漂移：平均接口使用 `farmId`，逐日预报接口使用 `farmID`，小时级接口 `/algBaseDataApi/v1/getForecast10DaysBeforeAndAfter` 仍可能返回 `Api not exists`，目前依赖 fallback。
- 本地真实联调仍依赖 `Farm.external_farm_id`；缺失时天气链路直接不可用。
- 前端虽然已开始调试，但页面级验收和字段最终定稿还没有完全收口。

## Next Step

下个 session 优先做三件事：

1. 继续和前端一起把植保页面联调跑完，重点验 `survey-results` / `execution-completions` / `review resolve` 的页面流转。
2. 继续补病虫调查 / 防治的调试支撑，必要时把 `daily-update-survey` 的 replay 固化成更明确的 `merged / emergency` 模式。
3. 继续收口生育期和气象运行期策略，把历史回刷、raw stage code 和人工录入影响范围说清楚。

## Last Updated

`2026-06-03`
