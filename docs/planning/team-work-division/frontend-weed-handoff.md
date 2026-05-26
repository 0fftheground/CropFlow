# 杂草防治前端联调交接稿

> 本文档用于给前端开发提供“当前已可联调”的页面需求和接口契约。  
> 口径以当前后端代码和已落地 API 为准，不再沿用尚未实现的 `Evaluation`、`SystemNotification` 聚合视图或建议态字段草案。

适用阶段：

```text
P2 - 杂草防治样板链路前后端联调
```

接口前缀：

```text
/api
```

接口出入参明细请同时阅读：

```text
docs/api/frontend-weed-api-contract.md
```

---

## 1. 当前前端页面范围

按当前已实现链路，建议前端按 9 个独立页面规划：

| pageKey | pageName | 目标 | 当前状态 | 说明 |
|---|---|---|---|---|
| `plan_create` | 计划创建 | 创建 `PlantingPlan` | 可直接接真实接口 | 闭环入口 |
| `plan_detail` | 计划详情 | 看计划、任务、复核、事件总览 | 可接简化版真实接口 | 当前不包含 `CropStageState` / `SystemNotification` 专门接口 |
| `calendar_list` | 农事项日历 | 看 `CalendarItem` 列表 | 可直接接真实接口 | 重点区分预备农事项和正式任务 |
| `task_detail` | 任务详情 | 看 `FarmingTask`、方案、执行历史 | 可直接接真实接口 | 已有聚合详情接口 |
| `survey_entry` | 调查录入 | 录入药前/药后调查结果 | 可直接接真实接口 | 复用 `POST /tasks/{id}/survey-results` |
| `review_request` | 人工复核 | 看审核上下文并提交决策 | 可直接接真实接口 | 已有详情和处理接口 |
| `execution_feedback` | 执行反馈 | 录入正式作业执行结果 | 可直接接真实接口 | 复用 `POST /tasks/{id}/execution-completions` |
| `evaluation_entry` | 服务评价录入 | 录入满意度和联系人 | 可直接接真实接口 | 当前不是独立 `Evaluation` 对象，而是服务评价任务的调查结果录入 |
| `service_effect_survey` | 服务人员现场确认 | 录入现场实际情况和原因 | 可直接接真实接口 | 录入后链路结束 |

---

## 2. 页面流转

```text
plan_create
  -> plan_detail
  -> calendar_list
  -> task_detail
  -> survey_entry / execution_feedback / review_request / evaluation_entry
  -> service_effect_survey
  -> plan_detail
```

杂草防治主链路页面流转建议：

1. `plan_create` 创建计划后跳转 `plan_detail`
2. `plan_detail` 进入 `calendar_list` 查看预备农事项
3. `calendar_list` 或 `plan_detail` 进入 `task_detail`
4. 调查类任务从 `task_detail` 进入 `survey_entry`
5. 复核类事项从 `plan_detail` 或 `task_detail` 进入 `review_request`
6. 正式防治任务从 `task_detail` 进入 `execution_feedback`
7. 服务评价任务从 `task_detail` 进入 `evaluation_entry`
8. 服务评价不满意后，跳转 `service_effect_survey`
9. 现场确认提交后返回 `plan_detail`

---

## 3. 页面需求总表

| pageKey | entry | primaryObjects | mustShow | primaryActions | backendReadiness | notes |
|---|---|---|---|---|---|---|
| `plan_create` | 入口页 | `PlantingPlan` | 基础表单、创建结果 | 查询选项、创建计划 | ready | 创建前先查稻作类型 / 种植方式 / 品种 |
| `plan_detail` | 创建后 / 计划列表 | `PlantingPlan` / `CalendarItem` / `FarmingTask` / `ReviewRequest` / `EventRecord` | 计划基础信息、预备事项、正式任务、待复核事项、关键事件 | 跳转详情页 | partial-ready | 当前先做简化版计划总览，不等待 `SystemNotification` |
| `calendar_list` | 计划详情 | `CalendarItem` | 标题、日期、状态、来源任务、是否已生成正式任务 | 查看详情 | ready | 列表里要显式区分 `CalendarItem` 和 `FarmingTask` |
| `task_detail` | 计划详情 / 日历页 | `FarmingTask` / `OperationPlan` / `Execution` / `ExecutionRecord` / `EventRecord` | 任务主信息、方案、执行记录、来源对象、下游日历项 | 跳转录入页、复核页 | ready | 当前最适合作为工作台页面 |
| `survey_entry` | 任务详情 | `FarmingTask` / `ExecutionRecord` | 任务上下文、调查表单 | 提交调查结果 | ready | 根据 `task_subtype` 切换表单 |
| `review_request` | 计划详情 / 任务详情 | `ReviewRequest` / `TaskIntent` / `OperationPlan` / `ExecutionRecord` | 触发原因、候选任务、方案、来源调查 | 提交审核决策 | ready | 审核后可返回新建任务 id |
| `execution_feedback` | 任务详情 | `ExecutionRecord` | 作业结果、作业时间、面积/药量 | 提交执行结果 | ready | 仅用于正式作业任务 |
| `evaluation_entry` | 任务详情 | `FarmingTask` / `ExecutionRecord` | 满意度、评价时间、评价人、联系方式、备注 | 提交服务评价 | ready | 满意结束，不满意生成现场确认任务 |
| `service_effect_survey` | 服务评价不满意后 | `FarmingTask` / `ExecutionRecord` | 现场日期、实际情况、原因、备注 | 提交现场确认结果 | ready | 当前提交后无下游自动编排 |

---

## 4. 页面与接口依赖关系

### 4.1 `plan_create`

| action | method | path | 用途 |
|---|---|---|---|
| 查询稻作类型 | `GET` | `/api/code-dicts?category=culti_type` | 读取稻作类型选项 |
| 查询种植方式 | `GET` | `/api/code-dicts?category=sowingmtd` | 读取种植方式选项 |
| 查询品种 | `GET` | `/api/rice-varieties?query={keyword}&limit=20` | 读取品种选项 |
| 创建计划 | `POST` | `/api/planting-plans` | 创建 `PlantingPlan` |

创建成功后建议前端：

1. 跳转 `plan_detail`
2. 并行读取计划本体、`calendar-items`、`tasks`、`review-requests`

### 4.2 `plan_detail`

| action | method | path | 用途 |
|---|---|---|---|
| 查看计划详情 | `GET` | `/api/planting-plans/{plantingPlanId}` | 读取计划基础信息 |
| 查看预备农事项 | `GET` | `/api/planting-plans/{plantingPlanId}/calendar-items` | 读取 `CalendarItem` 列表 |
| 查看正式任务 | `GET` | `/api/planting-plans/{plantingPlanId}/tasks` | 读取 `FarmingTask` 列表 |
| 查看待审核事项 | `GET` | `/api/planting-plans/{plantingPlanId}/review-requests` | 读取 `ReviewRequest` 列表 |
| 查看事件时间线 | `GET` | `/api/planting-plans/{plantingPlanId}/event-records` | 读取 `EventRecord` 时间线 |

建议布局：

1. 顶部显示计划基础字段
2. 中部显示 `CalendarItem` / `FarmingTask`
3. 侧边或底部显示 `ReviewRequest`
4. 底部显示 `EventRecord`

### 4.3 `calendar_list`

| action | method | path | 用途 |
|---|---|---|---|
| 查看预备农事项 | `GET` | `/api/planting-plans/{plantingPlanId}/calendar-items` | 读取 `CalendarItem` 列表 |
| 查看正式任务 | `GET` | `/api/planting-plans/{plantingPlanId}/tasks` | 对照哪些事项已转正式任务 |

前端建议规则：

1. `CalendarItem.generated_task_id` 非空时显示“已生成正式任务”
2. `generated_task_id` 为空时显示“预备农事项”

### 4.4 `task_detail`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务详情 | `GET` | `/api/tasks/{taskId}` | 聚合读取任务、方案、执行、事件 |

`GET /api/tasks/{taskId}` 当前返回：

```json
{
  "task": {},
  "operation_plans": [],
  "executions": [],
  "execution_records": [],
  "review_request": null,
  "source_task_intent": null,
  "source_calendar_item": null,
  "source_execution_record": null,
  "downstream_calendar_items": [],
  "event_records": []
}
```

前端建议重点展示：

1. `task`
2. `operation_plans`
3. `execution_records`
4. `review_request`
5. `event_records`

### 4.5 `survey_entry`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取任务信息和历史 |
| 提交调查结果 | `POST` | `/api/tasks/{taskId}/survey-results` | 录入调查结果 |

通用请求格式：

```json
{
  "result_payload": {},
  "actual_start_at": "2026-05-26T09:00:00",
  "actual_end_at": "2026-05-26T09:30:00"
}
```

通用成功响应格式：

```json
{
  "execution_record_id": 11,
  "event_record_id": 12,
  "farming_task_ids": [],
  "task_intent_ids": [13],
  "review_request_ids": [14]
}
```

字段解释：

1. `farming_task_ids`：提交后直接生成的正式任务
2. `task_intent_ids`：提交后生成的建议态对象
3. `review_request_ids`：提交后生成的待审核事项

### 4.6 `review_request`

| action | method | path | 用途 |
|---|---|---|---|
| 查看复核详情 | `GET` | `/api/review-requests/{reviewRequestId}` | 读取审核上下文 |
| 提交审核结论 | `POST` | `/api/review-requests/{reviewRequestId}/resolve` | 提交复核决策 |

`POST /api/review-requests/{reviewRequestId}/resolve` 请求格式：

```json
{
  "decision": "approve",
  "decision_payload": {},
  "decision_note": "通过",
  "resolved_by": "agronomist_001"
}
```

成功响应格式：

```json
{
  "review_request_id": 21,
  "event_record_id": 31,
  "decision": "approve",
  "status": "resolved",
  "task_intent_ids": [41],
  "farming_task_ids": [51],
  "operation_plan_ids": [61],
  "resolved_at": "2026-05-26T11:00:00"
}
```

### 4.7 `execution_feedback`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取任务和当前方案 |
| 提交执行结果 | `POST` | `/api/tasks/{taskId}/execution-completions` | 录入正式作业执行结果 |

请求格式：

```json
{
  "operation_date": "2026-04-20T00:00:00",
  "result_payload": {
    "actual": "completed"
  },
  "actual_start_at": "2026-04-20T08:00:00",
  "actual_end_at": "2026-04-20T09:00:00",
  "actual_area": 20.5,
  "actual_amount": 8.0,
  "amount_unit": "kg"
}
```

成功响应格式：

```json
{
  "execution_id": 21,
  "execution_record_id": 22,
  "event_record_id": 23,
  "calendar_item_ids": [24, 25]
}
```

### 4.8 `evaluation_entry`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取服务评价任务上下文 |
| 提交服务评价 | `POST` | `/api/tasks/{taskId}/survey-results` | 录入服务评价结果 |

请求示例：

```json
{
  "result_payload": {
    "is_satisfied": false,
    "evaluated_at": "2026-05-26T10:30:00",
    "evaluator_name": "张三",
    "contact_info": "13800138000",
    "comment": "需要现场复查"
  }
}
```

行为约定：

1. `is_satisfied = true`：链路结束，响应中的 `farming_task_ids` 为空
2. `is_satisfied = false`：直接生成一个 `plant_protection.service_effect_survey` 正式任务，返回其 id 到 `farming_task_ids`

### 4.9 `service_effect_survey`

| action | method | path | 用途 |
|---|---|---|---|
| 查看任务上下文 | `GET` | `/api/tasks/{taskId}` | 读取现场确认任务上下文 |
| 提交现场确认结果 | `POST` | `/api/tasks/{taskId}/survey-results` | 录入现场实际情况和原因 |

请求示例：

```json
{
  "result_payload": {
    "survey_date": "20260501",
    "actual_situation": "现场确认局部杂草残留，未继续扩散。",
    "reason": "前期喷施覆盖不均匀。",
    "comment": "已向农户说明情况。"
  }
}
```

字段校验：

1. `survey_date` 必填
2. `actual_situation` 必填
3. `reason` 必填
4. `comment` 可选

行为约定：

1. 提交后链路结束
2. 当前不会自动生成 `TaskIntent`、`ReviewRequest` 或新的 `FarmingTask`

---

## 5. 页面级字段建议

### 5.1 `plan_create`

必填字段：

1. `plan_name`
2. `farm_id`
3. `field_ids`
4. `culti_type_code`
5. `planting_method_code`
6. `crop_name`
7. `variety_id`
8. `sowing_date`

其中需要特别注意：

1. `plan_code` 由后端生成，前端不传
2. `culti_type_code` 前端展示文案应使用“稻作类型”
3. `planting_method_code` 前端展示文案应使用“种植方式”
4. `variety_id` 前端展示文案应使用“品种”

可选字段：

1. `year`
2. `transplant_date`
3. `harvest_date`
4. `transplant_leaf_age`
5. `previous_harvest_date`
6. `ratoon_first_season_harvest_date`
7. `expected_harvest_date`
8. `status`
9. `task_generation_window_days`
10. `metadata`

### 5.2 `plan_detail`

建议至少展示：

1. `PlantingPlan.plan_name`
2. `PlantingPlan.crop_name`
3. `PlantingPlan.variety_name`
4. `PlantingPlan.sowing_date`
5. `PlantingPlan.status`
6. `CalendarItem.title`
7. `CalendarItem.suggested_start_date`
8. `CalendarItem.status`
9. `FarmingTask.title`
10. `FarmingTask.task_subtype`
11. `FarmingTask.status`
12. `ReviewRequest.title`
13. `ReviewRequest.status`
14. `EventRecord.event_type`
15. `EventRecord.processing_status`

### 5.3 `task_detail`

建议至少展示：

1. `task.title`
2. `task.task_subtype`
3. `task.status`
4. `task.planned_start_at`
5. `task.planned_end_at`
6. `task.generation_reason`
7. `operation_plans[].parameters`
8. `operation_plans[].basis`
9. `execution_records[].record_type`
10. `execution_records[].result_payload`
11. `event_records[].event_type`
12. `source_calendar_item`
13. `source_task_intent`
14. `review_request`

### 5.4 `survey_entry`

当前按任务 subtype 切表单：

1. `plant_protection.stem_leaf_weed_pre_survey`
2. `plant_protection.rice_safety_survey`
3. `plant_protection.control_effect_survey`
4. `plant_protection.service_effect_evaluation`
5. `plant_protection.service_effect_survey`

前端实现建议：

1. 页面骨架共用
2. 表单 schema 按 `task.task_subtype` 切换

### 5.5 `evaluation_entry`

必填字段：

1. `is_satisfied`
2. `evaluated_at`
3. `evaluator_name`
4. `contact_info`

可选字段：

1. `comment`

### 5.6 `service_effect_survey`

必填字段：

1. `survey_date`
2. `actual_situation`
3. `reason`

可选字段：

1. `comment`

---

## 6. 前端联调顺序建议

建议按以下顺序接入，而不是同时起 9 个页面：

1. `plan_create`
2. `plan_detail`
3. `calendar_list`
4. `task_detail`
5. `survey_entry`
6. `review_request`
7. `execution_feedback`
8. `evaluation_entry`
9. `service_effect_survey`

原因：

1. 前 7 个页面能先打通主杂草防治链路
2. 后 2 个页面是服务评估尾部链路，独立性更强

---

## 7. 当前已知限制

这些点前端需要按“当前后端真实状态”处理：

1. `plan_detail` 当前没有独立 `SystemNotification` 接口
2. `plan_detail` 当前没有独立 `CropStageState` 读取接口
3. 服务评价当前不是独立 `Evaluation` 对象，而是服务评价任务的调查结果录入
4. `service_effect_survey` 当前录入后链路直接结束
5. 若要演示后台自动把 `CalendarItem` 转为正式调查任务，需要本地启用 scheduler 或使用已有 seed / trace 流程

---

## 8. 给前端的实现建议

1. 所有写接口提交成功后，都优先使用返回的 id 刷新对应详情页，而不是只依赖本地状态推断
2. `survey-results` 返回值要统一处理 `farming_task_ids`、`task_intent_ids`、`review_request_ids`
3. `task_subtype` 应作为页面渲染和表单切换的主分流字段
4. `plan_detail` 第一版先做简化总览，不等待缺失对象补齐
5. `service_effect_survey` 第一版按终点表单实现，不预埋额外状态机
