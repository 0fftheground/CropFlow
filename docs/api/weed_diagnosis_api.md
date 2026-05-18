# 杂草自动诊断算法接口文档

## 一、概述

本系统提供水稻杂草自动诊断和防治建议 API 服务，包括土壤封闭日期推荐、茎叶除草药前调查时间推荐、茎叶除草防治日期推荐、药后调查日期推荐和补防诊断。

> 说明：算法不自动获取外部气象数据，所需气象数据由调用方通过接口参数传入。
>
> CropFlow 当前第一版对接口结果的执行反馈仅考虑人工录入，不接设备回调或第三方执行系统回传。

## 二、基础信息

| 项目 | 说明 |
|------|------|
| 接口地址 | `localhost` |
| 请求方式 | `POST` |
| Content-Type | `application/json` |
| 日期格式 | `YYYYmmdd`，例如 `20260410` |

## 三、状态码说明

| 状态码 | 解释 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |

## 四、通用响应格式

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "result": []
  }
}
```

部分接口会返回 `target`，用于给防治方案推荐算法提供防治靶标：

```json
{
  "code": 200,
  "msg": "已推荐除草日期",
  "data": {
    "target": {
      "水稻叶龄": 4.5,
      "防治靶标": ["5叶以下禾本科杂草", "未萌发草种"]
    },
    "result": []
  }
}
```

参数错误响应示例：

```json
{
  "code": 400,
  "msg": "参数错误: 缺少 cultivation_date",
  "data": {
    "result": []
  }
}
```

服务器内部错误响应示例：

```json
{
  "code": 500,
  "msg": "系统错误: 接口处理失败，请检查输入参数或稍后重试",
  "data": {
    "result": []
  }
}
```

## 五、通用参数说明

### 1. `weather_data` 气象数据

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `DATE` | 日期 | 是 | string | 格式：`YYYYmmdd` |
| `TEMP` | 平均温度 | 是 | float | 单位：℃ |

### 2. `province` 省份

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `province` | 省份 | 需要输出防治方案的接口必填 | string | 支持省份名称或省份编码，例如 `"湖南省"`、`"75"` |

防治方案筛选所需年份不需要单独传入，接口从 `cultivation_date` 前 4 位解析。例如 `cultivation_date=20260410` 时，年份按 `2026` 处理。

### 3. 防治方案

防治方案结构参考防治方案服务返回结果：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `处方` | 推荐处方 | array | 按复配顺序排列 |
| `兑水量` | 推荐兑水量 | string | 土壤封闭为 `3 L/亩`；茎叶除草和补防为 `4 L/亩` |

`处方` 元素说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `农药` | 农药名称 | string | - |
| `剂型` | 剂型 | string | - |
| `厂商` | 厂商 | string | - |
| `推荐用量` | 推荐用量 | string | - |

#### 气象数据范围要求

`weather_data` 必须提供连续逐日数据，`DATE` 覆盖范围按闭区间计算，即包含开始日期和结束日期当天。若一次请求涉及多个调查日期，应按最早开始日期和最晚结束日期合并提供完整连续气象数据。

各接口要求如下：

| 接口 | 是否需要 `weather_data` | 开始日期 | 结束日期 |
|------|-------------------------|----------|----------|
| 土壤封闭日期推荐 | 否 | - | - |
| 茎叶除草药前调查时间推荐 | 是 | 直播：`weed_germination_date`；机插/机抛：`cultivation_date` | 开始日期 + 45d |
| 茎叶除草防治日期推荐 | 是 | `survey_data_before_treatment` 中最早的 `调查日期` | 开始日期 + 45d |
| 药后调查日期推荐 | 否 | - | - |
| 补防诊断 | 否 | - | - |

> 示例中的 `weather_data` 仅展示字段格式；实际调用时需按上述范围传入完整连续逐日数据。

### 4. 药前调查数据

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `调查日期` | 药前调查日期 | 是 | string | 格式：`YYYYmmdd` |
| `水稻叶龄` | 水稻叶龄 | 是 | float | - |
| `稗草` | 稗草调查数据 | 是 | object | 包含 `leaf_age`、`mass` |
| `千金子` | 千金子调查数据 | 是 | object | 包含 `leaf_age`、`mass` |
| `阔叶草` | 阔叶草调查数据 | 是 | object | 包含 `mass` |
| `莎草` | 莎草调查数据 | 是 | object | 包含 `mass` |

药前调查对象子字段说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `leaf_age` | 杂草叶龄 | float | 对应杂草的叶龄 |
| `mass` | 杂草出草量 | float | 1 平米内对应杂草的出草量 |

### 5. 药后调查数据

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `调查日期` | 药后调查日期 | 是 | string | 格式：`YYYYmmdd` |
| `水稻叶龄` | 水稻叶龄 | 是 | float | - |
| `水稻药害等级` | 水稻药害等级 | 是 | string | `无`、`低`、`中`、`高` 等 |
| `稗草` | 稗草药后数据 | 是 | object | 包含 `防效`、`leaf_age`、`mass` |
| `千金子` | 千金子药后数据 | 是 | object | 包含 `防效`、`leaf_age`、`mass` |
| `阔叶草` | 阔叶草药后数据 | 是 | object | 包含 `防效`、`mass` |
| `莎草` | 莎草药后数据 | 是 | object | 包含 `防效`、`mass` |

药后调查对象子字段说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `防效` | 防治效果 | float | 取值范围：`0~1` |
| `leaf_age` | 杂草叶龄 | float | 对应杂草的叶龄 |
| `mass` | 杂草出草量 | float | 1 平米内对应杂草的出草量 |

## 六、接口详情

### （一）土壤封闭处方推荐

#### 请求地址

```http
POST /api/soil_treatment_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 可选值 / 规则 |
|------|------|------|------|---------------|
| `province` | 省份 | 是 | string | 用于筛选土壤封闭防治方案，支持省份名称或省份编码 |
| `rice_type` | 水稻遗传类型 | 是 | string | `粳稻`、`籼稻` |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`机插`、`机抛` |
| `cultivation_date` | 栽培时间 | 是 | string | 当 `cultivation_pattern=直播` 时填写播种日期；当 `cultivation_pattern=机插/机抛` 时填写移栽日期 |


#### 请求示例

```json
{
  "province": "75",
  "rice_type": "籼稻",
  "cultivation_system": "早稻",
  "cultivation_pattern": "直播",
  "cultivation_date": "20260410"
}
```

#### 返回字段

| 字段 | 含义 | 说明 |
|------|------|------|
| `杂草萌发起始日期` | 算法采用的杂草萌发起始日期 | - |
| `土壤封闭推荐日期` | 土壤封闭推荐日期，单日或起止日期 | - |
| `封闭操作` | 当前算法输出 `苗后封闭` | - |
| `防治方案` | 土壤封闭防治方案 | 包含 `处方`、`兑水量`，兑水量为 `3 L/亩` |

#### 返回示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "result": [
      {
        "土壤封闭推荐日期": ["20260410", "20260413"],
        "农事操作": "苗后封闭",
        "防治方案": {
          "处方": [
            {
              "农药": "示例农药",
              "剂型": "SC",
              "厂商": "示例厂商",
              "推荐用量": "100 ~ 150 mL/亩"
            }
          ],
          "兑水量": "3 L/亩"
        }
      }
    ]
  }
}
```

### （二）茎叶除草药前调查时间推荐

#### 请求地址

```http
POST /api/weed_survey_date_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 可选值 / 规则 |
|------|------|------|------|---------------|
| `weather_data` | 气象数据 | 是 | array | 直播从 `weed_germination_date` 至 `weed_germination_date + 45d`；机插/机抛从 `cultivation_date` 至 `cultivation_date + 45d`，均为闭区间连续逐日数据 |
| `rice_type` | 水稻遗传类型 | 是 | string | `粳稻`、`籼稻` |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`机插`、`机抛` |
| `cultivation_date` | 栽培时间 | 是 | string | 当 `cultivation_pattern=直播` 时填写播种日期；当 `cultivation_pattern=机插/机抛` 时填写移栽日期 |



#### 请求示例

```json
{
  "weather_data": [
    {
      "DATE": "20260409",
      "TEMP": 26
    }
  ],
  "rice_type": "籼稻",
  "cultivation_system": "早稻",
  "cultivation_pattern": "直播",
  "cultivation_date": "20260410"
}
```

#### 返回字段

| 字段 | 含义 |
|------|------|
| `推荐茎叶除草前调查日期` | 药前调查推荐日期 |

#### 返回示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "result": [
      {
        "推荐茎叶除草前调查日期": "20260418"
      }
    ]
  }
}
```

### （三）茎叶除草处方推荐

#### 请求地址

```http
POST /api/weed_treatment_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `province` | 省份 | 是 | string | 用于筛选茎叶除草防治方案，支持省份名称或省份编码 |
| `weather_data` | 气象数据 | 是 | array | 从 `survey_data_before_treatment` 中最早 `调查日期` 至该日期 + 45d，闭区间连续逐日数据 |
| `rice_type` | 水稻遗传类型 | 是 | string | `粳稻`、`籼稻` |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`机插`、`机抛` |
| `cultivation_date` | 栽培时间 | 是 | string | 播种日期或移栽日期 |
| `survey_data_before_treatment` | 药前调查数据 | 是 | array | 详见通用参数说明 |
| `last_survey_date` | 上次调查日期 | 否 | string / null | 格式：`YYYYmmdd`；默认 `null` |

#### 请求示例

```json
{
  "province": "75",
  "weather_data": [
    {
      "DATE": "20260418",
      "TEMP": 25
    }
  ],
  "rice_type": "籼稻",
  "cultivation_system": "早稻",
  "cultivation_pattern": "直播",
  "cultivation_date": "20260410",
  "last_survey_date": null,
  "survey_data_before_treatment": [
    {
      "调查日期": "20260418",
      "水稻叶龄": 4.5,
      "稗草": {
        "leaf_age": 2,
        "mass": 100
      },
      "千金子": {
        "leaf_age": 0,
        "mass": 0
      },
      "阔叶草": {
        "mass": 0
      },
      "莎草": {
        "mass": 0
      }
    }
  ]
}
```

#### 返回示例：已推荐防治日期

```json
{
  "code": 200,
  "msg": "已推荐除草日期",
  "data": {
    "target": {
      "水稻叶龄": 4.5,
      "防治靶标": ["5叶以下禾本科杂草", "未萌发草种"]
    },
    "result": [
      {
        "杂草萌发起始日期": "20260409",
        "防治对象": ["稗草"],
        "推荐防治日期": ["20260420"],
        "防治方案": {
          "处方": [
            {
              "农药": "示例农药",
              "剂型": "SC",
              "厂商": "示例厂商",
              "推荐用量": "100 ~ 150 mL/亩"
            }
          ],
          "兑水量": "4 L/亩"
        }
      }
    ]
  }
}
```

#### 返回示例：需重新调查

```json
{
  "code": 200,
  "msg": "5d后重新调查",
  "data": {
    "target": {
      "水稻叶龄": 4.5,
      "防治靶标": ["未萌发草种"]
    },
    "result": [
      {
        "杂草萌发起始日期": "20260418",
        "推荐茎叶除草前调查日期": "20260423"
      }
    ]
  }
}
```

### （四）药后调查日期推荐

> 当前算法不使用气象数据，本接口无需传入 `weather_data`。

#### 请求地址

```http
POST /api/after_treatment_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `control_date` | 实际防治日期 | 是 | string | 格式：`YYYYmmdd` |

#### 请求示例

```json
{
  "control_date": "20260420"
}
```

#### 返回示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "result": {
      "药后调查日期": "20260426"
    }
  }
}
```

### （五）补防诊断

> 当前算法不使用气象数据，本接口无需传入 `weather_data`。

#### 请求地址

```http
POST /api/additional_treatment_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `province` | 省份 | 需要立即补防时必填 | string | 用于筛选补防方案，支持省份名称或省份编码 |
| `cultivation_date` | 栽培时间 | 需要立即补防时必填 | string | 用于解析年份，格式：`YYYYmmdd` |
| `cultivation_system` | 稻作类型 | 需要立即补防时必填 | string | `早稻`、`中稻`、`晚稻` |
| `cultivation_pattern` | 栽培方式 | 需要立即补防时必填 | string | `直播`、`机插`、`机抛` |
| `weed_germination_date` | 杂草萌发起始日期 | 是 | string | 使用药后调查日期推荐结果中的 `杂草萌发起始日期` |
| `control_target` | 防治对象 | 是 | array | 使用药后调查日期推荐结果中的 `防治对象` |
| `control_date` | 实际防治/补防日期 | 是 | array | 每次防治或补防日期记录到数组中 |
| `after_treatment_survey_date` | 推荐药后调查日期 | 是 | string | 使用药后调查日期推荐结果中的 `药后调查日期` |
| `survey_data_before_treatment` | 药前调查数据 | 是 | array | 详见通用参数说明 |
| `survey_data_after_treatment` | 药后调查数据或补防后调查数据 | 是 | array | 详见通用参数说明 |

#### 请求示例

```json
{
  "province": "75",
  "cultivation_date": "20260410",
  "cultivation_system": "早稻",
  "cultivation_pattern": "直播",
  "weed_germination_date": "20260409",
  "control_target": ["稗草"],
  "control_date": ["20260420"],
  "after_treatment_survey_date": "20260426",
  "survey_data_before_treatment": [
    {
      "调查日期": "20260418",
      "水稻叶龄": 4.5,
      "稗草": {
        "leaf_age": 2,
        "mass": 100
      },
      "千金子": {
        "leaf_age": 0,
        "mass": 0
      },
      "阔叶草": {
        "mass": 0
      },
      "莎草": {
        "mass": 0
      }
    }
  ],
  "survey_data_after_treatment": [
    {
      "调查日期": "20260426",
      "水稻叶龄": 4.5,
      "水稻药害等级": "无",
      "稗草": {
        "防效": 0.75,
        "leaf_age": 3,
        "mass": 100
      },
      "千金子": {
        "防效": 0,
        "leaf_age": 0,
        "mass": 0
      },
      "阔叶草": {
        "防效": 0,
        "mass": 0
      },
      "莎草": {
        "防效": 0,
        "mass": 0
      }
    }
  ]
}
```

#### 返回说明

可能的 `msg`：

| msg | 含义 |
|-----|------|
| `无需补防` | 不需要补防 |
| `需缓解药害` | 暂不补防，需等待药害缓解 |
| `需要待药害缓解后进行补防，补充调查后重新录入数据` | 需要补充调查后再判断 |
| `需要立即补防` | 需要立即补防 |

仅当 `msg` 为 `需要立即补防` 时，返回 `防治方案`。当 `msg` 为 `无需补防`、`需缓解药害`、`需要待药害缓解后进行补防，补充调查后重新录入数据` 时，不返回 `防治方案`。

#### 返回示例

```json
{
  "code": 200,
  "msg": "需要立即补防",
  "data": {
    "target": {
      "水稻叶龄": 4.5,
      "防治靶标": ["5叶以下禾本科杂草"]
    },
    "result": [
      {
        "杂草萌发起始日期": "20260409",
        "防治对象": ["稗草"],
        "药后调查日期": "20260426",
        "实际药后调查日期": "20260426",
        "补防对象": ["稗草"],
        "推荐补防日期": ["20260426", "20260427"],
        "补充调查日期": null,
        "服务效果评估日期": null,
        "防治方案": {
          "处方": [
            {
              "农药": "示例农药",
              "剂型": "SC",
              "厂商": "示例厂商",
              "推荐用量": "100 ~ 150 mL/亩"
            }
          ],
          "兑水量": "4 L/亩"
        }
      }
    ]
  }
}
```

## 七、接口调用顺序

1. `/api/soil_treatment_diagnosis`
2. `/api/weed_survey_date_diagnosis`
3. `/api/weed_treatment_diagnosis`
4. `/api/after_treatment_diagnosis`
5. `/api/additional_treatment_diagnosis`
