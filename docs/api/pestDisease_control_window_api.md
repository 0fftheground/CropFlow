# 防治窗口接口文档

## 1. 文档说明

本文档描述防治窗口相关生产接口，接口只负责算法计算并直接返回结果。

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
- 接口用途：只计算理论防治窗口、防治对象、防治方案和下一步所需打药适宜度数据日期范围，不做打药适宜度校正。

该接口不接收 `spray_suitability_data`，不返回 `final_window`、`suitability_dates`、`weather_adjust`。

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
| `status` | string/null | 理论推荐状态，例如 `0~2d`、`3~5d`、`normal`。 |
| `rounds` | array | 理论防治轮次列表。无需防治时为空数组。 |
| `spray_suitability_required_range` | array | 下一步需要获取的打药适宜度总日期范围，格式 `[YYYYMMDD, YYYYMMDD]`；无需防治时为 `[]`。 |
| `flags` | object | 辅助标记。 |

#### `rounds[]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `round` | integer | 防治轮次。 |
| `theory_window` | array | 理论防治窗口，格式 `[start_date, end_date]`。 |
| `targets` | object | 当前轮次防治对象。 |
| `prescription` | object | 当前轮次防治方案。 |

`spray_suitability_required_range` 规则：

- 常规防治：每个理论窗口 `[start, end]` 按 `start - 3 天` 到 `end + 15 天` 计算，再合并为总范围。
- 突发防治：理论窗口 `[start, end]` 按 `start` 到 `end + 10 天` 计算；若防治对象包含 `纹枯病` 则不晚于 `灌浆期`，否则不晚于 `齐穗期`。

### 2.5 响应示例

```json
{
  "code": 200,
  "msg": "单次防治",
  "data": {
    "control_type": "regular",
    "control_mode": "单次防治",
    "status": "3~5d",
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
    "spray_suitability_required_range": ["20260628", "20260718"],
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

该接口不重新计算理论防治方案，不生成或返回农药处方，不返回 `spray_suitability_required_range`。

### 3.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `control_type` | string | 是 | 推荐类型。`regular` 表示常规防治，`emergency` 表示突发病虫防治。 |
| `theory_plan` | object | 是 | `/pestDisease/control/generate-theory-control-plan` 返回的理论防治结果，传 `data` 部分即可；接口也兼容传完整 `code/msg/data` 响应对象。 |
| `spray_suitability_data` | array | 是 | 打药适宜度逐日数据，元素包含 `date` 和 `dy_ws`，应覆盖 `theory_plan.spray_suitability_required_range`。 |
| `plant_info` | object | 否 | 种植信息。`control_type=emergency` 时建议传入，用于齐穗期/灌浆期截止判断。 |

### 3.3 请求示例

```json
{
  "control_type": "regular",
  "theory_plan": {
    "control_type": "regular",
    "control_mode": "单次防治",
    "status": "3~5d",
    "rounds": [
      {
        "round": 1,
        "theory_window": ["20260701", "20260703"],
        "targets": {
          "二化螟": "防治",
          "稻飞虱": "防治"
        },
        "prescription": {
          "chemicals": [],
          "water_volume": "3 L/亩"
        }
      }
    ],
    "spray_suitability_required_range": ["20260628", "20260718"]
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

气象调整规则：

- 常规防治：优先理论窗口内；不适宜则向前 3 天；再不适宜则向后 15 天；仍无适宜日则取消防治。
- 突发防治：优先理论窗口内；不适宜则向后最多 10 天；传入 `plant_info` 时，非纹枯病不晚于齐穗期，包含纹枯病不晚于灌浆期。
- `spray_suitability_data` 缺少调整所需日期时返回参数错误，例如 `spray_suitability_data 缺少日期: 20260704`。

### 3.5 响应示例

```json
{
  "code": 200,
  "msg": "单次防治",
  "data": {
    "control_type": "regular",
    "control_mode": "单次防治",
    "status": "3~5d",
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

该接口不接收 `spray_suitability_data`，不做合并、不做气象筛选，只返回取数范围。单类型防治不调用该接口，直接使用理论接口返回的 `spray_suitability_required_range`。

### 4.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `regular_theory` | object | 是 | 常规理论防治结果，使用 `rounds[].theory_window` 和 `rounds[].targets`。`rounds` 至少 1 条。 |
| `emergency_theory` | object | 是 | 突发理论防治结果，使用 `rounds[].theory_window` 和 `rounds[].targets`。`rounds` 必须且只能 1 条。 |
| `extend_days` | integer | 否 | 合并接口顺延常规防治时的最大扩展天数，默认 `10`。 |
| `plant_info` | object | 否 | 种植信息。传入后，突发范围按齐穗期/灌浆期做上限裁剪。 |

取数范围规则：

- 常规每个理论窗口 `[start, end]`：取 `start - 3 天` 到 `end + 2 * extend_days + 30 天`。
- 默认 `extend_days=10` 时，常规为 `start - 3 天` 到 `end + 50 天`。
- 突发理论窗口 `[start, end]`：取 `start` 到 `end + 25 天`。
- 若传入 `plant_info`，突发对象包含 `纹枯病` 时不晚于灌浆期，否则不晚于齐穗期；裁剪后不会早于突发理论窗口结束日期。
- 总范围取所有常规范围和突发范围的最小开始日期、最大结束日期。

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
- 接口用途：基于常规和突发理论防治窗口，合并相邻防治事件，处理最小打药间隔，并筛选最终适宜打药日期。

### 5.2 请求参数

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `spray_suitability_data` | array | 是 | 打药适宜度逐日数据，元素包含 `date` 和 `dy_ws`。 |
| `regular_theory` | object | 是 | 常规理论防治事件。`rounds` 可包含多条未执行常规防治事件。 |
| `emergency_theory` | object | 是 | 突发理论防治事件。`rounds` 最多只能包含 1 条。 |
| `min_gap_days` | integer | 否 | 两次打药最小间隔天数，默认 `7`。 |
| `merge_gap_days` | integer | 否 | 常规与突发窗口相邻多少天内合并，默认 `3`。 |
| `extend_days` | integer | 否 | 因间隔不足顺延时，最多向后扩展天数，默认 `10`。 |
| `plant_info` | object | 条件必填 | 突发防治需要按生育期限制向后搜索范围时必填，结构同理论接口的 `plant_info`。 |

`regular_theory.rounds[]` 和 `emergency_theory.rounds[]` 均使用理论防治窗口 `theory_window`，不是已经经过气象适宜度调整的 `final_window`。接口内部会先合并和处理间隔，再基于 `spray_suitability_data` 筛选最终日期；适宜度调整后会再次合并和处理间隔。

`rounds[]` 字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `round` | integer | 是 | 防治轮次。 |
| `theory_window` | array | 是 | 理论防治窗口，格式 `[start_date, end_date]`。 |
| `targets` | object | 是 | 防治对象，例如 `{"二化螟": "防治"}`。 |

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
- `/pestDisease/control/generate-theory-control-plan` 不接收 `spray_suitability_data`，只返回调用方下一步需要获取的打药适宜度日期范围。
- `/pestDisease/control/adjust-control-window` 使用理论接口返回的 `spray_suitability_required_range` 对应日期数据做最终防治时间调整。
- `/pestDisease/control/get-merge-spray-suitability-range` 用于常规和突发同时存在时，提前计算合并接口所需的打药适宜度取数范围。

接口内部只做规则计算、窗口换算、适宜日期筛选、对象合并和结果格式化。
