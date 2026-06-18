# 防治窗口接口文档

## 1. 文档说明

本文档描述防治窗口相关生产接口，接口接收业务入参并返回计算结果。

接口约束：

- 不访问数据库。
- 不请求种植计划详情接口。
- 不请求生育期预测接口。
- 不调用打药适宜度外部接口；需要气象调整或合并的接口由调用方传入 `spray_suitability_data`。
- 外部数据由调用方作为接口入参传入。
- 日期字段除特别说明外，统一使用 `YYYYMMDD`。

## 2. 病虫理论防治方案接口

### 2.1 接口信息

- 请求方法：`POST`
- 接口路径：`/pestDisease/control/generate-theory-control-plan`
- 接口用途：只计算理论防治窗口、防治对象和防治方案，不做打药适宜度校正。

该接口不接收 `spray_suitability_data`，不返回 `final_window`、`suitability_dates`、`weather_adjust`、`spray_suitability_required_range`。

### 2.2 请求参数

请求字段如下；该接口不接收 `spray_suitability_data`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `control_type` | string | 是 | 推荐类型。`regular` 表示常规防治，`emergency` 表示突发病虫防治。 |
| `province` | string | 是 | 省份名称或省份编码，用于查询防治方案库。 |
| `plant_info` | object | 是 | 种植信息，包含年份、稻作类型、栽培方式和基础生育期节点。 |
| `survey_data` | object | 是 | 当前调查数据，包含调查日期、生育期编码和各病虫调查指标。 |
| `spray_info` | object | 条件必填 | 当前打药信息。`control_type=regular` 时必填。 |
| `spray_info_list` | array | 条件必填 | 历史打药信息列表。`control_type=emergency` 时必填。 |
| `level1_window` | array | 条件必填 | 一级理论防治日期，格式 `[MMDD, MMDD]`。`control_type=regular` 时必填。 |
| `herb_control_date` | array | 否 | 除草剂使用日期窗口，格式 `[YYYYMMDD, YYYYMMDD]`。 |
| `harvest_date` | string | 否 | 计划收割日期，格式 `YYYYMMDD`。 |

#### `plant_info`

`plant_info` 只需要传算法使用的种植信息，不需要传完整种植计划，也不会通过 `plant_id` 查询数据库。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `year` | string/integer | 是 | 种植年份，用于查询防治方案库。 |
| `cultivation_system` | string | 是 | 稻作类型，例如 `早稻`、`中稻`、`一季晚稻`、`晚稻`、`再生稻`。 |
| `cultivation_pattern` | string | 是 | 栽培方式，例如 `直播`、`抛秧`、`插秧`。 |
| `growth_stage` | object | 是 | 基础生育期节点，字段见下表。 |

`growth_stage` 字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `tillering_date` | string | 是 | 分蘖期日期，格式 `YYYY-MM-DD`。 |
| `pokou_date` | string | 是 | 破口期日期，格式 `YYYY-MM-DD`。 |
| `heading_date` | string | 是 | 齐穗期日期，格式 `YYYY-MM-DD`。 |

#### `survey_data`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `survey_date` | string | 是 | 调查日期，格式 `YYYYMMDD`。 |
| `survey_method` | string | 否 | 调查方法。仅常规防治且 `spray_info.stage="破口药"` 时建议传入；不传默认按 `一级理论防治日期`。 |
| `bbch_stage` | integer | 是 | 当前 BBCH 生育期编码。 |
| `ErHuaMing` | object | 是 | 二化螟调查数据，字段见“病虫调查字段”。 |
| `DaoFeiShi` | object | 是 | 稻飞虱调查数据，字段见“病虫调查字段”。 |
| `DaoWenBing` | object | 是 | 稻瘟病调查数据，字段见“病虫调查字段”。 |
| `WenKuBing` | object | 是 | 纹枯病调查数据，字段见“病虫调查字段”。 |
| `DaoZongJuanYeMing` | object | 是 | 稻纵卷叶螟调查数据，字段见“病虫调查字段”。 |

`survey_method` 仅支持 `一级理论防治日期`、`生育期`。非破口药场景可不传。

病虫调查字段：

| 对象 | 字段 | 类型 | 取值/单位 | 说明                   |
| --- | --- | --- | --- |----------------------|
| `ErHuaMing` | `dead_sheath_rate` | number | `0~1` | 枯鞘率。                 |
| `ErHuaMing` | `dead_heart_rate` | number | `0~1` | 枯心率。                 |
| `ErHuaMing` | `main_larval_instars` | integer | `0~6` | 主要虫龄，`0` 表示未发现或无主要虫龄。 |
| `ErHuaMing` | `damaged_plant_rate` | number | `0~1` | 虫伤株率。                |
| `DaoFeiShi` | `insects_per_100_hills` | number | `>=0` | 百丛虫量。                |
| `DaoWenBing` | `acute_lesion` | boolean | `true/false` | 是否发现急性病斑。            |
| `DaoWenBing` | `diseased_leaf_rate` | number | `0~1` | 病叶率。                 |
| `WenKuBing` | `lesion_on_upper_leaf_sheath` | boolean | `true/false` | 倒 2 叶鞘及以上是否发现病斑。     |
| `WenKuBing` | `diseased_hill_rate` | number | `0~1` | 病丛率。                 |
| `DaoZongJuanYeMing` | `rolled_leaf_tips_per_100_hills` | number | `>=0` | 百丛束尖数。               |
| `DaoZongJuanYeMing` | `larvae_count` | number | `>=0` | 幼虫数量。                |
| `DaoZongJuanYeMing` | `moths_per_square_meter` | number | `>=0` | 每平方米蛾量。              |

病虫调查字段缺失或为空时按 `0` 或 `false` 处理；为保证诊断准确性，建议完整传入实际调查数据。

#### `spray_info`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `stage` | string | 是 | 当前打药阶段，例如 `封行药`、`破口药`、`齐穗药`、`常规病虫预防`、`突发病虫防治`。 |
| `round` | integer | 否 | 当前打药轮次。算法不依赖该字段，调用方可用于业务追溯。 |

#### `spray_info_list[]`

`spray_info_list` 仅 `control_type=emergency` 时必填，每项至少包含：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `stage` | string | 是 | 历史打药阶段。 |

### 2.3 请求示例

```json
{
  "control_type": "regular",
  "province": "湖南省",
  "plant_info": {
    "year": "2026",
    "cultivation_system": "早稻",
    "cultivation_pattern": "直播",
    "growth_stage": {
      "tillering_date": "2026-05-18",
      "pokou_date": "2026-06-20",
      "heading_date": "2026-06-27"
    }
  },
  "survey_data": {
    "survey_date": "20260628",
    "survey_method": "一级理论防治日期",
    "bbch_stage": 23,
    "ErHuaMing": {
      "dead_sheath_rate": 0,
      "dead_heart_rate": 0,
      "main_larval_instars": 0,
      "damaged_plant_rate": 0
    },
    "DaoZongJuanYeMing": {
      "rolled_leaf_tips_per_100_hills": 20,
      "larvae_count": 0,
      "moths_per_square_meter": 0
    },
    "DaoFeiShi": {
      "insects_per_100_hills": 0
    },
    "DaoWenBing": {
      "acute_lesion": false,
      "diseased_leaf_rate": 0
    },
    "WenKuBing": {
      "lesion_on_upper_leaf_sheath": false,
      "diseased_hill_rate": 0
    }
  },
  "spray_info": {
    "round": 1,
    "stage": "封行药"
  },
  "level1_window": ["0702", "0706"],
  "herb_control_date": ["20260625", "20260628"]
}
```

### 2.4 响应参数

接口统一返回 `code/msg/data`，以下业务字段位于 `data` 内。顶层 `msg` 取 `data.control_mode`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `control_type` | string | 推荐类型，取值同请求入参。 |
| `control_mode` | string | 理论推荐模式，例如 `单次防治`、`连续防治`、`需要防治`。 |
| `status` | string/null | 理论推荐状态，例如 `0~2d`、`1~3d`、`normal`。 |
| `rounds` | array | 理论防治轮次列表。无需防治时为空数组。 |
| `flags` | object | 辅助标记。 |

#### `rounds[]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `round` | integer | 防治轮次。 |
| `theory_window` | array | 理论防治窗口，格式 `[start_date, end_date]`。 |
| `targets` | object | 当前轮次防治对象。 |
| `prescription` | object | 当前轮次防治方案。 |

### 2.5 响应示例

```json
{
  "code": 200,
  "msg": "单次防治",
  "data": {
    "control_type": "regular",
    "control_mode": "单次防治",
    "status": "1~3d",
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260701", "20260703"],
        "targets": {
          "二化螟": "防治",
          "稻飞虱": "防治",
          "稻瘟病": "防治",
          "纹枯病": "防治",
          "稻纵卷叶螟": "防治"
        },
        "prescription": {
          "chemicals": [],
          "water_volume": "3 L/亩"
        }
      }
    ],
    "flags": {
      "advanced": true,
      "over_threshold_targets": ["稻纵卷叶螟"]
    }
  }
}
```

## 3. 病虫防治窗口气象调整接口

### 3.1 接口信息

- 请求方法：`POST`
- 接口路径：`/pestDisease/control/adjust-control-window`
- 接口用途：接收理论防治方案和该理论方案要求范围内的打药适宜度数据，只做气象适宜度调整，返回最终实际防治时间。

该接口不重新计算理论防治方案，不返回 `spray_suitability_required_range`，也不返回 `prescription`；防治方案以理论防治接口返回为准。

### 3.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `control_type` | string | 是 | 推荐类型。`regular` 表示常规防治，`emergency` 表示突发病虫防治。 |
| `theory_plan` | object | 是 | `/pestDisease/control/generate-theory-control-plan` 返回的理论防治结果，传 `data` 部分即可；接口也兼容传完整 `code/msg/data` 响应对象。 |
| `spray_suitability_data` | array | 是 | 打药适宜度逐日数据，元素包含 `date` 和 `dy_ws`。审核后建议按保守取数范围传入；接口只在算法实际检索范围内筛选。 |
| `plant_info` | object | 是 | 种植信息。用于统一审核后任务结构；突发防治会使用其中的齐穗日期并推导灌浆日期来裁剪实际检索范围。 |

#### `theory_plan`

`theory_plan` 可直接传理论防治接口返回的 `data`，也兼容传完整 `code/msg/data` 响应对象；如果传完整响应对象，接口会读取其中的 `data`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `control_type` | string | 是 | 推荐类型，取值同请求入参。 |
| `control_mode` | string | 是 | 理论推荐模式，例如 `单次防治`、`连续防治`、`需要防治`。 |
| `status` | string/null | 否 | 理论推荐状态。 |
| `rounds` | array | 是 | 理论防治轮次列表，字段见下方 `theory_plan.rounds[]`。 |
| `flags` | object | 否 | 辅助标记。 |

`theory_plan.rounds[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `round` | integer | 否 | 防治轮次；不传时按数组顺序从 1 开始。 |
| `theory_window` | array | 是 | 理论防治窗口，格式 `[start_date, end_date]`，日期为 `YYYYMMDD`。 |
| `targets` | object | 是 | 当前轮次防治对象。突发防治会根据是否包含 `纹枯病` 判断气象检索上限；该字段不用于返回防治方案。 |

`plant_info` 结构同理论防治接口中的 `plant_info`，其中 `growth_stage.heading_date` 为齐穗日期；算法内部按 `heading_date + 7 天` 推导灌浆日期。

审核后 `spray_suitability_data` 建议保守取数范围：

- 单轮次：覆盖 `theory_window[0] - 3 天` 到 `theory_window[1] + 30 天`。
- 多轮次：覆盖所有轮次最早 `theory_window[0] - 3 天` 到所有轮次最晚 `theory_window[1] + 30 天`。
- 这是调用方获取气象数据的保守范围，不是算法实际筛选范围。

算法内部实际检索范围：

- `control_type=regular`：先查理论窗口，再查前 3 天，再查后 15 天；均无适宜或较适宜日期时取消防治。
- `control_type=emergency`：先查理论窗口，再查 `theory_window[1] + 1 天` 到 `theory_window[1] + 10 天`；传入 `plant_info` 时，包含 `纹枯病` 的突发防治最多检索到 `灌浆`，其他突发防治最多检索到 `齐穗`，但不会早于理论窗口结束日。
- `plant_info.growth_stage.heading_date` 为齐穗日期，算法内部灌浆日期按 `heading_date + 7 天` 推导，不需要额外传 `grain_filling_date`。
- 调用方传入超出实际检索范围的气象数据不会扩大最终推荐范围。

### 3.3 请求示例

```json
{
  "control_type": "regular",
  "theory_plan": {
    "control_type": "regular",
    "control_mode": "单次防治",
    "status": "1~3d",
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260701", "20260703"],
        "targets": {
          "二化螟": "防治",
          "稻飞虱": "防治"
        }
      }
    ]
  },
  "plant_info": {
    "year": "2026",
    "cultivation_system": "早稻",
    "cultivation_pattern": "直播",
    "growth_stage": {
      "tillering_date": "2026-05-18",
      "pokou_date": "2026-06-20",
      "heading_date": "2026-06-27"
    }
  },
  "spray_suitability_data": [
    {"date": "20260628", "dy_ws": 0},
    {"date": "20260629", "dy_ws": 0},
    {"date": "20260630", "dy_ws": 0.6},
    {"date": "20260701", "dy_ws": 0},
    {"date": "20260702", "dy_ws": 1},
    {"date": "20260703", "dy_ws": 0},
    {"date": "20260704", "dy_ws": 0},
    {"date": "20260705", "dy_ws": 0},
    {"date": "20260706", "dy_ws": 0},
    {"date": "20260707", "dy_ws": 0},
    {"date": "20260708", "dy_ws": 0},
    {"date": "20260709", "dy_ws": 0},
    {"date": "20260710", "dy_ws": 0},
    {"date": "20260711", "dy_ws": 0},
    {"date": "20260712", "dy_ws": 0},
    {"date": "20260713", "dy_ws": 0},
    {"date": "20260714", "dy_ws": 0},
    {"date": "20260715", "dy_ws": 0},
    {"date": "20260716", "dy_ws": 0},
    {"date": "20260717", "dy_ws": 0},
    {"date": "20260718", "dy_ws": 0}
  ]
}
```

### 3.4 响应参数

接口统一返回 `code/msg/data`，以下业务字段位于 `data` 内。顶层 `msg` 取 `data.control_mode`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `control_type` | string | 推荐类型，取值同请求入参。 |
| `control_mode` | string | 理论推荐模式，例如 `单次防治`、`连续防治`、`需要防治`。 |
| `status` | string/null | 最终状态。气象调整导致无可用日期时为 `取消防治`。 |
| `rounds` | array | 最终防治轮次列表。无需防治或取消防治时为空数组。 |
| `weather_adjust` | object | 气象适宜度调整说明。 |

#### `rounds[]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `round` | integer | 防治轮次。 |
| `theory_window` | array | 理论防治窗口，格式 `[start_date, end_date]`。 |
| `final_window` | array | 气象调整后的最终实际防治日期。 |
| `targets` | object | 当前轮次防治对象。 |
| `suitability_dates` | object | 命中的适宜日期，包含 `standard` 和 `moderate`。 |
| `weather_adjust_reason` | string | 当前轮次气象调整原因。 |

`weather_adjust` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `adjusted` | boolean | 是否产生气象适宜度调整结果。 |
| `reason` | string/null | 总体调整说明。 |
| `round_reasons` | array | 各轮次调整说明。 |

### 3.5 响应示例

```json
{
  "code": 200,
  "msg": "单次防治",
  "data": {
    "control_type": "regular",
    "control_mode": "单次防治",
    "status": "1~3d",
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260701", "20260703"],
        "final_window": ["20260702"],
        "targets": {
          "二化螟": "防治",
          "稻飞虱": "防治"
        },
        "suitability_dates": {
          "standard": ["20260702"],
          "moderate": []
        },
        "weather_adjust_reason": "理论防治时机中存在标准适宜打药日期"
      }
    ],
    "weather_adjust": {
      "adjusted": true,
      "reason": "第1次防治：理论防治时机中存在标准适宜打药日期",
      "round_reasons": [
        {
          "round": 1,
          "reason": "理论防治时机中存在标准适宜打药日期"
        }
      ]
    }
  }
}
```

## 4. 常规+突发合并取数范围提示接口

### 4.1 接口信息

- 请求方法：`POST`
- 接口路径：`/pestDisease/control/get-merge-spray-suitability-range`
- 接口用途：在常规理论防治和突发理论防治同时存在时，计算调用合并接口前需要获取的打药适宜度数据总日期范围。

该接口不接收 `spray_suitability_data`，不做合并、不做气象筛选，只返回常规和突发合并场景所需的取数范围。单类型防治不调用该接口，调用方按调整接口的算法检索范围规则准备 `spray_suitability_data`。
[..](..%2F..%2F..)
### 4.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `regular_theory` | object | 是 | 常规理论防治结果，使用 `rounds[].theory_window` 和 `rounds[].targets`。`rounds` 至少 1 条。 |
| `emergency_theory` | object | 是 | 突发理论防治结果，使用 `rounds[].theory_window` 和 `rounds[].targets`。`rounds` 必须且只能 1 条。 |
| `extend_days` | integer | 否 | 合并接口使用的扩展参数，默认 `10`。 |
| `plant_info` | object | 否 | 种植信息。传入后用于计算突发防治相关日期范围。 |

`regular_theory` 和 `emergency_theory` 均为理论防治结果对象，至少包含 `rounds` 字段；`rounds[]` 使用理论防治窗口 `theory_window`，不是气象适宜度调整后的 `final_window`。

`rounds[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `round` | integer | 是 | 防治轮次。 |
| `theory_window` | array | 是 | 理论防治窗口，格式 `[start_date, end_date]`，日期为 `YYYYMMDD`。 |
| `targets` | object | 是 | 防治对象，key 为病虫名称，value 为 `防治` 或 `兼防`。 |

`plant_info` 结构同理论防治接口中的 `plant_info`。

### 4.3 请求示例

```json
{
  "regular_theory": {
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260812", "20260816"],
        "targets": {
          "二化螟": "防治"
        }
      },
      {
        "round": 2,
        "theory_window": ["20260822", "20260824"],
        "targets": {
          "稻飞虱": "防治"
        }
      }
    ]
  },
  "emergency_theory": {
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260810", "20260812"],
        "targets": {
          "稻瘟病": "防治"
        }
      }
    ]
  },
  "extend_days": 10,
  "plant_info": {
    "year": "2026",
    "cultivation_system": "中稻",
    "cultivation_pattern": "直播",
    "growth_stage": {
      "tillering_date": "2026-06-15",
      "pokou_date": "2026-08-15",
      "heading_date": "2026-08-22"
    }
  }
}
```

### 4.4 响应示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "spray_suitability_required_range": ["20260809", "20261013"]
  }
}
```

调用顺序：分别生成常规/突发理论结果 -> 调用本接口获取 `spray_suitability_required_range` -> 后端按该范围获取 `spray_suitability_data` -> 调用 `/pestDisease/control/merge-control-plan`。

## 5. 病虫常规防治与突发防治时间合并判断接口

### 5.1 接口信息

- 请求方法：`POST`
- 接口路径：`/pestDisease/control/merge-control-plan`
- 接口用途：接收常规和突发理论防治事件及打药适宜度数据，返回合并后的最终打药安排。

### 5.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `spray_suitability_data` | array | 是 | 打药适宜度逐日数据，元素包含 `date` 和 `dy_ws`。 |
| `regular_theory` | object | 是 | 常规理论防治事件。`rounds` 可包含多条未执行常规防治事件。 |
| `emergency_theory` | object | 是 | 突发理论防治事件。`rounds` 最多只能包含 1 条。 |
| `min_gap_days` | integer | 否 | 两次打药最小间隔天数，默认 `7`。 |
| `merge_gap_days` | integer | 否 | 常规与突发窗口相邻多少天内合并，默认 `3`。 |
| `extend_days` | integer | 否 | 合并接口使用的扩展参数，默认 `10`。 |
| `plant_info` | object | 条件必填 | 突发防治相关日期计算所需的种植信息，结构同理论接口的 `plant_info`。 |

`regular_theory.rounds[]` 和 `emergency_theory.rounds[]` 均使用理论防治窗口 `theory_window`，不是已经经过气象适宜度调整的 `final_window`。接口根据传入的理论事件和打药适宜度数据返回合并后的最终打药安排。

`rounds[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `round` | integer | 是 | 防治轮次。 |
| `theory_window` | array | 是 | 理论防治窗口，格式 `[start_date, end_date]`，日期为 `YYYYMMDD`。 |
| `targets` | object | 是 | 防治对象，key 为病虫名称，value 为 `防治` 或 `兼防`，例如 `{"二化螟": "防治", "稻飞虱": "兼防"}`。 |
| `prescription` | object | 否 | 当前理论轮次防治方案。合并接口会随最终事件透传；若事件被合并，会合并两个事件的处方并去重。 |

`regular_theory` 和 `emergency_theory` 的顶层结构均为：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `rounds` | array | 是 | 理论防治事件列表；`regular_theory.rounds` 可多条，`emergency_theory.rounds` 最多 1 条。 |

`plant_info` 结构同理论防治接口中的 `plant_info`。

### 5.3 请求示例

```json
{
  "regular_theory": {
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260812", "20260816"],
        "targets": {
          "二化螟": "防治"
        },
        "prescription": {
          "chemicals": [],
          "water_volume": "3 L/亩"
        }
      },
      {
        "round": 2,
        "theory_window": ["20260822", "20260824"],
        "targets": {
          "稻飞虱": "防治"
        }
      }
    ]
  },
  "emergency_theory": {
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260810", "20260812"],
        "targets": {
          "稻瘟病": "防治"
        },
        "prescription": {
          "chemicals": [],
          "water_volume": "3 L/亩"
        }
      }
    ]
  },
  "min_gap_days": 7,
  "merge_gap_days": 3,
  "extend_days": 10,
  "spray_suitability_data": [
    {"date": "20260810", "dy_ws": 1},
    {"date": "20260811", "dy_ws": 0},
    {"date": "20260812", "dy_ws": 1},
    {"date": "20260813", "dy_ws": 0.6},
    {"date": "20260814", "dy_ws": 0},
    {"date": "20260815", "dy_ws": 0},
    {"date": "20260816", "dy_ws": 0},
    {"date": "20260822", "dy_ws": 0.7},
    {"date": "20260823", "dy_ws": 0},
    {"date": "20260824", "dy_ws": 0}
  ],
  "plant_info": {
    "year": "2026",
    "cultivation_system": "中稻",
    "cultivation_pattern": "直播",
    "growth_stage": {
      "tillering_date": "2026-06-15",
      "pokou_date": "2026-08-15",
      "heading_date": "2026-08-22"
    }
  }
}
```

### 5.4 响应示例

接口统一返回 `code/msg/data`。顶层 `msg` 取业务 `message`，`data` 内不返回 `message`。

```json
{
  "code": 200,
  "msg": "常规防治与突发防治时间邻近，已合并为一次打药安排；理论防治时机中存在标准适宜打药日期",
  "data": {
    "merged": true,
    "events": [
      {
        "type": "merged",
        "round": 1,
        "theory_window": ["20260812", "20260812"],
        "final_window": ["20260812"],
        "targets": {
          "二化螟": "防治",
          "稻瘟病": "防治"
        },
        "prescription": {
          "chemicals": [],
          "water_volume": "3 L/亩"
        },
        "suitability_dates": {
          "standard": ["20260812"],
          "moderate": []
        }
      }
    ]
  }
}
```

## 6. 外部数据职责

调用方负责获取并传入以下外部数据：

- 通过业务系统获取目标地块的打药适宜度逐日数据，并作为 `spray_suitability_data` 传入。
- 通过种植计划系统获取种植信息，并裁剪为 `plant_info`。
- 通过种植计划或业务系统获取基础生育期节点，并作为 `plant_info.growth_stage` 传入；`成熟期` 不参与防治推荐计算，无需传入。
- `/pestDisease/control/adjust-control-window` 和 `/pestDisease/control/merge-control-plan` 不调用打药适宜度外部服务，调用方需传入 `spray_suitability_data`。
- `/pestDisease/control/generate-theory-control-plan` 不接收 `spray_suitability_data`，只返回理论防治窗口、防治对象和防治方案。
- `/pestDisease/control/adjust-control-window` 使用调用方传入的打药适宜度数据做最终防治时间调整；审核后单类型防治建议按 `theory_window[0] - 3 天` 到 `theory_window[1] + 30 天` 的保守范围准备数据，接口会按算法实际检索范围裁剪。
- `/pestDisease/control/get-merge-spray-suitability-range` 用于常规和突发同时存在时，提前计算合并接口所需的打药适宜度取数范围。

接口按业务规则完成结果计算和格式化。
