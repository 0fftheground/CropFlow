# 生育期预测接口契约

本文档用于 CropFlow 后端与生育期算法服务联调，约定当前版本的请求和响应格式。

## 1. 基本信息

- algorithmCode: `stage_prediction_algorithm`
- algorithmName: 生育期预测算法
- purpose: 根据种植计划基础信息返回生育期时间线与积温阈值快照，供 Stage Orchestrator 保存 `StagePredictionSnapshot`、推导 `CropStageState`、维护 `CropThermalTimeState`
- owner: 生育期算法接口开发同事
- endpoint: `POST /stage/predict`
- method: `POST`
- auth: 当前版默认内网服务，无额外鉴权；如后续增加鉴权，需保持 JSON body 不变

## 2. 触发时机

- upstream workflowKey / jobKey: `StagePredictionRefreshJob`
- trigger event:
  - `PlanCreated`
  - `PlanKeyInfoChanged`
  - 后续预留：`WeatherUpdated`、`ActualStageRecorded`
- trigger step: Plan Orchestrator 进入 Stage Orchestrator 后调用
- whether sync or async: 同步调用

## 3. 请求输入

| field | type | required | source | example | notes |
|---|---|---|---|---|---|
| `planting_plan_id` | integer | 是 | `PlantingPlan.id` | `1001` | 系统内部计划 ID |
| `plan_code` | string | 是 | `PlantingPlan.planCode` | `PLAN-20260527-001` | 便于算法侧排查日志 |
| `crop_name` | string | 是 | `PlantingPlan.cropName` | `水稻` | 当前 MVP 先按水稻处理 |
| `culti_type_code` | integer | 是 | `PlantingPlan.cultiTypeCode` | `5` | 栽培制度 code |
| `planting_method_code` | integer | 是 | `PlantingPlan.plantingMethodCode` | `1` | 种植方式 code |
| `variety_id` | integer | 是 | `PlantingPlan.varietyId` | `33` | 品种 ID |
| `variety_name` | string | 是 | `PlantingPlan.varietyName` | `黄广农占` | 品种名称 |
| `sowing_date` | string(date) | 是 | `PlantingPlan.sowingDate` | `2026-04-10` | ISO `YYYY-MM-DD` |
| `transplant_date` | string(date) | 否 | `PlantingPlan.transplantDate` | `2026-04-28` | 直播可为空 |
| `transplant_leaf_age` | string/number | 否 | `PlantingPlan.transplantLeafAge` | `4.5` | 插秧场景可传 |
| `expected_harvest_date` | string(date) | 否 | `PlantingPlan.expectedHarvestDate` | `2026-07-25` | 当前版可为空 |
| `previous_harvest_date` | string(date) | 否 | `PlantingPlan.previousHarvestDate` | `2026-01-15` | 再生季前茬可传 |
| `ratoon_first_season_harvest_date` | string(date) | 否 | `PlantingPlan.ratoonFirstSeasonHarvestDate` | `2026-07-20` | 再生季可传 |
| `as_of_date` | string(date) | 是 | Stage Orchestrator | `2026-05-27` | 表示本次预测对应的业务日期 |
| `metadata` | object | 否 | `PlantingPlan.metadata` | `{}` | 当前版透传扩展字段；不要依赖字段顺序 |

## 4. 请求示例

```json
{
  "planting_plan_id": 1001,
  "plan_code": "PLAN-20260527-001",
  "crop_name": "水稻",
  "culti_type_code": 5,
  "planting_method_code": 1,
  "variety_id": 33,
  "variety_name": "黄广农占",
  "sowing_date": "2026-04-10",
  "transplant_date": null,
  "transplant_leaf_age": null,
  "expected_harvest_date": null,
  "previous_harvest_date": null,
  "ratoon_first_season_harvest_date": null,
  "as_of_date": "2026-05-27",
  "metadata": {}
}
```

## 5. 响应输出

| field | type | meaning | example | targetObject | targetField |
|---|---|---|---|---|---|
| `code` | integer | 调用结果码 | `200` | none | none |
| `msg` | string | 结果说明 | `success` | none | none |
| `data.algorithm_code` | string | 算法编码 | `stage_prediction_algorithm` | `StagePredictionSnapshot` | `algorithmCode` |
| `data.algorithm_version` | string | 算法版本 | `v1.0.0` | `StagePredictionSnapshot` | `algorithmVersion` |
| `data.stage_timeline` | object | 生育期时间线 | 见下方 | `StagePredictionSnapshot` | `stageTimeline` |
| `data.thermal_thresholds` | object | 阈值与积温快照 | 见下方 | `StagePredictionSnapshot` / `CropThermalTimeState` | `thermalThresholds` / 对应字段 |

### 5.1 `stage_timeline` 结构

`stage_timeline` 固定使用以下结构：

```json
{
  "stages": [
    {
      "stage_code": "seedling",
      "stage_name": "苗期",
      "start_date": "2026-04-10",
      "end_date": "2026-04-19",
      "key_date": "2026-04-10"
    },
    {
      "stage_code": "tillering",
      "stage_name": "分蘖期",
      "start_date": "2026-04-20",
      "end_date": "2026-06-09",
      "key_date": "2026-04-20"
    },
    {
      "stage_code": "pokou",
      "stage_name": "破口期",
      "start_date": "2026-06-10",
      "end_date": "2026-06-17",
      "key_date": "2026-06-10"
    },
    {
      "stage_code": "heading",
      "stage_name": "齐穗期",
      "start_date": "2026-06-18",
      "end_date": "2026-07-19",
      "key_date": "2026-06-18"
    },
    {
      "stage_code": "maturity",
      "stage_name": "成熟期",
      "start_date": "2026-07-20",
      "end_date": "2026-07-20",
      "key_date": "2026-07-20"
    }
  ]
}
```

说明：

- 当前后端会根据 `stages[]` 中各节点的 `start_date` 推导当前阶段，不要求算法直接返回 `current_stage_code`
- `stage_code` 当前至少必须包含：
  - `tillering`
  - `pokou`
  - `heading`
  - `maturity`
- 这四个节点会被植保病虫害调查窗口服务直接消费，分别映射为：
  - `tillering_date`
  - `pokou_date`
  - `heading_date`
  - `maturity_date`

### 5.2 `thermal_thresholds` 结构

```json
{
  "base_temperature": 10,
  "thermal_time_unit": "degree_day",
  "accumulated_thermal_time": 780,
  "last_calculated_date": "2026-05-27",
  "data_version": "weather-20260527-v1",
  "stage_thresholds": {
    "tillering": 180,
    "pokou": 760,
    "heading": 820,
    "maturity": 1180
  }
}
```

说明：

- `accumulated_thermal_time`、`base_temperature`、`thermal_time_unit`、`last_calculated_date` 会同步写入 `CropThermalTimeState`
- `stage_thresholds` 当前先整体保存到 `StagePredictionSnapshot.thermalThresholds`

## 6. 响应示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "algorithm_code": "stage_prediction_algorithm",
    "algorithm_version": "v1.0.0",
    "stage_timeline": {
      "stages": [
        {
          "stage_code": "seedling",
          "stage_name": "苗期",
          "start_date": "2026-04-10",
          "end_date": "2026-04-19",
          "key_date": "2026-04-10"
        },
        {
          "stage_code": "tillering",
          "stage_name": "分蘖期",
          "start_date": "2026-04-20",
          "end_date": "2026-06-09",
          "key_date": "2026-04-20"
        },
        {
          "stage_code": "pokou",
          "stage_name": "破口期",
          "start_date": "2026-06-10",
          "end_date": "2026-06-17",
          "key_date": "2026-06-10"
        },
        {
          "stage_code": "heading",
          "stage_name": "齐穗期",
          "start_date": "2026-06-18",
          "end_date": "2026-07-19",
          "key_date": "2026-06-18"
        },
        {
          "stage_code": "maturity",
          "stage_name": "成熟期",
          "start_date": "2026-07-20",
          "end_date": "2026-07-20",
          "key_date": "2026-07-20"
        }
      ]
    },
    "thermal_thresholds": {
      "base_temperature": 10,
      "thermal_time_unit": "degree_day",
      "accumulated_thermal_time": 780,
      "last_calculated_date": "2026-05-27",
      "data_version": "weather-20260527-v1",
      "stage_thresholds": {
        "tillering": 180,
        "pokou": 760,
        "heading": 820,
        "maturity": 1180
      }
    }
  }
}
```

## 7. 异常返回

| code | meaning | retryable | fallbackAction | notes |
|---|---|---|---|---|
| `400` | 请求字段缺失或格式非法 | 否 | 修正请求字段后重试 | 至少返回缺失字段名 |
| `422` | 算法无法根据当前作物/品种/日期生成阶段 | 否 | 记录失败事件，人工排查 | 用于业务上无可计算结果 |
| `500` | 算法内部异常 | 是 | 后端记录失败事件并按 job 重试策略处理 | 建议返回 trace id |
| `504` | 超时 | 是 | 后端记录失败事件并稍后重试 | 当前后端默认按同步失败处理 |

## 8. 当前版约束

1. 当前版只要求返回预测时间线，不要求直接返回当前阶段。
2. `stage_timeline.stages` 必须按时间正序可排序，且每个节点必须有 `stage_code`、`stage_name`、`start_date`。
3. 病虫害调查依赖 `tillering`、`pokou`、`heading`、`maturity` 四个节点；若缺失，后端会判为不可消费。
4. 如后续需要支持天气重算或人工录入回写，优先在保持本契约兼容的前提下追加字段，不直接改名。
