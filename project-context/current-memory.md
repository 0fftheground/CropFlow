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
- 前端联调 contract 继续细化：
  - 病虫调查第一版固定为完整 5 类对象 schema，`survey_method` 只读回填，零值字段显式回传
  - `task_detail` 已明确要展示已完成任务的执行结果
  - 新增 `PATCH /api/tasks/{taskId}/execution-records/latest`，支持只编辑最近一次执行记录并生成 `ExecutionRecordUpdated`
- 计划运行态和执行链路补了几项关键能力：
  - `PATCH /planting-plans/{id}` 现在记录 `PlanUpdated` 审计事件
  - `draft -> active` 会自动补发 `TaskDueCheckTriggered`
  - `/planting-plans/{id}/tasks` 已改为返回全量任务，不再过滤 completed
  - `resolved_by` 兼容 `user id / username / display_name`
- 生育期 / 气象 MVP 规则已固定并落成 ADR：`docs/decisions/007-stage-weather-runtime-mvp-rules.md`
- 创建计划和运行期联调口径已放宽 / 收紧到当前版本：
  - 创建计划允许先不传地块
  - 生育期人工录入只接受 raw stage code，禁止未来日期，同批多条录入会做顺序冲突校验
- 开发环境脚本已固定使用项目 `.venv`：`scripts/start-dev.ps1`
- 新增 `scripts/replay_pest_disease_daily_update.py`，可基于真实计划回放 `daily-update-survey` 并复现 `merged_into_regular`。

## Remaining

- 继续做前端真实联调验收，优先 `plan_detail / task_detail / survey_entry / review_request / execution_feedback`。
- 病虫日更虽然已能回放 `merged_into_regular`，但 `new_emergency` 的稳定复现方式还值得继续收口。
- 生育期与气象运行期 MVP 口径已收口：
  - 天气输入优先级固定为 `observed > forecast > climatology`
  - `forecast` 只刷新预测层，不直接触发 `StageChanged`
  - 历史 `observed` 修正从“修正日期”和最近人工 raw stage 锚点两者中更晚者开始重算
  - 人工录入只接受 raw stage code，且只能录入当天或过去日期
- 气象运行期管理仍未完全产品化：更细缓存、版本审计、异常展示和前端状态细化仍待补齐。
- DeviceCommand、InventoryItem / InventoryTransaction 仍按 deferred 处理。

## Blockers

- 外部天气接口契约仍有漂移：平均接口使用 `farmId`，逐日预报接口使用 `farmID`，小时级接口 `/algBaseDataApi/v1/getForecast10DaysBeforeAndAfter` 仍可能返回 `Api not exists`，目前依赖 fallback。
- 本地真实联调仍依赖 `Farm.external_farm_id`；缺失时天气链路直接不可用。
- 前端虽然已开始调试，但页面级真实验收还没跑完，尤其是执行结果展示 / 编辑和病虫调查提交流程。

## Next Step

下个 session 优先做三件事：

1. 继续和前端一起把植保页面联调跑完，重点验 `survey-results` / `execution-completions` / `execution-record update` / `review resolve` 的页面流转。
2. 继续补病虫调查 / 防治的调试支撑，必要时把 `daily-update-survey` 的 replay 固化成更明确的 `merged / emergency` 模式。
3. 按已冻结的生育期 / 气象 MVP 规则继续联调，重点补天气异常展示、前端状态表达和历史修正验证。

## Last Updated

`2026-06-04`
