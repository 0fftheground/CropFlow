# 生育期预测接口契约

本文档用于 CropFlow 后端与生育期算法服务联调，约定当前版本的请求和响应格式。

## 1. 基本信息

- algorithmCode: `stage_prediction_algorithm`
- algorithmName: 生育期预测算法
- purpose: 后端先准备种植基础信息、种植区域和标准化逐日天气数据，算法侧完成生育期积温阈值匹配、积温累计和生育期时间线计算；后端再保存 `StagePredictionSnapshot`、推导 `CropStageState`、维护 `CropThermalTimeState`
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

## 3. 当前职责边界

### 3.1 CropFlow 后端负责

1. 组织种植计划基础字段。
2. 组织种植区域字段：`adcode`、省、市、区县。
3. 从统一 weather provider 获取历史天气和预测天气，并标准化为连续逐日 `weather_data`。
4. 传入本次预测对应的业务日期 `as_of_date`。
5. 持久化算法响应，更新 `StagePredictionSnapshot`、`CropStageState`、`CropThermalTimeState`。

### 3.2 生育期算法负责

1. 根据品种、栽培类型、种植区域匹配生育期积温阈值。
2. 基于后端提供的逐日天气数据完成积温累计。
3. 计算并返回完整生育期时间线。
4. 返回阈值快照和当前累计积温快照，供后端落库。

## 4. 请求输入

| field | type | required | source | example | notes |
|---|---|---|---|---|---|
| `crop_name` | string | 是 | `PlantingPlan.cropName` | `水稻` | 当前 MVP 先按水稻处理 |
| `culti_type_code` | integer | 是 | `PlantingPlan.cultiTypeCode` | `5` | 栽培制度 code |
| `planting_method_code` | integer | 是 | `PlantingPlan.plantingMethodCode` | `1` | 种植方式 code |
| `variety_id` | integer | 是 | `PlantingPlan.varietyId` | `33` | 品种 ID |
| `variety_name` | string | 是 | `PlantingPlan.varietyName` | `黄广农占` | 品种名称 |
| `sowing_date` | string(date) | 是 | `PlantingPlan.sowingDate` | `2026-04-10` | ISO `YYYY-MM-DD` |
| `transplant_date` | string(date) | 否 | `PlantingPlan.transplantDate` | `2026-04-28` | 直播可为空 |
| `transplant_leaf_age` | string/number | 否 | `PlantingPlan.transplantLeafAge` | `4.5` | 插秧场景可传 |
| `as_of_date` | string(date) | 是 | Stage Orchestrator | `2026-05-27` | 表示本次预测对应的业务日期；同时作为天气观测/预测分界点 |
| `location` | object | 是 | `Farm` 结构化字段 | 见下方 | 用于区域阈值匹配 |
| `weather_data` | array | 是 | 后端 weather provider 组织 | 见下方 | 连续逐日天气数据，包含历史与预测 |
| `metadata` | object | 否 | `PlantingPlan.metadata` | `{}` | 当前版透传扩展字段；不要依赖字段顺序 |

### 4.1 `location` 结构

| field | type | required | example | notes |
|---|---|---|---|---|
| `adcode` | string | 是 | `430181` | 稳定行政区编码，算法主匹配键 |
| `province` | string | 是 | `湖南省` | 省份名称 |
| `city` | string | 是 | `长沙市` | 地级市名称 |
| `district_county` | string | 是 | `浏阳市` | 区 / 县 / 县级市名称 |
| `centroid_lat` | number | 否 | `28.1543` | 可选，当前版仅作透传 |
| `centroid_lon` | number | 否 | `113.6432` | 可选，当前版仅作透传 |

说明：

1. 当前后端会优先使用 `adcode` 作为稳定区域键，省市区县名称用于辅助匹配和排查。
2. 当前版区域信息由 `Farm` 结构化字段提供，不再从 `PlantingPlan.metadata` 透传。

### 4.2 `weather_data` 结构

`weather_data` 用于提供后端标准化后的连续逐日天气数据。当前版约定如下：

| field | type | required | example | notes |
|---|---|---|---|---|
| `date` | string(date) | 是 | `2026-05-27` | ISO `YYYY-MM-DD` |
| `avg_temp` | number | 是 | `26` | 当日平均气温 |
| `min_temp` | number | 否 | `22` | 当日最低气温 |
| `max_temp` | number | 否 | `30` | 当日最高气温 |
| `source_type` | string | 是 | `observed` / `forecast` / `climatology` | 真实历史、短期预测或长期气候平均补齐 |
| `data_version` | string | 否 | `weather-20260527-v1` | 后端气象数据版本，便于追踪 |

说明：

1. `weather_data` 必须按日期连续，且后端保证按时间正序传入。
2. 当前版由 CropFlow 后端统一取数和标准化，算法接口不自行向外部天气源取数。
3. `source_type=observed` 表示历史实况；`forecast` 表示短期预报；`climatology` 表示超出短期预报窗口后使用历史多年平均值补齐。
4. 当前接入的历史平均接口不返回“今天”数据，因此 `as_of_date` 当天会由短期预报接口补齐。
5. 当前版默认从 `sowing_date` 开始传天气；结束日期由后端按业务窗口组织，不由算法侧反向推断。

## 5. 请求示例

```json
{
  "crop_name": "水稻",
  "culti_type_code": 5,
  "planting_method_code": 1,
  "variety_id": 33,
  "variety_name": "黄广农占",
  "sowing_date": "2026-04-10",
  "transplant_date": null,
  "transplant_leaf_age": null,
  "as_of_date": "2026-05-27",
  "location": {
    "adcode": "430181",
    "province": "湖南省",
    "city": "长沙市",
    "district_county": "浏阳市"
  },
  "weather_data": [
    {
      "date": "2026-04-10",
      "avg_temp": 26,
      "source_type": "observed"
    },
    {
      "date": "2026-04-11",
      "avg_temp": 26,
      "source_type": "observed"
    },
    {
      "date": "2026-05-28",
      "avg_temp": 27,
      "source_type": "forecast",
      "data_version": "weather-20260527-v1"
    }
  ],
  "metadata": {}
}
```

## 6. 响应输出

| field | type | meaning | example | targetObject | targetField |
|---|---|---|---|---|---|
| `code` | integer | 调用结果码 | `200` | none | none |
| `msg` | string | 结果说明 | `success` | none | none |
| `data.algorithm_code` | string | 算法编码 | `stage_prediction_algorithm` | `StagePredictionSnapshot` | `algorithmCode` |
| `data.algorithm_version` | string | 算法版本 | `v1.0.0` | `StagePredictionSnapshot` | `algorithmVersion` |
| `data.stage_timeline` | object | 生育期时间线 | 见下方 | `StagePredictionSnapshot` | `stageTimeline` |
| `data.thermal_thresholds` | object | 阈值与积温快照 | 见下方 | `StagePredictionSnapshot` / `CropThermalTimeState` | `thermalThresholds` / 对应字段 |

### 6.1 `stage_timeline` 结构

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

1. 当前后端会根据 `stages[]` 中各节点的 `start_date` 推导当前阶段，不要求算法直接返回 `current_stage_code`。
2. `stage_code` 当前至少必须包含：
   - `tillering`
   - `pokou`
   - `heading`
   - `maturity`
3. 这四个节点会被植保病虫害调查窗口服务直接消费，分别映射为：
   - `tillering_date`
   - `pokou_date`
   - `heading_date`
   - `maturity_date`

### 6.2 `thermal_thresholds` 结构

```json
{
  "threshold_rule_id": "hn-late-rice-v1",
  "threshold_rule_version": "2026.05",
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

1. `threshold_rule_id`、`threshold_rule_version` 用于表达算法匹配到的阈值规则版本；当前后端会整体保存在 `StagePredictionSnapshot.thermalThresholds`。
2. `accumulated_thermal_time`、`base_temperature`、`thermal_time_unit`、`last_calculated_date` 会同步写入 `CropThermalTimeState`。
3. `stage_thresholds` 当前先整体保存到 `StagePredictionSnapshot.thermalThresholds`。

## 7. 响应示例

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
      "threshold_rule_id": "hn-late-rice-v1",
      "threshold_rule_version": "2026.05",
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

## 8. 异常返回

| code | meaning | retryable | fallbackAction | notes |
|---|---|---|---|---|
| `400` | 请求字段缺失或格式非法 | 否 | 修正请求字段后重试 | 至少返回缺失字段名 |
| `422` | 算法无法根据当前作物 / 品种 / 区域 / 天气生成阶段 | 否 | 记录失败事件，人工排查 | 用于业务上无可计算结果 |
| `500` | 算法内部异常 | 是 | 后端记录失败事件并按 job 重试策略处理 | 建议返回 trace id |
| `504` | 超时 | 是 | 后端记录失败事件并稍后重试 | 当前后端默认按同步失败处理 |

## 9. 当前版约束

1. 当前版由后端统一取天气，算法接口不自行拉外部气象数据。
2. 当前版算法需要同时完成阈值匹配和生育期计算，不只返回阈值表。
3. 当前版只要求返回预测时间线，不要求直接返回当前阶段。
4. `stage_timeline.stages` 必须按时间正序可排序，且每个节点必须有 `stage_code`、`stage_name`、`start_date`。
5. 病虫害调查依赖 `tillering`、`pokou`、`heading`、`maturity` 四个节点；若缺失，后端会判为不可消费。
6. 如后续需要支持天气重算或人工录入回写，优先在保持本契约兼容的前提下追加字段，不直接改名。

## 10. 输入边界说明

1. 当前契约不向算法接口暴露 `planting_plan_id`、`plan_code` 等系统内部业务标识。
2. 当前契约不再默认传 `expected_harvest_date`、`previous_harvest_date`、`ratoon_first_season_harvest_date`；如后续再生稻预测确实需要，再按算法需求单独补充。
3. 算法接口输入只保留参与区域阈值匹配、生育期计算和积温判断所需的农艺字段。
4. 计划维度的追踪、幂等、日志关联由 CropFlow 后端在调用侧和快照落库侧自己处理，不进入算法 contract。
