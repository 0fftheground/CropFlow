# 调查窗口接口文档

## 1. 文档说明

本文档描述调查窗口相关生产接口，接口接收外部数据并返回调查窗口结果。

接口约束：

- 不读写调查事件表。
- 不包含 `reference_*`、`db_config`、`current_date` 等测试或内部参数。
- 外部数据由调用方作为接口入参传入。
- 当前日期由接口内部取 `now`，调用方不传日期。
- 日期字段除特别说明外，统一使用 `YYYYMMDD`。

## 2. 病虫常规调查初始化接口

### 2.1 接口信息

- 请求方法：`POST`
- 接口路径：`/pestDisease/survey/init-regular-survey`
- 接口用途：接收种植计划信息和病虫全年一级理论防治日期，返回当前种植季全部常规调查计划。

### 2.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `cultivation_type` | string | 是 | 种植制度，例如 `早稻`、`中稻`、`晚稻`、`再生稻`。 |
| `growth_stage` | object | 是 | 生育期信息。 |
| `level1_of_year` | object | 是 | 病虫全年一级理论防治日期。 |

#### `growth_stage`

只传本接口要求的时期。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `tillering_date` | string | 是 | 分蘖期，格式 `YYYY-MM-DD`。 |
| `pokou_date` | string | 是 | 破口期，格式 `YYYY-MM-DD`。 |
| `heading_date` | string | 是 | 齐穗期，格式 `YYYY-MM-DD`。 |
| `maturity_date` | string | 是 | 成熟期，格式 `YYYY-MM-DD`。 |

#### `level1_of_year`

病虫全年一级理论防治日期明细，键为次序，值为 `[MMDD, MMDD]`。

### 2.3 请求示例

```json
{
  "cultivation_type": "早稻",
  "growth_stage": {
    "tillering_date": "2026-04-20",
    "pokou_date": "2026-06-10",
    "heading_date": "2026-06-18",
    "maturity_date": "2026-07-20"
  },
  "level1_of_year": {
    "1": ["0509", "0513"],
    "2": ["0607", "0611"]
  }
}
```

### 2.4 响应参数

接口统一返回 `code/msg/data`，以下业务字段位于 `data` 内。顶层 `msg` 按 `data.count` 生成，格式为 `已生成{count}个常规调查任务`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `count` | integer | 常规调查计划数量。 |
| `regular_plans` | array | 常规调查计划列表。每日更新接口需要传回该字段。 |

#### `regular_plans[]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | 调查状态，常见值为 `need_survey`。 |
| `调查日期` | array | 调查日期窗口，格式 `[YYYYMMDD, YYYYMMDD]`。 |
| `spray_stage` | string | 本次调查对应的打药阶段，取值为 `封行药`、`破口药`、`齐穗药` 或 `常规病虫预防`。 |
| `survey_method` | string | 调查日期来源，取值为 `一级理论防治日期` 或 `生育期`。 |
| `调查对象` | array | 本次调查涉及的病虫害。 |
| `排除原因` | object | 未纳入调查对象的原因。 |
| `msg` | string | 结果说明。 |

`spray_stage` 根据本次实际防治窗口 `[effective_start_dt, effective_end_dt]` 与生育期节点窗口重叠关系确定：

- 早稻：`封行 = tillering_date + 12 天`，节点判断窗口为节点前 7 天至节点后 7 天。
- 非早稻：`封行 = tillering_date + 9 天`，节点判断窗口为节点前 10 天至节点后 10 天。
- `破口 = pokou_date`，`齐穗 = heading_date`。
- 命中破口期调整规则时优先返回 `破口药`；否则按 `封行药`、`破口药`、`齐穗药` 顺序判断；均不命中时返回 `常规病虫预防`。

`survey_method` 根据调查日期来源确定：按一级理论防治日期倒推时为 `一级理论防治日期`；因破口期规则按生育期调整时为 `生育期`。

### 2.5 响应示例

```json
{
  "code": 200,
  "msg": "已生成2个常规调查任务",
  "data": {
    "count": 2,
    "regular_plans": [
      {
        "status": "need_survey",
        "调查日期": ["20260502", "20260504"],
        "spray_stage": "封行药",
        "survey_method": "一级理论防治日期",
        "调查对象": ["二化螟", "稻纵卷叶螟", "稻飞虱", "稻瘟病", "纹枯病"],
        "排除原因": {
          "稻曲病": "当前一级理论防治日期不在目标防治范围内"
        },
        "msg": "当前处于可防治周期，建议按调查日期开展调查"
      }
    ]
  }
}
```

## 3. 病虫调查事件每日更新接口

### 3.1 接口信息

- 请求方法：`POST`
- 接口路径：`/pestDisease/survey/daily-update-survey`
- 接口用途：接收常规调查初始化结果、逐日天气和台风数据，返回当天调查事件。

### 3.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `growth_stage` | object | 是 | 生育期信息，字段同常规调查初始化接口。 |
| `regular_plans` | array | 是 | 常规调查初始化接口返回的 `regular_plans`。 |
| `weather_data` | array | 是 | 逐日天气数据，至少覆盖当前日期前 8 天至当前日期后 7 天。 |
| `typhoon_data` | object | 是 | 未来 72 小时台风相关预警和逐小时天气数据。 |
| `actual_control_date` | string | 否 | 上次打药实际日期，格式 `YYYYMMDD`，仅用于合并判断。 |

不输入以下字段：

- `current_date`
- `reference_date`
- `typhoon_affected_72h`
- `db_config`
- `farm_id`
- `farm_name`
- `adcode`
- `location`

### 3.3 `weather_data`

`weather_data` 用于提供逐日天气数据，建议至少覆盖当前日期前 8 天至当前日期后 7 天。接口内部当前日期由服务端 `now` 获取，调用方不传 `current_date`。

该时间范围用于覆盖降温回看、未来触发候选和连续不良天气判断；传入范围不足时，接口不会因日期范围本身报错，但可能导致临时调查触发判断不完整。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `DATE` | string | 是 | 日期，格式 `YYYYMMDD`。 |
| `TMAX` | number | 是 | 最高气温，单位摄氏度。 |
| `RAIN` | number | 是 | 降雨量，单位毫米。 |
| `SUN` | number | 是 | 日照时数，单位小时。 |

### 3.4 `typhoon_data`

`typhoon_data` 用于提供未来 72 小时台风相关预警和逐小时天气数据。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `alerts` | array | 是 | 台风、热带低压、台风外围、外围环流等相关预警列表。 |
| `hourly_weather_72h` | array | 是 | 未来 72 小时逐小时天气。 |

#### `typhoon_data.alerts[]`

`alerts[]` 为服务层按目标地块省份匹配范围过滤并精简后的台风相关预警。服务层传入算法前需要先过滤：

- 过滤 `msgType = "解除"` 的预警。
- 过滤 `msgTypeCode = "Cancel"` 的预警。
- 过滤非台风相关 `eventType`。
- 只保留目标地块所属省份对应范围内的台风相关预警，省份匹配范围见“3.5 台风数据范围”。

台风相关 `eventType` 关键词包括：`台风`、`热带风暴`、`强热带风暴`、`超强台风`、`热带低压`、`台风外围`、`外围环流`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `eventType` | string | 是 | 台风相关预警类型，例如 `台风预警`、`热带低压预警`。 |
| `effective` | string | 是 | 预警生效时间，支持 `YYYYMMDDHHmmss` 或 `YYYY-MM-DD HH:mm:ss`。 |

#### `typhoon_data.hourly_weather_72h[]`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `datetime` | string | 是 | 小时时间。 |
| `pre` | number | 是 | 小时降水量，单位毫米。 |
| `wins` | number | 是 | 平均风速。 |
| `gust` | number | 否 | 阵风风速。 |
| `wp` | string | 否 | 天气现象文本，例如 `阵雨`。 |

### 3.5 台风数据范围

台风判断不依赖农场坐标，接口也不再接收 `farm_info`。调用方需要根据目标地块所属省份，传入对应省份匹配范围内的台风相关预警；接口默认 `typhoon_data.alerts` 已完成该范围过滤。

湖南省农场：

- 需传入湖南、广东、广西相关台风/热带低压预警
- 湖南省前缀：`43`
- 广东省前缀：`44`
- 广西壮族自治区前缀：`45`

安徽省农场：

- 需传入安徽、浙江、福建、上海、江苏相关台风/热带低压预警
- 安徽省前缀：`34`
- 浙江省前缀：`33`
- 福建省前缀：`35`
- 上海市前缀：`31`
- 江苏省前缀：`32`

### 3.6 请求示例

```json
{
  "growth_stage": {
    "tillering_date": "2026-04-20",
    "pokou_date": "2026-06-10",
    "heading_date": "2026-06-18",
    "maturity_date": "2026-07-20"
  },
  "regular_plans": [
    {
      "status": "need_survey",
      "调查日期": ["20260502", "20260504"],
      "spray_stage": "封行药",
      "survey_method": "一级理论防治日期",
      "调查对象": ["二化螟", "稻纵卷叶螟"],
      "排除原因": {},
      "msg": "当前处于可防治周期，建议按调查日期开展调查"
    }
  ],
  "weather_data": [
    {
      "DATE": "20260701",
      "RAIN": 1.2,
      "TMAX": 30.2,
      "SUN": 2.5
    }
  ],
  "typhoon_data": {
    "alerts": [
      {
        "eventType": "台风预警",
        "effective": "20260701080000"
      }
    ],
    "hourly_weather_72h": [
      {
        "datetime": "2026-07-01 09:00:00",
        "pre": 1.2,
        "wins": 6.1,
        "gust": 9.0,
        "wp": "阵雨"
      }
    ]
  },
  "actual_control_date": "20260705"
}
```

### 3.7 响应参数

接口统一返回 `code/msg/data`，以下业务字段位于 `data` 内。顶层 `msg` 取 `data.msg`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | 每日更新结果状态。 |
| `msg` | string | 结果说明。 |
| `survey_window` | array | 输出调查窗口，格式 `[YYYYMMDD, YYYYMMDD]`。 |
| `spray_stage` | string | 输出调查对应的打药阶段；突发调查为 `突发病虫防治`。 |
| `targets` | array | 调查对象。 |
| `exclude_reasons` | object | 排除原因。 |
| `source` | string | 输出来源，常见值为 `merge`、`emergency`、`none`。 |
| `raw_result` | object | 原始计算结果，便于追溯。 |

#### `status`

| 值 | 说明 |
| --- | --- |
| `merged_into_regular` | 突发调查已合并到常规调查。 |
| `new_emergency` | 存在新增突发调查任务。 |
| `no_new_event` | 当天无新增调查事件。 |

### 3.8 响应示例

```json
{
  "code": 200,
  "msg": "已识别到临时调查触发条件，建议开展临时调查",
  "data": {
    "status": "new_emergency",
    "msg": "已识别到临时调查触发条件，建议开展临时调查",
    "survey_window": ["20260703", "20260704"],
    "spray_stage": "突发病虫防治",
    "targets": ["稻飞虱", "纹枯病"],
    "exclude_reasons": {
      "稻曲病": "当前调查窗口不在目标防治范围内"
    },
    "source": "emergency",
    "raw_result": {
      "regular": {
        "status": "need_survey",
        "调查日期": ["20260502", "20260504"],
        "spray_stage": "封行药",
        "survey_method": "一级理论防治日期",
        "调查对象": ["二化螟", "稻纵卷叶螟"],
        "排除原因": {},
        "msg": "当前处于可防治周期，建议按调查日期开展调查"
      },
      "emergency": {
        "status": "need_survey",
        "调查日期": ["20260703", "20260704"],
        "spray_stage": "突发病虫防治",
        "调查对象": ["稻飞虱", "纹枯病"],
        "排除原因": {
          "稻曲病": "当前调查窗口不在目标防治范围内"
        },
        "msg": "已识别到临时调查触发条件，建议开展临时调查"
      },
      "merge": {
        "can_merge": false,
        "status": "not_merged",
        "reason": "常规调查与突发调查不满足合并条件",
        "matched_rule": null,
        "merged_into": null,
        "final_survey_window": [],
        "actual_control_date": "20260705"
      }
    }
  }
}
```

## 4. 调用方职责

- 调用方负责获取并传入所有外部数据。
- 调用方负责保存常规调查初始化接口输出的 `regular_plans`，并在每日更新时传回。
- 接口不访问数据库、不请求气象接口。
- 气象数据由 `weather_data` 和 `typhoon_data.hourly_weather_72h` 直接传入，农场坐标不作为生产接口入参。
