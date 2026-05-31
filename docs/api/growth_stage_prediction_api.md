# 生育期阈值规则接口契约

本文档用于 CropFlow 后端与生育期算法服务联调，约定建议收敛的下一版请求和响应格式。

## 0. 当前状态说明

1. 当前后端实现已开始按 `vNext` 口径收敛：算法请求不再传 `weather_data`，后端本地负责天气驱动的积温累计与阶段推进。
2. 当前建议主契约仍以“算法返回可执行的积温规则包，后端派生业务阶段日期”为主。
3. 如算法侧需要补充阶段点返回，当前只要求返回业务必需的部分原始阶段点，不承诺返回完整 `stage_timeline`；现阶段确认的业务节点 raw code 为 `21=分蘖期(tillering)`、`51=破口期(pokou)`、`58=齐穗期(heading)`、`89=成熟期(maturity)`。
4. 在代码与算法服务完成同步改造前，本文档仍作为 handoff 目标口径；如真实返回字段与本文档不同，应优先显式补充差异说明。

## 1. 基本信息

- algorithmCode: `stage_prediction_algorithm`
- algorithmName: 生育期阈值规则匹配
- purpose: 后端先准备种植基础信息和种植区域，算法侧完成生育期阈值规则匹配并返回可执行规则包；后端据此维护 `CropThermalTimeState`、推导 `CropStageState`、生成或重算阶段日期
- owner: 生育期算法接口开发同事
- endpoint: `POST /stage/predict`
- method: `POST`
- auth: 当前版默认内网服务，无额外鉴权；如后续增加鉴权，需保持 JSON body 不变

说明：

1. 当前文档先沿用既有 `POST /stage/predict` 路径，避免接口路径和业务语义同时改动。
2. 如果算法侧希望把“规则匹配”和“时间线预测”显式拆开，后续可另议新的 endpoint 名称，但本期先不展开。

## 2. 触发时机

- upstream workflowKey / jobKey: `StagePredictionRefreshJob`
- trigger event:
  - `PlanCreated`
  - `PlanKeyInfoChanged`
  - 规则版本变化后的人工作业重算
- trigger step: Plan Orchestrator 进入 Stage Orchestrator 后调用
- whether sync or async: 同步调用

说明：

1. `WeatherUpdated` 默认不再直接触发算法接口重调。
2. `WeatherUpdated` 到来后，由 CropFlow 后端基于最新天气增量更新累计积温，并判断是否跨越阶段阈值。
3. `ActualStageRecorded` 进入后，是否需要重新匹配阈值规则，取决于业务是否修改了会影响规则匹配的计划信息；默认不直接重调算法。

## 3. 职责边界

### 3.1 CropFlow 后端负责

1. 组织种植计划基础字段。
2. 组织种植区域字段：`adcode`、省、市、区县。
3. 从统一 weather provider 获取历史天气和预测天气。
4. 根据算法返回的规则包累计积温、维护 `CropThermalTimeState`。
5. 根据累计积温和阶段阈值推导 `CropStageState`。
6. 根据连续天气序列推导各阶段日期，并回写 `StagePredictionSnapshot` 或其他派生快照。
7. 处理 `WeatherUpdated`、`ActualStageRecorded`、日历重算和幂等控制。

### 3.2 生育期算法负责

1. 根据品种、栽培类型、种植区域匹配生育期阈值规则。
2. 返回完整的积温计算规则，而不只返回单个基础温度。
3. 返回阶段阈值、规则版本和必要的计算语义，保证后端可独立复现积温累计和阶段推进。
4. 不再负责基于天气数据直接计算完整 `stage_timeline`。
5. 如需要附带阶段点，算法只返回当前业务必需的原始阶段点集合，后续可随新增农事需求再扩展。

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
| `location` | object | 是 | `Farm` 结构化字段 | 见下方 | 用于区域阈值匹配 |
| `metadata` | object | 否 | `PlantingPlan.metadata` | `{}` | 当前版透传扩展字段；不要依赖字段顺序 |

说明：

1. `weather_data` 不再进入算法请求体。
2. `as_of_date` 不再作为规则匹配必填字段；如果后续算法确认规则匹配与业务日期有关，再单独加回。
3. `crop_name` 当前版本固定传 `水稻`；若为其他作物，算法应返回不支持。
4. `transplant_leaf_age` 表示移栽时叶龄，单位为“叶”；允许整数或 1 位小数，例如 `4`、`4.5`。
5. `transplant_leaf_age` 仅在插秧场景且规则匹配依赖该字段时使用；直播场景可为空。

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

1. 后端优先使用 `adcode` 作为稳定区域键，省市区县名称用于辅助匹配和排查。
2. 区域信息由 `Farm` 结构化字段提供，不再从 `PlantingPlan.metadata` 透传。

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
  "location": {
    "adcode": "430181",
    "province": "湖南省",
    "city": "长沙市",
    "district_county": "浏阳市"
  },
  "metadata": {}
}
```

## 6. 响应输出

| field | type | meaning | example | targetObject | targetField |
|---|---|---|---|---|---|
| `code` | integer | 调用结果码 | `200` | none | none |
| `msg` | string | 结果说明 | `success` | none | none |
| `data.algorithm_code` | string | 算法编码 | `stage_prediction_algorithm` | `StagePredictionSnapshot` | `algorithmCode` |
| `data.algorithm_version` | string | 算法版本 | `v2.0.0` | `StagePredictionSnapshot` | `algorithmVersion` |
| `data.threshold_rule` | object | 可执行的积温规则包 | 见下方 | `StagePredictionSnapshot` / `CropThermalTimeState` | `thermalThresholds` / 对应字段 |

### 6.1 `threshold_rule` 结构

```json
{
  "threshold_rule_id": "hn-late-rice-v2",
  "threshold_rule_version": "2026.05",
  "thermal_time_unit": "degree_day",
  "base_temperature": 10,
  "upper_temperature_cap": 30,
  "lower_temperature_floor": 10,
  "calculation_method": "avg_temp_minus_base_capped",
  "rounding_rule": "keep_1_decimal_daily_keep_1_decimal_accumulated",
  "effective_date_rule": "threshold_reached_same_day",
  "stage_thresholds": {
    "tillering": 180,
    "pokou": 760,
    "heading": 820,
    "maturity": 1180
  }
}
```

字段说明：

| field | type | required | meaning | notes |
|---|---|---|---|---|
| `threshold_rule_id` | string | 是 | 阈值规则主标识 | 用于追踪命中的是哪套规则 |
| `threshold_rule_version` | string | 是 | 规则版本 | 后续规则调整必须升版本 |
| `thermal_time_unit` | string | 是 | 积温单位 | 当前建议固定 `degree_day` |
| `base_temperature` | number | 是 | 基础温度 | 用于扣减基准温度 |
| `upper_temperature_cap` | number | 否 | 高温截断上限 | 无上限时可为 `null` |
| `lower_temperature_floor` | number | 否 | 低温截断下限 | 与 `base_temperature` 不必强绑定，但当前建议保持一致 |
| `calculation_method` | string | 是 | 日积温计算方法 | 例如 `avg_temp_minus_base_capped` |
| `rounding_rule` | string | 是 | 日积温与累计积温取整规则 | 必须稳定，不可让后端自行猜测 |
| `effective_date_rule` | string | 是 | 首次跨阈值后的生效日规则 | 例如达到阈值当天进入新阶段 |
| `stage_thresholds` | object | 是 | 各阶段累计积温阈值 | 阶段 code 作为 key |

说明：

1. `threshold_rule` 必须足够让后端基于天气序列独立复现积温累计过程。
2. 如果算法还有其他影响阶段推进的特殊规则，必须显式返回字段，不允许仅放在口头约定里。
3. `stage_thresholds` 当前至少必须包含：
   - `tillering`
   - `pokou`
   - `heading`
   - `maturity`
4. `algorithm_code` 当前固定返回 `stage_prediction_algorithm`。
5. `algorithm_version` 当前建议使用语义化版本格式：`v主版本.次版本.修订号`，例如 `v2.0.0`。
6. `threshold_rule_version` 当前建议使用规则发布日期格式：`YYYY.MM`，例如 `2026.05`。
7. `threshold_rule_id` 用于稳定标识一套阈值规则；当规则内容未变化时，`threshold_rule_id` 不应变化。
8. `thermal_time_unit` 当前允许值仅为 `degree_day`。

### 6.1.1 业务阶段映射

当前已确认的业务阶段与 `docs/生育期code_list.xlsx` 原始阶段 code 映射如下：

| businessStage | rawStageCode | notes |
|---|---|---|
| `tillering` | `21` | 分蘖期 |
| `pokou` | `51` | 破口期 |
| `heading` | `58` | 齐穗期 |
| `maturity` | `89` | 成熟期 |

说明：

1. 这 4 个节点是当前病虫害调查和阶段派生必需的最小集合。
2. 如算法侧后续开始返回阶段点，允许只返回上述必要子集，不要求一次性覆盖完整生育期 code 列表。
3. 后端侧应继续以业务阶段名 `tillering / pokou / heading / maturity` 作为内部稳定口径，并在快照中保留对应 raw stage code 以便追踪。

### 6.1.2 真实生育期录入接口

后端提供计划级接口录入真实生育期，接口只生成 `ActualStageRecorded` 事件并交给 Plan Orchestrator；生育期状态更新、`StageChanged` 事件和后续日历影响仍由编排链路处理。

```http
POST /api/planting-plans/{plantingPlanId}/actual-stages
```

请求体按 `code: date` 传入：

```json
{
  "stages": {
    "21": "2026-05-12",
    "58": "2026-06-18"
  },
  "source_record_id": "manual-20260618-001",
  "operator_id": "user-7",
  "note": "田间观测记录"
}
```

说明：

1. `stages` 的 key 使用阶段 code，当前支持 `21 / 51 / 58 / 89`，后端也兼容内部业务阶段名。
2. `stages` 的 value 使用 ISO 日期 `YYYY-MM-DD`。
3. 批量传入多条记录时，后端按日期从早到晚生成事件，避免后录入的较早阶段覆盖较晚阶段。
4. 幂等维度为 `plantingPlanId + stageCode + effectiveDate + sourceRecordId`。

### 6.2 规则字段参考返回值

当前建议先冻结以下参考返回值，避免后端和算法侧各自理解：

| field | recommended value | meaning |
|---|---|---|
| `calculation_method` | `avg_temp_minus_base_capped` | 按日均温计算有效积温，并应用上下限裁剪 |
| `rounding_rule` | `keep_1_decimal_daily_keep_1_decimal_accumulated` | 日积温保留 1 位小数，累计积温每次累加后保留 1 位小数 |
| `effective_date_rule` | `threshold_reached_same_day` | 累计积温首次达到或超过阶段阈值的当天，记为新阶段开始日 |

如后续算法确实需要支持多种规则，建议先在以下参考值集合内扩展。

#### 6.2.1 `calculation_method` 参考值

1. `avg_temp_minus_base_capped`
   公式建议固定为：
   `daily_thermal_time = max(min(avg_temp, upper_temperature_cap) - base_temperature, 0)`

   说明：
   - 当 `upper_temperature_cap` 为空时，按 `avg_temp` 直接参与计算。
   - 当 `avg_temp <= lower_temperature_floor` 时，建议直接记为 `0`；若 `lower_temperature_floor` 为空，则按公式中的 `max(..., 0)` 处理。
   - 这是当前建议默认值。

2. `avg_temp_minus_base_uncapped`
   公式建议固定为：
   `daily_thermal_time = max(avg_temp - base_temperature, 0)`

   说明：
   - 不使用高温上限裁剪。
   - 仅在算法明确不需要高温截断时使用。

#### 6.2.2 `rounding_rule` 参考值

1. `keep_1_decimal_daily_keep_1_decimal_accumulated`
   说明：
   - 单日积温计算完成后保留 1 位小数。
   - 累计积温每次加总后保留 1 位小数。
   - 这是当前建议默认值。

2. `keep_2_decimal_daily_keep_2_decimal_accumulated`
   说明：
   - 单日积温计算完成后保留 2 位小数。
   - 累计积温每次加总后保留 2 位小数。

3. `keep_raw_daily_keep_1_decimal_accumulated`
   说明：
   - 单日积温内部计算不额外截断。
   - 仅累计结果在每次加总后保留 1 位小数。

#### 6.2.3 `effective_date_rule` 参考值

1. `threshold_reached_same_day`
   说明：
   - 累计积温首次达到或超过阶段阈值的当天，记为该阶段 `start_date`。
   - 这是当前建议默认值。

2. `threshold_reached_next_day`
   说明：
   - 某日累计积温首次达到或超过阶段阈值时，次日记为该阶段 `start_date`。

3. `threshold_strictly_exceeded_same_day`
   说明：
   - 只有累计积温严格大于阈值时，才记为进入新阶段。
   - 达到但不超过阈值时，仍视为前一阶段。

## 7. 响应示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "algorithm_code": "stage_prediction_algorithm",
    "algorithm_version": "v2.0.0",
    "threshold_rule": {
      "threshold_rule_id": "hn-late-rice-v2",
      "threshold_rule_version": "2026.05",
      "thermal_time_unit": "degree_day",
      "base_temperature": 10,
      "upper_temperature_cap": 30,
      "lower_temperature_floor": 10,
      "calculation_method": "avg_temp_minus_base_capped",
      "rounding_rule": "keep_1_decimal_daily_keep_1_decimal_accumulated",
      "effective_date_rule": "threshold_reached_same_day",
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

## 8. 后端派生规则

算法接口不再直接返回 `stage_timeline` 后，后端按以下规则派生：

1. 后端根据逐日天气和 `threshold_rule` 计算日积温与累计积温。
2. 累计积温首次跨过某阶段阈值的日期，即该阶段的 `start_date`。
3. 后端根据 `effective_date_rule` 判断“跨阈值当天”还是“次日”进入新阶段。
4. `CropThermalTimeState` 保存累计积温、单位、基础温度、最后计算日期和天气版本。
5. `CropStageState` 保存当前阶段及生效日期。
6. `StagePredictionSnapshot.stage_timeline` 当前由后端派生，并至少保留业务阶段名；如后续算法侧同步返回原始阶段点，快照中应同时保留 raw stage code。
7. 病虫害调查窗口仍直接消费后端推导出的：
   - `tillering_date`
   - `pokou_date`
   - `heading_date`
   - `maturity_date`

## 9. 异常返回

| code | meaning | retryable | fallbackAction | notes |
|---|---|---|---|---|
| `400` | 请求字段缺失或格式非法 | 否 | 修正请求字段后重试 | 至少返回缺失字段名 |
| `422` | 算法无法根据当前作物 / 品种 / 区域匹配规则 | 否 | 记录失败事件，人工排查 | 用于业务上无可计算规则 |
| `500` | 算法内部异常 | 是 | 后端记录失败事件并按 job 重试策略处理 | 建议返回 trace id |
| `504` | 超时 | 是 | 后端记录失败事件并稍后重试 | 当前后端默认按同步失败处理 |

## 10. 当前版约束

1. 当前版由后端统一取天气，算法接口不自行拉外部气象数据。
2. 当前版算法不要求返回完整 `stage_timeline`；如返回阶段点，也只要求返回当前业务必需的部分节点。
3. 当前版规则包必须足够让后端独立完成积温累计和生育期推进。
4. 当前确认的关键原始阶段 code 为 `21 / 51 / 58 / 89`，分别对应 `tillering / pokou / heading / maturity`。
5. 如后续需要新增特殊修正规则或更多阶段点，优先通过追加字段扩展，不直接改变现有字段语义。
6. 病虫害调查依赖 `tillering`、`pokou`、`heading`、`maturity` 四个阶段节点；若规则无法推导这些节点，后端会判为不可消费。

## 11. 输入边界说明

1. 当前契约不向算法接口暴露 `planting_plan_id`、`plan_code` 等系统内部业务标识。
2. 当前契约不默认传 `expected_harvest_date`、`previous_harvest_date`、`ratoon_first_season_harvest_date`；如后续再生稻规则匹配确实需要，再按算法需求单独补充。
3. 算法接口输入只保留参与区域阈值匹配所需的农艺字段和地点字段。
4. 计划维度的追踪、幂等、日志关联由 CropFlow 后端在调用侧和快照落库侧自己处理，不进入算法 contract。
