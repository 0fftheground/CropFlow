# 植保前端 API Contract

> 本文档面向前端联调，描述当前后端已实现接口的真实出入参。  
> 口径以当前 FastAPI 路由和响应模型为准。

适用阶段：

```text
P2 - 植保链路前后端联调
```

基础信息：

```text
Base URL: {host}/api
Content-Type: application/json
```

通用返回说明：

1. 成功返回 `200` 或 `201`
2. 参数或业务校验失败返回 `400`
3. 资源不存在返回 `404`
4. 请求体结构错误返回 `422`
5. 未处理异常返回 `500`
6. 响应头会回写 `X-Request-ID`

错误响应格式：

```json
{
  "detail": "error message"
}
```

---

## 1. 接口目录

| 用途 | method | path |
|---|---|---|
| 健康检查 | `GET` | `/health` |
| 字典查询 | `GET` | `/code-dicts` |
| 品种模糊查询 | `GET` | `/rice-varieties` |
| 农场创建 | `POST` | `/farms` |
| 农场列表 | `GET` | `/farms` |
| 农场详情 | `GET` | `/farms/{farmId}` |
| 农场更新 | `PATCH` | `/farms/{farmId}` |
| 创建计划 | `POST` | `/planting-plans` |
| 计划列表 | `GET` | `/planting-plans` |
| 计划详情 | `GET` | `/planting-plans/{plantingPlanId}` |
| 更新计划 | `PATCH` | `/planting-plans/{plantingPlanId}` |
| 计划下 CalendarItem 列表 | `GET` | `/planting-plans/{plantingPlanId}/calendar-items` |
| 计划下 FarmingTask 列表 | `GET` | `/planting-plans/{plantingPlanId}/tasks` |
| 计划下 TaskIntent 列表 | `GET` | `/planting-plans/{plantingPlanId}/task-intents` |
| 计划下 ReviewRequest 列表 | `GET` | `/planting-plans/{plantingPlanId}/review-requests` |
| 计划下 EventRecord 列表 | `GET` | `/planting-plans/{plantingPlanId}/event-records` |
| 计划当前生育期状态 | `GET` | `/planting-plans/{plantingPlanId}/stage-state` |
| 计划积温状态 | `GET` | `/planting-plans/{plantingPlanId}/thermal-time-state` |
| 计划最新生育期预测快照 | `GET` | `/planting-plans/{plantingPlanId}/stage-predictions/latest` |
| 人工录入真实生育期 | `POST` | `/planting-plans/{plantingPlanId}/actual-stages` |
| 任务详情 | `GET` | `/tasks/{taskId}` |
| 调查结果录入 | `POST` | `/tasks/{taskId}/survey-results` |
| 执行结果录入 | `POST` | `/tasks/{taskId}/execution-completions` |
| 编辑最近一次执行记录 | `PATCH` | `/tasks/{taskId}/execution-records/latest` |
| 复核详情 | `GET` | `/review-requests/{reviewRequestId}` |
| 复核处理 | `POST` | `/review-requests/{reviewRequestId}/resolve` |

---

## 2. 公共响应对象

### 2.1 `PlantingPlanResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `plan_code` | `string` | 计划编码；由后端生成 |
| `plan_name` | `string` | 计划名称 |
| `farm_id` | `int` | 农场 id |
| `farm_name` | `string \| null` | 农场名称；由后端根据 `farm_id` 关联返回 |
| `field_ids` | `int[]` | 地块 id 列表 |
| `year` | `int \| null` | 年份 |
| `culti_type_code` | `int` | 稻作类型编码 |
| `planting_method_code` | `int` | 种植方式编码 |
| `crop_name` | `string` | 作物名称 |
| `variety_id` | `int` | 品种 id |
| `variety_name` | `string` | 品种名称 |
| `sowing_date` | `date` | 播种日期 |
| `transplant_date` | `date \| null` | 移栽日期 |
| `harvest_date` | `date \| null` | 收获日期 |
| `transplant_leaf_age` | `decimal \| null` | 移栽叶龄 |
| `previous_harvest_date` | `date \| null` | 上季收获日期 |
| `ratoon_first_season_harvest_date` | `date \| null` | 再生稻首季收获日期 |
| `expected_harvest_date` | `date \| null` | 预计收获日期 |
| `status` | `string` | 当前状态 |
| `task_generation_window_days` | `int` | 任务生成窗口天数 |
| `metadata` | `object` | 扩展信息 |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.2 `FarmResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 农场主键 |
| `farm_name` | `string` | 农场名称 |
| `external_farm_id` | `string \| null` | 外部农场 id；天气接口等外部系统联调使用 |
| `province` | `string \| null` | 省 |
| `city` | `string \| null` | 市 |
| `district_county` | `string \| null` | 区 / 县 |
| `adcode` | `string \| null` | 行政区编码 |
| `boundary_wkt` | `string \| null` | 地块边界 WKT；当前可为空 |
| `centroid_lat` | `decimal \| null` | 中心点纬度 |
| `centroid_lon` | `decimal \| null` | 中心点经度 |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.3 `CalendarItemResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `stage_code` | `string \| null` | 阶段编码 |
| `task_category` | `string` | 大类 |
| `task_subtype` | `string` | 子类 |
| `title` | `string` | 标题 |
| `description` | `string \| null` | 描述 |
| `suggested_start_date` | `date` | 建议开始日期 |
| `suggested_end_date` | `date` | 建议结束日期 |
| `status` | `string` | `active / generated / invalidated` |
| `generation_condition` | `object` | 生成条件 |
| `parent_task_id` | `int \| null` | 上游任务 id |
| `source_execution_id` | `int \| null` | 上游执行 id |
| `source_execution_record_id` | `int \| null` | 上游执行记录 id |
| `generated_task_id` | `int \| null` | 已生成的正式任务 id |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.4 `FarmingTaskResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `calendar_item_id` | `int \| null` | 来源 CalendarItem |
| `task_intent_id` | `int \| null` | 来源 TaskIntent |
| `review_request_id` | `int \| null` | 来源 ReviewRequest |
| `task_category` | `string` | 大类 |
| `task_subtype` | `string` | 子类 |
| `title` | `string` | 标题 |
| `description` | `string \| null` | 描述 |
| `target_stage_code` | `string \| null` | 目标阶段 |
| `planned_start_at` | `datetime \| null` | 计划开始时间 |
| `planned_end_at` | `datetime \| null` | 计划结束时间 |
| `priority` | `string` | 优先级 |
| `status` | `string` | 当前状态 |
| `execution_mode` | `string` | 执行方式 |
| `generation_reason` | `string \| null` | 生成原因 |
| `parent_task_id` | `int \| null` | 上游任务 id |
| `source_execution_id` | `int \| null` | 上游执行 id |
| `source_execution_record_id` | `int \| null` | 上游执行记录 id |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.5 `TaskIntentResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `task_category` | `string` | 大类 |
| `task_subtype` | `string` | 子类 |
| `priority` | `string` | 优先级 |
| `status` | `string` | `pending / converted / rejected / no_action / pending_more_info` |
| `trigger_type` | `string` | 触发事件类型 |
| `trigger_summary` | `string \| null` | 触发摘要 |
| `rule_result` | `object` | 结构化建议 |
| `suggested_action` | `string \| null` | 建议动作 |
| `need_more_info_fields` | `object` | 补充信息字段 |
| `no_action_reason` | `string \| null` | 无需处理原因 |
| `parent_task_id` | `int \| null` | 上游任务 id |
| `source_execution_id` | `int \| null` | 上游执行 id |
| `source_execution_record_id` | `int \| null` | 上游执行记录 id |
| `converted_task_id` | `int \| null` | 转出的正式任务 id |
| `source_event_id` | `int \| null` | 来源事件 id |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.6 `ReviewRequestResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `review_type` | `string` | 复核类型 |
| `status` | `string` | `open / resolved` |
| `priority` | `string` | 优先级 |
| `assigned_user_id` | `string \| null` | 指派人 |
| `source_entity_type` | `string` | 来源对象类型 |
| `source_entity_id` | `int` | 来源对象 id |
| `title` | `string` | 标题 |
| `description` | `string \| null` | 描述 |
| `decision` | `string \| null` | 复核结论 |
| `decision_payload` | `object` | 复核上下文和输入 |
| `resolved_by` | `string \| null` | 处理人 |
| `resolved_at` | `datetime \| null` | 处理时间 |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.7 `EventRecordResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int \| null` | 计划 id |
| `event_type` | `string` | 事件类型 |
| `event_category` | `string` | 事件分类 |
| `event_source` | `string` | 来源 |
| `source_system` | `string \| null` | 来源系统 |
| `source_record_id` | `string \| null` | 来源记录 id |
| `payload` | `object` | 事件内容 |
| `occurred_at` | `datetime` | 发生时间 |
| `received_at` | `datetime \| null` | 接收时间 |
| `processed_at` | `datetime \| null` | 处理时间 |
| `processing_status` | `string` | `received / processing / processed / failed` |
| `error_message` | `string \| null` | 错误信息 |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.8 `CropStageStateResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `current_stage_code` | `string` | 当前阶段编码；预测态通常为业务阶段，人工录入时也可能返回 raw stage code |
| `current_stage_name` | `string` | 当前阶段名称 |
| `stage_source` | `string` | `predicted / manual` |
| `effective_date` | `date` | 当前阶段生效日期 |
| `source_snapshot_id` | `int \| null` | 来源生育期快照 id |
| `last_updated_at` | `datetime \| null` | 业务更新时间 |
| `version` | `int` | 版本号 |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.9 `CropThermalTimeStateResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `accumulated_thermal_time` | `decimal` | 当前累计积温 |
| `thermal_time_unit` | `string` | 当前固定为 `degree_day` |
| `base_temperature` | `decimal \| null` | 基础温度；当前按亚种动态取值：`粳(sub=1)=10`，其他 `=12` |
| `start_date` | `date \| null` | 积温累计起点 |
| `last_calculated_date` | `date \| null` | 最近一次基于 observed 累积到的日期 |
| `threshold_snapshot_id` | `int \| null` | 阈值快照 id |
| `data_version` | `string \| null` | 天气版本摘要 |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

### 2.10 `StagePredictionSnapshotResponse`

| field | type | notes |
|---|---|---|
| `id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `prediction_version` | `int` | 快照版本 |
| `prediction_source` | `string` | `initial / plan_change / weather_update / runtime_refresh / manual_adjustment` |
| `algorithm_code` | `string` | 算法编码 |
| `algorithm_version` | `string \| null` | 算法版本 |
| `generated_at` | `datetime \| null` | 生成时间 |
| `input_payload` | `object` | 请求、重算摘要和审计信息 |
| `stage_timeline` | `object` | 后端派生的生育期时间线，包含 `stages` 和 `raw_stage_points` |
| `thermal_thresholds` | `object` | 积温阈值快照 |
| `source_event_id` | `int \| null` | 来源事件 id |
| `created_at` | `datetime \| null` | 创建时间 |
| `updated_at` | `datetime \| null` | 更新时间 |

`stage_timeline` 当前读取建议：

1. `stage_timeline.stages`：给现有关键业务节点使用
2. `stage_timeline.raw_stage_points`：给前端完整阶段展示使用
3. `raw_stage_points[*].season_scope`：`main / ratoon`
4. `raw_stage_points[*].source`：`predicted / manual`
5. 当前 raw stage points 覆盖完整主季 `BBCH13/21/28/41/42/44/45/50/51/55/58/89`；再生稻才会额外出现 `Z_BBCH51/58/89`

---

## 3. 计划接口

### 3.1 创建计划

`POST /api/planting-plans`

当前注意：

```text
1. `plan_code` 已改为后端自动生成。
2. 前端创建计划时不再传这个字段。
```

请求体：

| field | type | required | notes |
|---|---|---|---|
| `plan_name` | `string` | yes | 计划名称 |
| `farm_id` | `int` | yes | 农场 id |
| `field_ids` | `int[]` | yes | 地块 id 列表 |
| `culti_type_code` | `int` | yes | 稻作类型编码 |
| `planting_method_code` | `int` | yes | 种植方式编码 |
| `crop_name` | `string` | yes | 作物名称 |
| `variety_id` | `int` | yes | 品种 id |
| `sowing_date` | `date` | yes | 播种日期 |
| `year` | `int \| null` | no | 年份 |
| `transplant_date` | `date \| null` | no | 移栽日期 |
| `harvest_date` | `date \| null` | no | 收获日期 |
| `transplant_leaf_age` | `decimal \| null` | no | 移栽叶龄 |
| `previous_harvest_date` | `date \| null` | no | 上季收获日期 |
| `ratoon_first_season_harvest_date` | `date \| null` | no | 再生稻首季收获日期 |
| `expected_harvest_date` | `date \| null` | no | 预计收获日期 |
| `status` | `string` | no | 默认 `draft` |
| `task_generation_window_days` | `int` | no | 默认 `14` |
| `metadata` | `object` | no | 默认 `{}` |

成功响应：

1. `201 Created`
2. 响应体为 `PlantingPlanResponse`

建议前端展示口径：

1. `plan_code`：展示即可，不让用户手填
2. `culti_type_code`：UI 文案使用“稻作类型”
3. `planting_method_code`：UI 文案使用“种植方式”
4. `variety_id`：UI 文案使用“品种”

### 3.0 创建计划前的选项查询

#### 3.0.0 农场接口

前端创建计划前，应先查询农场列表，获取 `farm_id`。

##### 农场列表

`GET /api/farms`

成功响应：

1. `200 OK`
2. 响应体为 `FarmResponse[]`

##### 农场详情

`GET /api/farms/{farmId}`

成功响应：

1. `200 OK`
2. 响应体为 `FarmResponse`

##### 创建农场

`POST /api/farms`

请求体：

| field | type | required | notes |
|---|---|---|---|
| `farm_name` | `string` | yes | 农场名称 |
| `external_farm_id` | `string \| null` | no | 外部农场 id |
| `province` | `string` | yes | 省 |
| `city` | `string` | yes | 市 |
| `district_county` | `string` | yes | 区 / 县 |
| `adcode` | `string` | yes | 行政区编码 |
| `boundary_wkt` | `string \| null` | no | 边界 WKT |
| `centroid_lat` | `decimal \| null` | no | 中心点纬度 |
| `centroid_lon` | `decimal \| null` | no | 中心点经度 |

成功响应：

1. `201 Created`
2. 响应体为 `FarmResponse`

##### 更新农场

`PATCH /api/farms/{farmId}`

请求体字段与创建农场一致，但全部可选。

成功响应：

1. `200 OK`
2. 响应体为 `FarmResponse`

#### 3.0.1 字典查询

`GET /api/code-dicts?category={category}`

当前前端会用到：

1. `category=culti_type`
2. `category=sowingmtd`

响应体：

```json
[
  {
    "code": 5,
    "name": "早稻",
    "category": "culti_type"
  }
]
```

字段说明：

| field | type | notes |
|---|---|---|
| `code` | `int` | 实际提交值 |
| `name` | `string` | 展示名称 |
| `category` | `string` | 字典分类 |

#### 3.0.2 品种模糊查询

`GET /api/rice-varieties?query={keyword}&limit=20`

Query 参数：

| field | type | required | notes |
|---|---|---|---|
| `query` | `string \| null` | no | 品种名模糊匹配关键词 |
| `limit` | `int` | no | 默认 `20`，范围 `1~100` |

响应体：

```json
[
  {
    "id": 1,
    "name": "黄广农占",
    "approve_region": "长江中下游",
    "culti_type_code": 5,
    "sub_type_code": 9
  }
]
```

字段说明：

| field | type | notes |
|---|---|---|
| `id` | `int` | 实际提交的 `variety_id` |
| `name` | `string` | 品种名称 |
| `approve_region` | `string \| null` | 审定区域 |
| `culti_type_code` | `int \| null` | 对应稻作类型编码 |
| `sub_type_code` | `int \| null` | 品种子类型编码 |

### 3.2 计划列表

`GET /api/planting-plans`

Query 参数：

| field | type | required | notes |
|---|---|---|---|
| `statuses` | `string[]` | no | 可多值过滤 |

成功响应：

1. `200 OK`
2. 响应体为 `PlantingPlanResponse[]`

### 3.3 计划详情

`GET /api/planting-plans/{plantingPlanId}`

成功响应：

1. `200 OK`
2. 响应体为 `PlantingPlanResponse`

### 3.4 更新计划

`PATCH /api/planting-plans/{plantingPlanId}`

请求体字段与创建计划一致，但全部可选。

成功响应：

1. `200 OK`
2. 响应体为 `PlantingPlanResponse`

### 3.5 计划下 CalendarItem 列表

`GET /api/planting-plans/{plantingPlanId}/calendar-items`

成功响应：

1. `200 OK`
2. 响应体为 `CalendarItemResponse[]`

### 3.6 计划下 FarmingTask 列表

`GET /api/planting-plans/{plantingPlanId}/tasks`

成功响应：

1. `200 OK`
2. 响应体为 `FarmingTaskResponse[]`

### 3.7 计划下 TaskIntent 列表

`GET /api/planting-plans/{plantingPlanId}/task-intents`

成功响应：

1. `200 OK`
2. 响应体为 `TaskIntentResponse[]`

### 3.8 计划下 ReviewRequest 列表

`GET /api/planting-plans/{plantingPlanId}/review-requests`

成功响应：

1. `200 OK`
2. 响应体为 `ReviewRequestResponse[]`

### 3.9 计划下 EventRecord 列表

`GET /api/planting-plans/{plantingPlanId}/event-records`

成功响应：

1. `200 OK`
2. 响应体为 `EventRecordResponse[]`

### 3.10 计划当前生育期状态

`GET /api/planting-plans/{plantingPlanId}/stage-state`

成功响应：

1. `200 OK`
2. 响应体为 `CropStageStateResponse` 或 `null`

### 3.11 计划积温状态

`GET /api/planting-plans/{plantingPlanId}/thermal-time-state`

成功响应：

1. `200 OK`
2. 响应体为 `CropThermalTimeStateResponse` 或 `null`

### 3.12 计划最新生育期预测快照

`GET /api/planting-plans/{plantingPlanId}/stage-predictions/latest`

成功响应：

1. `200 OK`
2. 响应体为 `StagePredictionSnapshotResponse` 或 `null`

当前前端使用建议：

1. 展示阶段时间线优先读 `stage_timeline.raw_stage_points`
2. 需要排查 forecast/observed 回刷时，再读 `input_payload.recalculation_summary`
3. 当前阶段显示优先读 `/stage-state`，不要直接自己从 `stage_timeline` 反推

### 3.13 人工录入真实生育期

`POST /api/planting-plans/{plantingPlanId}/actual-stages`

请求体：

| field | type | required | notes |
|---|---|---|---|
| `stages` | `object` | yes | `rawStageCode -> date`；至少 1 条 |
| `source_record_id` | `string \| null` | no | 幂等来源记录 |
| `operator_id` | `string \| null` | no | 操作人 |
| `note` | `string \| null` | no | 备注 |
| `metadata` | `object` | no | 默认 `{}` |

`stages` 当前建议直接使用完整 raw stage code，例如：

1. `BBCH13`
2. `BBCH21`
3. `BBCH28`
4. `BBCH41`
5. `BBCH42`
6. `BBCH44`
7. `BBCH45`
8. `BBCH50`
9. `BBCH51`
10. `BBCH55`
11. `BBCH58`
12. `BBCH89`
13. `Z_BBCH51`
14. `Z_BBCH58`
15. `Z_BBCH89`

请求约束：

1. 只接受完整 raw stage code，不再接受业务阶段码如 `heading`
2. 不再接受旧数字 code，如 `21 / 50 / 58 / 89`
3. 日期第一版允许按联调需要录入未来日期，不再限制只能录入当天或过去日期
4. 同一次请求可同时提交多个 raw stage code，后端会按一批人工锚点一起应用，而不是逐条独立重算
5. 如同次请求中多个 raw stage 的日期顺序与 raw stage 顺序冲突，后端直接返回 `400`
6. 录入后后端会以这些 raw stage code 作为人工锚点重算预测；锚点之间已存在的中间 raw stage 日期默认保留，不强制改写
7. 如当前阶段发生变化，后端会继续触发 `StageChanged` 并刷新受影响的 `CalendarItem / FarmingTask`

成功响应：

1. `201 Created`
2. 响应体为 `EventRecordResponse[]`

---

## 4. 任务接口

### 4.1 任务详情

`GET /api/tasks/{taskId}`

响应体：

| field | type | notes |
|---|---|---|
| `task` | `FarmingTaskResponse` | 任务主对象 |
| `operation_plans` | `OperationPlanResponse[]` | 方案列表 |
| `executions` | `ExecutionResponse[]` | 执行列表 |
| `execution_records` | `ExecutionRecordResponse[]` | 执行记录列表 |
| `review_request` | `TaskDetailReviewRequestResponse \| null` | 关联复核 |
| `source_task_intent` | `TaskDetailTaskIntentResponse \| null` | 来源建议 |
| `source_calendar_item` | `TaskDetailCalendarItemResponse \| null` | 来源预备事项 |
| `source_execution_record` | `ExecutionRecordResponse \| null` | 来源执行记录 |
| `downstream_calendar_items` | `TaskDetailCalendarItemResponse[]` | 下游日历项 |
| `event_records` | `EventRecordResponse[]` | 相关事件 |

补充说明：

1. `source_calendar_item` 当前会带出 `generation_condition`
2. `plant_protection.regular_disease_pest_survey` 页面建议优先从 `source_calendar_item.generation_condition` 读取上下文
3. 常规病虫调查上下文中的 `rawPlan` 已统一为英文键：`survey_window`、`targets`、`exclude_reasons`
4. `survey_method` 可从 `source_calendar_item.generation_condition.surveyMethod` 回填

#### `OperationPlanResponse`

| field | type |
|---|---|
| `id` | `int` |
| `farming_task_id` | `int` |
| `plan_type` | `string` |
| `status` | `string` |
| `version` | `int` |
| `algorithm_code` | `string \| null` |
| `algorithm_version` | `string \| null` |
| `operation_area` | `object` |
| `operation_window_start` | `datetime \| null` |
| `operation_window_end` | `datetime \| null` |
| `execution_mode` | `string` |
| `parameters` | `object` |
| `prescription_map` | `object` |
| `acceptance_criteria` | `object` |
| `basis` | `string \| null` |
| `source_event_id` | `int \| null` |
| `created_at` | `datetime \| null` |
| `updated_at` | `datetime \| null` |

#### `ExecutionResponse`

| field | type |
|---|---|
| `id` | `int` |
| `planting_plan_id` | `int` |
| `farming_task_id` | `int` |
| `operation_plan_id` | `int \| null` |
| `execution_mode` | `string` |
| `status` | `string` |
| `assigned_to_type` | `string \| null` |
| `assigned_to_id` | `string \| null` |
| `external_system_code` | `string \| null` |
| `external_execution_id` | `string \| null` |
| `started_at` | `datetime \| null` |
| `completed_at` | `datetime \| null` |
| `failure_reason` | `string \| null` |
| `created_at` | `datetime \| null` |
| `updated_at` | `datetime \| null` |

#### `ExecutionRecordResponse`

| field | type |
|---|---|
| `id` | `int` |
| `planting_plan_id` | `int` |
| `execution_id` | `int` |
| `record_type` | `string` |
| `operation_date` | `date \| null` |
| `record_time` | `datetime` |
| `actual_start_at` | `datetime \| null` |
| `actual_end_at` | `datetime \| null` |
| `actual_area` | `decimal \| null` |
| `actual_amount` | `decimal \| null` |
| `amount_unit` | `string \| null` |
| `result_payload` | `object` |
| `attachments` | `array` |
| `created_at` | `datetime \| null` |
| `updated_at` | `datetime \| null` |

前端展示建议：

1. `execution_records` 已包含已完成任务的执行结果，不要因为任务状态为 `completed` 就隐藏这块
2. 建议优先展示最近一条记录的：
   `operation_date`
   `actual_start_at`
   `actual_end_at`
   `actual_area`
   `actual_amount`
   `amount_unit`
   `result_payload`
3. 当前 `execution_records` 按最近记录优先返回，前端可直接把 `execution_records[0]` 当作“最近一次执行结果”

### 4.2 调查结果录入

`POST /api/tasks/{taskId}/survey-results`

通用请求体：

| field | type | required | notes |
|---|---|---|---|
| `result_payload` | `object` | yes | 业务表单主体 |
| `actual_start_at` | `datetime \| null` | no | 实际开始时间 |
| `actual_end_at` | `datetime \| null` | no | 实际结束时间 |

成功响应：

| field | type | notes |
|---|---|---|
| `execution_record_id` | `int` | 新建执行记录 id |
| `event_record_id` | `int` | 新建事件 id |
| `farming_task_ids` | `int[]` | 直接生成的正式任务 |
| `task_intent_ids` | `int[]` | 新建建议 |
| `review_request_ids` | `int[]` | 新建待审核事项 |

#### 当前已支持的 `result_payload` 口径

##### `plant_protection.stem_leaf_weed_pre_survey`

最小示例：

```json
{
  "survey_date": "20260418",
  "rice_leaf_age": 4.5,
  "BaiCao": { "leaf_age": 2, "mass": 100 },
  "QianJinZi": { "leaf_age": 0, "mass": 0 },
  "KuoYeCao": { "mass": 0 },
  "SuoCao": { "mass": 0 }
}
```

##### `plant_protection.rice_safety_survey`

最小示例：

```json
{
  "survey_date": "20260423",
  "rice_injury_level": "无"
}
```

##### `plant_protection.control_effect_survey`

最小示例：

```json
{
  "survey_date": "20260427",
  "control_date": "20260420",
  "previous_injury_level": "无",
  "survey_data_before_treatment": {},
  "rice_leaf_age": 4.5,
  "rice_injury_level": "无",
  "BaiCao": { "control_effect": 1, "leaf_age": 0, "mass": 0 },
  "QianJinZi": { "control_effect": 1, "leaf_age": 0, "mass": 0 },
  "KuoYeCao": { "control_effect": 1, "mass": 0 },
  "SuoCao": { "control_effect": 1, "mass": 0 }
}
```

##### `plant_protection.regular_disease_pest_survey`

推荐示例：

```json
{
  "survey_date": "20260603",
  "survey_method": "一级理论防治日期",
  "bbch_stage": 23,
  "ErHuaMing": {
    "dead_sheath_rate": 0,
    "dead_heart_rate": 0,
    "main_larval_instars": 0,
    "damaged_plant_rate": 0
  },
  "DaoZongJuanYeMing": {
    "rolled_leaf_tips_per_100_hills": 0,
    "larvae_count": 0,
    "moths_per_square_meter": 0
  },
  "DaoFeiShi": {
    "insects_per_100_hills": 12
  },
  "DaoWenBing": {
    "acute_lesion": false,
    "diseased_leaf_rate": 0
  },
  "WenKuBing": {
    "lesion_on_upper_leaf_sheath": false,
    "diseased_hill_rate": 0
  }
}
```

字段说明：

1. `survey_date` 必填，格式建议用 `YYYYMMDD`
2. `survey_method` 仅支持 `一级理论防治日期 / 生育期`；建议直接回传任务上下文中的调查日期来源；第一版按只读回填处理
3. `bbch_stage` 为当前调查时的 BBCH 阶段数值
4. 动态对象建议优先按任务上下文展开；上下文来源优先取 `source_calendar_item.generation_condition.rawPlan.targets`
5. `source_calendar_item.generation_condition.rawPlan` 中的窗口和对象字段使用英文键：`survey_window`、`targets`、`exclude_reasons`
6. `cultivation_type=早稻` 时，任务上下文可能不包含 `DaoFeiShi`
7. 第一版提交口径仍建议按完整 5 类对象 schema 回传；未发现病虫时显式传 `0 / false`

行为：

1. 常规情况下会生成一个 `plant_protection.disease_pest_control` 的 `TaskIntent`，同时生成 `review_request_ids`
2. 如果理论防治结果为无需防治，或气象调整后无可执行日期，则返回 `task_intent_ids`，但不会生成 `review_request_ids`
3. 前端不要假设病虫调查提交后一定进入审核，也不要假设一定直接结束

##### `plant_protection.sudden_disease_pest_survey`

推荐示例：

```json
{
  "survey_date": "20260629",
  "bbch_stage": 45,
  "ErHuaMing": {
    "dead_sheath_rate": 0,
    "dead_heart_rate": 0,
    "main_larval_instars": 0,
    "damaged_plant_rate": 0
  },
  "DaoZongJuanYeMing": {
    "rolled_leaf_tips_per_100_hills": 0,
    "larvae_count": 0,
    "moths_per_square_meter": 0
  },
  "DaoFeiShi": {
    "insects_per_100_hills": 0
  },
  "DaoWenBing": {
    "acute_lesion": true,
    "diseased_leaf_rate": 5
  },
  "WenKuBing": {
    "lesion_on_upper_leaf_sheath": false,
    "diseased_hill_rate": 0
  }
}
```

字段说明：

1. `survey_date` 必填
2. `bbch_stage` 建议按实际调查阶段传入
3. 第一版仍建议按统一完整 schema 组装 5 类对象字段组；当前重点对象可在 UI 上优先展示，其余对象默认回传零值

行为：

1. 常规情况下会生成一个 `plant_protection.disease_pest_control` 的 `TaskIntent`
2. 若与已有常规病虫防治建议满足合并条件，后端可能关闭旧的 `TaskIntent / ReviewRequest`，并返回新的合并后 `task_intent_ids / review_request_ids`
3. 若理论防治结果为无需防治，则只返回 `task_intent_ids`，且对应 intent 状态为 `no_action`

病虫对象字段对照表：

| 对象 key | 中文建议 | 字段 | type | 取值/单位 | 说明 |
|---|---|---|---|---|---|
| `ErHuaMing` | 二化螟 | `dead_sheath_rate` | `number` | `0~1` | 枯鞘率 |
| `ErHuaMing` | 二化螟 | `dead_heart_rate` | `number` | `0~1` | 枯心率 |
| `ErHuaMing` | 二化螟 | `main_larval_instars` | `int` | `0~6` | 主要虫龄，`0` 表示未发现或无主要虫龄 |
| `ErHuaMing` | 二化螟 | `damaged_plant_rate` | `number` | `0~1` | 虫伤株率 |
| `DaoFeiShi` | 稻飞虱 | `insects_per_100_hills` | `number` | `>=0` | 百丛虫量 |
| `DaoWenBing` | 稻瘟病 | `acute_lesion` | `bool` | `true/false` | 是否发现急性病斑 |
| `DaoWenBing` | 稻瘟病 | `diseased_leaf_rate` | `number` | `0~1` | 病叶率 |
| `WenKuBing` | 纹枯病 | `lesion_on_upper_leaf_sheath` | `bool` | `true/false` | 倒 2 叶鞘及以上是否发现病斑 |
| `WenKuBing` | 纹枯病 | `diseased_hill_rate` | `number` | `0~1` | 病丛率 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `rolled_leaf_tips_per_100_hills` | `number` | `>=0` | 百丛束尖数 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `larvae_count` | `number` | `>=0` | 幼虫数量 |
| `DaoZongJuanYeMing` | 稻纵卷叶螟 | `moths_per_square_meter` | `number` | `>=0` | 每平方米蛾量 |

组装建议：

1. 第一版病虫对象范围按完整 5 类实现：`DaoFeiShi`、`DaoWenBing`、`ErHuaMing`、`DaoZongJuanYeMing`、`WenKuBing`
2. 每个对象字段组都作为 `result_payload` 下的一个子对象，不要拍平成顶层字段
3. `survey_date`、`survey_method`、`bbch_stage` 仍保持在 `result_payload` 顶层
4. `survey_method` 只在常规病虫调查页展示，并按只读字段回填；突发病虫调查默认不展示
5. 前端建议统一使用数字输入框 / 布尔开关；`main_larval_instars` 用整数输入
6. 第一版提交口径建议直接按完整 5 类对象 schema 回传；重点对象可优先展示，非重点对象可折叠但仍需带默认零值
7. 对于未发现病虫或调查值为零，字段组仍应保留并显式传 `0 / false`，不要依赖“省略字段组”表达零值

##### `plant_protection.service_effect_evaluation`

| field | type | required | notes |
|---|---|---|---|
| `is_satisfied` / `isSatisfied` | `bool` | yes | 是否满意 |
| `evaluated_at` / `evaluatedAt` | `datetime` | no | 评价时间 |
| `evaluator_name` / `evaluatorName` | `string` | no | 评价人 |
| `contact_info` / `contactInfo` | `string` | no | 联系方式 |
| `comment` | `string` | no | 备注 |

行为：

1. `true`：结束
2. `false`：会创建一个 `plant_protection.service_effect_survey` 正式任务，返回到 `farming_task_ids`

##### `plant_protection.service_effect_survey`

| field | type | required | notes |
|---|---|---|---|
| `survey_date` / `surveyDate` | `date` | yes | 现场确认日期 |
| `actual_situation` / `actualSituation` | `string` | yes | 现场实际情况 |
| `reason` | `string` | yes | 原因 |
| `comment` | `string` | no | 备注 |

行为：

1. 当前录入后链路结束
2. 当前不会新增 `TaskIntent`、`ReviewRequest`、`FarmingTask`

### 4.3 执行结果录入

`POST /api/tasks/{taskId}/execution-completions`

请求体：

| field | type | required | notes |
|---|---|---|---|
| `result_payload` | `object` | no | 默认 `{}` |
| `operation_date` | `datetime` | yes | 作业日期 |
| `actual_start_at` | `datetime \| null` | no | 实际开始时间 |
| `actual_end_at` | `datetime \| null` | no | 实际结束时间 |
| `actual_area` | `decimal \| null` | no | 实际面积 |
| `actual_amount` | `decimal \| null` | no | 实际药量/肥量 |
| `amount_unit` | `string \| null` | no | 单位 |

成功响应：

| field | type | notes |
|---|---|---|
| `execution_id` | `int` | 执行 id |
| `execution_record_id` | `int` | 执行记录 id |
| `event_record_id` | `int` | 事件 id |
| `operation_date` | `date \| null` | 本次作业日期；当前由 `ExecutionCompleted` 事件回填到响应 |
| `calendar_item_ids` | `int[]` | 新生成的下游 CalendarItem |

#### `plant_protection.disease_pest_control`

病虫正式防治任务当前复用通用执行结果录入接口，没有单独的专用路由。

最小示例：

```json
{
  "operation_date": "2026-05-09T09:00:00",
  "result_payload": {
    "operator": "agronomist-demo",
    "targets": ["二化螟", "稻瘟病", "稻飞虱"],
    "note": "local disease pest control smoke"
  },
  "actual_start_at": "2026-05-09T09:00:00",
  "actual_end_at": "2026-05-09T10:00:00",
  "actual_area": 12.5,
  "actual_amount": 3.0,
  "amount_unit": "亩"
}
```

行为：

1. 当前会生成执行记录和 `ExecutionCompleted` 事件
2. 当前病虫正式防治完成后，默认不会像杂草那样继续自动生成药后调查 `CalendarItem`
3. 成功响应仍使用通用格式；病虫任务下 `calendar_item_ids` 可能为空，前端不要假设一定会生成下游事项

### 4.4 编辑最近一次执行记录

`PATCH /api/tasks/{taskId}/execution-records/latest`

用途：

1. 仅修正该任务最近一次 `ExecutionRecord`
2. 当前不支持编辑任意历史执行记录
3. 当前不支持修改执行、任务、方案之间的关联关系

请求体：

| field | type | required | notes |
|---|---|---|---|
| `operation_date` | `datetime \| null` | no | 本次作业日期；仅保留日期部分，后端会同步更新对应 `ExecutionCompleted.operationDate` |
| `result_payload` | `object \| null` | no | 执行结果补充信息；整体替换 |
| `actual_start_at` | `datetime \| null` | no | 实际开始时间 |
| `actual_end_at` | `datetime \| null` | no | 实际结束时间；如变更会同步更新 `Execution.completed_at` |
| `actual_area` | `decimal \| null` | no | 实际面积 |
| `actual_amount` | `decimal \| null` | no | 实际药量/肥量 |
| `amount_unit` | `string \| null` | no | 单位 |

请求约束：

1. 至少传 1 个可编辑字段
2. 只更新最后一条执行记录
3. 如果任务没有执行记录，返回 `400`
4. 如果传入值与当前记录完全一致，返回 `400`
5. 更新后后端会新增 `ExecutionRecordUpdated` 事件，前端不需要自己补审计逻辑

成功响应：

| field | type | notes |
|---|---|---|
| `execution_id` | `int` | 执行 id |
| `execution_record_id` | `int` | 被更新的执行记录 id |
| `event_record_id` | `int` | 新建审计事件 id |
| `operation_date` | `date \| null` | 当前执行记录对应的作业日期 |
| `updated_fields` | `string[]` | 本次实际发生变化的字段 |

最小示例：

```json
{
  "operation_date": "2026-05-12T00:00:00",
  "actual_end_at": "2026-05-11T09:30:00",
  "actual_amount": 10.5,
  "result_payload": {
    "note": "corrected"
  }
}
```

成功响应示例：

```json
{
  "execution_id": 21,
  "execution_record_id": 22,
  "event_record_id": 24,
  "operation_date": "2026-05-12",
  "updated_fields": [
    "operation_date",
    "actual_end_at",
    "actual_amount",
    "result_payload",
    "record_time"
  ]
}
```

前端使用建议：

1. `task_detail` 若存在 `execution_records[0]`，可以显示“编辑执行结果”
2. 编辑成功后直接重新请求 `GET /api/tasks/{taskId}` 刷新详情
3. 不要在前端尝试维护历史 diff，直接使用 `updated_fields` 和事件时间线即可

---

## 5. 复核接口

### 5.1 复核详情

`GET /api/review-requests/{reviewRequestId}`

响应体：

| field | type | notes |
|---|---|---|
| `review_request_id` | `int` | 主键 |
| `planting_plan_id` | `int` | 计划 id |
| `review_type` | `string` | 复核类型 |
| `status` | `string` | 当前状态 |
| `decision` | `string \| null` | 已提交结论 |
| `title` | `string` | 标题 |
| `description` | `string \| null` | 描述 |
| `decision_payload` | `object` | 决策上下文 |
| `resolved_by` | `string \| null` | 处理人 |
| `resolved_at` | `datetime \| null` | 处理时间 |
| `source_task_intent` | `ReviewRequestTaskIntentResponse \| null` | 来源建议 |
| `linked_farming_task` | `ReviewRequestFarmingTaskResponse \| null` | 已关联正式任务 |
| `operation_plans` | `ReviewRequestOperationPlanResponse[]` | 候选方案 |
| `source_execution_record` | `ReviewRequestExecutionRecordResponse \| null` | 来源调查记录 |
| `event_records` | `ReviewRequestEventRecordResponse[]` | 相关事件 |

### 5.2 复核处理

`POST /api/review-requests/{reviewRequestId}/resolve`

请求体：

| field | type | required | notes |
|---|---|---|---|
| `decision` | `string` | yes | 见下方枚举 |
| `decision_payload` | `object` | no | 默认 `{}` |
| `decision_note` | `string \| null` | no | 备注 |
| `resolved_by` | `string \| null` | no | 处理人 |

允许的 `decision`：

1. `approve`
2. `reject`
3. `adjust`
4. `no_action`
5. `need_more_info`

成功响应：

| field | type | notes |
|---|---|---|
| `review_request_id` | `int` | 复核 id |
| `event_record_id` | `int` | 事件 id |
| `decision` | `string \| null` | 最终结论 |
| `status` | `string` | 当前状态 |
| `task_intent_ids` | `int[]` | 受影响建议 |
| `farming_task_ids` | `int[]` | 新建正式任务 |
| `operation_plan_ids` | `int[]` | 新建方案 |
| `resolved_at` | `datetime \| null` | 处理时间 |

---

## 6. 前端实现时的接口消费建议

1. 所有写接口成功后都用返回 id 刷新详情页
2. `survey-results` 是多分支接口，前端必须检查 `farming_task_ids`、`task_intent_ids`、`review_request_ids`
3. `task_subtype` 是页面表单切换的主分流字段
4. `404` 统一可按“对象不存在或已删除”处理
5. `400` 统一可按业务校验失败处理，直接展示 `detail`
6. 如果要排查后端日志或联调问题，记录响应头中的 `X-Request-ID`

---

## 7. 当前需要特别注意的 code / id 字段

### 7.1 前端需要传编码，且已有查询接口

| field | UI 应显示什么 | 当前真实传值 | 当前问题 |
|---|---|---|---|
| `culti_type_code` | 稻作类型 | code_dict.code | 用 `/api/code-dicts?category=culti_type` 查询 |
| `planting_method_code` | 种植方式 | code_dict.code | 用 `/api/code-dicts?category=sowingmtd` 查询 |
| `variety_id` | 品种 | rice_variety.id | 用 `/api/rice-varieties?query=` 查询 |
| `farm_id` | 农场 | farm.id | 用 `/api/farms` 查询 |

### 7.2 当前只适合机器分流，不适合直接展示给用户

这些字段当前建议由前端本地映射中文文案，不要直接裸展示：

1. `task_subtype`
2. `review_type`
3. `event_type`
4. `record_type`
5. `stage_code`
6. 各类 `status`
