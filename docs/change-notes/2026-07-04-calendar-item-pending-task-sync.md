# CalendarItem 变更同步 pending FarmingTask

日期：2026-07-04

## 背景

用户手工修正生育期后，Plan Calendar Refresh 会重新计算预备农事项 `CalendarItem`。此前只有病虫害常规调查在业务函数内单独同步已生成的 pending 正式任务，其他通过 `_upsert_calendar_item` 更新的 generated 日历项不会统一刷新关联 `FarmingTask` 的计划时间。

## 本次调整

- 将“generated CalendarItem -> pending FarmingTask”的同步逻辑提升到 `_upsert_calendar_item` 共用路径。
- 当 `CalendarItem.status == generated` 且存在 `generated_task_id` 时，仅在关联 `FarmingTask.status == pending` 时同步：
  - `title`
  - `description`
  - `planned_start_at`
  - `planned_end_at`
  - `target_stage_code`
- 已开始、已完成或其他非 pending 正式任务不被自动改动。
- 已审核产生的 `OperationPlan`、执行记录、复核结果不在本次通用同步范围内，仍按各自流程处理。

## 验证

- `tests/services/test_calendar_tasks.py::test_upsert_calendar_item_syncs_pending_generated_task`
- `tests/services/test_calendar_tasks.py` 全量通过
- `tests/services/test_plan_calendar_refresh.py` 全量通过
