# 杂草自动诊断算法接口文档

## 一、概述

本系统提供水稻杂草自动诊断和防治建议 API 服务，包括土壤封闭日期推荐、茎叶除草药前调查时间推荐、茎叶除草防治日期推荐、药后调查时间推荐、安全性调查后诊断和防效兼安全性调查后诊断。

> 说明：算法不自动获取外部气象数据，所需气象数据由调用方通过接口参数传入。

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
  "data": {}
}
```

参数错误响应示例：

```json
{
  "code": 400,
  "msg": "参数错误: 缺少 cultivation_date",
  "data": {}
}
```

服务器内部错误响应示例：

```json
{
  "code": 500,
  "msg": "系统错误: 接口处理失败，请检查输入参数或稍后重试",
  "data": {}
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
| `prescriptions` | 推荐处方 | array | 按复配顺序排列 |
| `water_volume` | 推荐兑水量 | string | 土壤封闭为 `3 L/亩`；茎叶除草和补防为 `4 L/亩` |

`prescriptions` 元素说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `pesticide` | 农药名称 | string | - |
| `formulation` | 剂型 | string | - |
| `manufacturer` | 厂商 | string | - |
| `recommended_dosage` | 推荐用量 | string | - |

#### 气象数据范围要求

`weather_data` 必须提供连续逐日数据，`DATE` 覆盖范围按闭区间计算，即包含开始日期和结束日期当天。若一次请求涉及多个调查日期，应按最早开始日期和最晚结束日期合并提供完整连续气象数据。

各接口要求如下：

| 接口 | 是否需要 `weather_data` | 开始日期 | 结束日期 |
|------|-------------------------|----------|----------|
| 土壤封闭日期推荐 | 否 | - | - |
| 茎叶除草药前调查时间推荐 | 是 | 直播：`weed_germination_date`；插秧/抛秧：`cultivation_date` | 开始日期 + 45d |
| 茎叶除草防治日期推荐 | 是 | `survey_data_before_treatment` 中最早的 `survey_date` | 开始日期 + 45d |
| 药后调查时间推荐 | 否 | - | - |
| 安全性调查后诊断 | 否 | - | - |
| 防效兼安全性调查后诊断 | 否 | - | - |

> 示例中的 `weather_data` 仅展示字段格式；实际调用时需按上述范围传入完整连续逐日数据。

### 4. 药前调查数据

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `survey_date` | 药前调查日期 | 是 | string | 格式：`YYYYmmdd` |
| `rice_leaf_age` | 水稻叶龄 | 是 | float | - |
| `BaiCao` | 稗草调查数据 | 是 | object | 包含 `leaf_age`、`mass` |
| `QianJinZi` | 千金子调查数据 | 是 | object | 包含 `leaf_age`、`mass` |
| `KuoYeCao` | 阔叶草调查数据 | 是 | object | 包含 `mass` |
| `SuoCao` | 莎草调查数据 | 是 | object | 包含 `mass` |

药前调查对象子字段说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `leaf_age` | 杂草叶龄 | float | 仅稗草、千金子传入；可选值：`0`、`1`、`1.5`、`2`、`2.5`、`3` |
| `mass` | 杂草出草量 | float | 1 平米内对应杂草的出草量 |

### 5. 药后安全性调查数据

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `survey_date` | 安全性调查日期 | 是 | string | 格式：`YYYYmmdd` |
| `rice_injury_level` | 水稻药害等级 | 是 | string | `无`、`轻`、`中`、`较重`、`严重`、`极重` |

### 6. 药后防效兼安全性调查数据

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `survey_date` | 防效兼安全性调查日期 | 是 | string | 格式：`YYYYmmdd` |
| `rice_leaf_age` | 水稻叶龄 | 是 | float | - |
| `rice_injury_level` | 水稻药害等级 | 是 | string | `无`、`轻`、`中`、`较重`、`严重`、`极重` |
| `BaiCao` | 稗草药后数据 | 是 | object | 包含 `control_effect`、`leaf_age`、`mass` |
| `QianJinZi` | 千金子药后数据 | 是 | object | 包含 `control_effect`、`leaf_age`、`mass` |
| `KuoYeCao` | 阔叶草药后数据 | 是 | object | 包含 `control_effect`、`mass` |
| `SuoCao` | 莎草药后数据 | 是 | object | 包含 `control_effect`、`mass` |

药后防效兼安全性调查对象子字段说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `control_effect` | 防治效果 | float | 取值范围：`0~1` |
| `leaf_age` | 杂草叶龄 | float | 仅稗草、千金子传入；可选值：`0`、`1`、`1.5`、`2`、`2.5`、`3` |
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
| `province` | 省份 | 是 | string | 用于筛选土壤封闭防治方案，直接传入省份名称，例如 `"湖南省"` |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻`、`一季晚稻`、`双季晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`插秧`、`抛秧` |
| `cultivation_date` | 栽培时间 | 是 | string | 格式：`YYYYmmdd` |

#### 请求示例

```json
{
  "province": "湖南省",
  "cultivation_system": "早稻",
  "cultivation_pattern": "直播",
  "cultivation_date": "20260410"
}
```

#### 返回字段

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `soil_treatment_recommended_date` | 土壤封闭推荐日期 | array | 当前输出为起止日期数组，格式为 `[YYYYmmdd, YYYYmmdd]` |
| `farming_operation` | 农事操作 | string | 当前算法输出 `苗后封闭` |
| `control_plan` | 土壤封闭防治方案 | object | 结构见“五、通用参数说明-防治方案”，兑水量为 `3 L/亩` |

#### 成功返回示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "soil_treatment_recommended_date": [
      "20260418",
      "20260421"
    ],
    "farming_operation": "苗后封闭",
    "control_plan": {
      "prescriptions": [
        {
          "pesticide": "60%苄·丁",
          "formulation": "OD",
          "manufacturer": "安徽远景作物保护有限公司",
          "recommended_dosage": "100 g/亩"
        }
      ],
      "water_volume": "3 L/亩"
    }
  }
}
```

#### 参数错误返回示例

```json
{
  "code": 400,
  "msg": "参数错误: cultivation_pattern 必须为 直播、插秧 或 抛秧",
  "data": {}
}
```

#### 系统错误返回示例

```json
{
  "code": 500,
  "msg": "系统错误: 具体错误原因",
  "data": {}
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
| `weather_data` | 气象数据 | 是 | array | 直播从 `weed_germination_date` 至 `weed_germination_date + 45d`；插秧/抛秧从 `cultivation_date` 至 `cultivation_date + 45d`，均为闭区间连续逐日数据 |
| `rice_type` | 水稻遗传类型 | 是 | string | `粳稻`、`籼稻` |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`插秧`、`抛秧` |
| `cultivation_date` | 栽培时间 | 是 | string | 当 `cultivation_pattern=直播` 时填写播种日期；当 `cultivation_pattern=插秧/抛秧` 时填写移栽日期 |



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

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `pre_stem_leaf_herbicide_survey_date` | 茎叶除草药前调查推荐日期 | string | 格式：`YYYYmmdd` |

#### 返回示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "pre_stem_leaf_herbicide_survey_date": "20260418"
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
| `weather_data` | 气象数据 | 是 | array | 从 `survey_data_before_treatment` 中最早 `survey_date` 至该日期 + 45d，闭区间连续逐日数据 |
| `rice_type` | 水稻遗传类型 | 是 | string | `粳稻`、`籼稻` |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`插秧`、`抛秧` |
| `cultivation_date` | 栽培时间 | 是 | string | 播种日期或移栽日期 |
| `survey_data_before_treatment` | 单次药前调查数据 | 是 | object | 详见通用参数说明 |
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
  "survey_data_before_treatment": {
    "survey_date": "20260418",
    "rice_leaf_age": 4.5,
    "BaiCao": {
      "leaf_age": 2,
      "mass": 100
    },
    "QianJinZi": {
      "leaf_age": 0,
      "mass": 0
    },
    "KuoYeCao": {
      "mass": 0
    },
    "SuoCao": {
      "mass": 0
    }
  }
}
```

#### 返回字段

成功响应存在两个业务分支：`msg=已推荐除草日期` 时返回防治日期和防治方案；`msg=5d后重新调查` 时返回下次药前调查推荐日期。两个分支的 `data` 字段集合保持一致，不适用字段返回 `null`。

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `control_target` | 防治对象 | array / null | 已推荐除草日期时返回需要防治的杂草对象；需重新调查时为 `null` |
| `recommended_control_date` | 推荐防治日期 | array / null | 已推荐除草日期时返回 `[YYYYmmdd, YYYYmmdd]`；需重新调查时为 `null` |
| `control_plan` | 茎叶除草防治方案 | object / null | 已推荐除草日期时返回，结构见“五、通用参数说明-防治方案”，兑水量为 `4 L/亩`；需重新调查时为 `null` |
| `pre_stem_leaf_herbicide_survey_date` | 茎叶除草药前调查推荐日期 | string / null | 需重新调查时返回，格式：`YYYYmmdd`；已推荐除草日期时为 `null` |

#### 返回示例：已推荐防治日期

```json
{
  "code": 200,
  "msg": "已推荐除草日期",
  "data": {
    "control_target": [
      "BaiCao"
    ],
    "recommended_control_date": [
      "20260420",
      "20260420"
    ],
    "control_plan": {
      "prescriptions": [
        {
          "pesticide": "示例农药",
          "formulation": "SC",
          "manufacturer": "示例厂商",
          "recommended_dosage": "100 ~ 150 mL/亩"
        }
      ],
      "water_volume": "4 L/亩"
    },
    "pre_stem_leaf_herbicide_survey_date": null
  }
}
```

#### 返回示例：需重新调查

```json
{
  "code": 200,
  "msg": "5d后重新调查",
  "data": {
    "control_target": null,
    "recommended_control_date": null,
    "control_plan": null,
    "pre_stem_leaf_herbicide_survey_date": "20260423"
  }
}
```

### （四）药后调查时间推荐

> 当前算法不使用气象数据，本接口无需传入 `weather_data`。

#### 请求地址

```http
POST /api/after_treatment_survey_date_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `operation_date` | 实际作业日期 | 是 | string | 格式：`YYYYmmdd` |

#### 请求示例

```json
{
  "operation_date": "20260420"
}
```

#### 返回字段

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `rice_safety_survey_date` | 安全性调查日期 | string | 作业后 3d，作为“安全性调查后诊断”的调查日期，格式：`YYYYmmdd` |
| `control_effect_survey_date` | 防效兼安全性调查日期 | string | 作业后 7d，作为“防效兼安全性调查后诊断”的调查日期，格式：`YYYYmmdd` |

#### 返回示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "rice_safety_survey_date": "20260423",
    "control_effect_survey_date": "20260427"
  }
}
```

### （五）安全性调查后诊断

> 当前算法不使用气象数据，本接口无需传入 `weather_data`。

#### 请求地址

```http
POST /api/injury_mitigation_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `survey_date` | 安全性调查日期 | 是 | string | 格式：`YYYYmmdd` |
| `rice_injury_level` | 水稻药害等级 | 是 | string | `无`、`轻`、`中`、`较重`、`严重`、`极重` |

#### 请求示例

```json
{
  "survey_date": "20260423",
  "rice_injury_level": "中"
}
```

#### 返回字段

| 分支 | 返回字段 | 说明 |
|------|----------|------|
| 无需缓解 | `need_mitigation`、`measures`、`recommended_mitigation_date` | 安全性调查后诊断不输出药害趋势 |
| 需要缓解 | `need_mitigation`、`measures`、`recommended_mitigation_date` | 安全性调查后诊断不输出药害趋势 |

`data` 字段说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `need_mitigation` | 是否需要药害缓解 | boolean | `true` 表示需要缓解，`false` 表示无需缓解 |
| `measures` | 药害缓解措施 | array | 按药害等级返回对应措施 |
| `recommended_mitigation_date` | 建议执行措施时间 | array / null | 需要缓解时返回安全性调查后 `0~2d`，格式为 `[YYYYmmdd, YYYYmmdd]`；无需缓解时为 `null` |

#### 返回示例：无需缓解

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "need_mitigation": false,
    "measures": ["自然恢复"],
    "recommended_mitigation_date": null
  }
}
```

#### 返回示例：需要缓解

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "need_mitigation": true,
    "measures": ["尿素3～5公斤/亩"],
    "recommended_mitigation_date": ["20260423", "20260425"]
  }
}
```

### （六）防效兼安全性调查后诊断

> 当前算法不使用气象数据，本接口无需传入 `weather_data`。

#### 请求地址

```http
POST /api/additional_treatment_diagnosis
```

#### 请求参数

| 字段 | 含义 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `province` | 省份 | 是 | string | 用于筛选补防方案，支持省份名称或省份编码 |
| `cultivation_system` | 稻作类型 | 是 | string | `早稻`、`中稻`、`晚稻`、`一季晚稻`、`双季晚稻` |
| `cultivation_pattern` | 栽培方式 | 是 | string | `直播`、`插秧`、`抛秧` |
| `cultivation_date` | 栽培时间 | 是 | string | 格式：`YYYYmmdd`，用于解析年份 |
| `control_date` | 实际作业日期 | 是 | string | 格式：`YYYYmmdd` |
| `previous_injury_level` | 安全性调查药害等级 | 是 | string | 用于判断药害趋势 |
| `survey_data_before_treatment` | 单次药前调查数据 | 是 | object | 详见通用参数说明 |
| `survey_data_after_treatment` | 单次防效兼安全性调查数据 | 是 | object | 详见“药后防效兼安全性调查数据” |

#### 请求示例

```json
{
  "province": "湖南省",
  "cultivation_system": "早稻",
  "cultivation_pattern": "插秧",
  "cultivation_date": "20260418",
  "control_date": "20260420",
  "previous_injury_level": "轻",
  "survey_data_before_treatment": {
    "survey_date": "20260418",
    "rice_leaf_age": 4.5,
    "BaiCao": {
      "leaf_age": 2,
      "mass": 40
    },
    "QianJinZi": {
      "leaf_age": 0,
      "mass": 0
    },
    "KuoYeCao": {
      "mass": 0
    },
    "SuoCao": {
      "mass": 0
    }
  },
  "survey_data_after_treatment": {
    "survey_date": "20260426",
    "rice_leaf_age": 4.5,
    "rice_injury_level": "无",
    "BaiCao": {
      "control_effect": 0.8,
      "leaf_age": 3,
      "mass": 20
    },
    "QianJinZi": {
      "control_effect": 1,
      "leaf_age": 0,
      "mass": 0
    },
    "KuoYeCao": {
      "control_effect": 1,
      "mass": 0
    },
    "SuoCao": {
      "control_effect": 1,
      "mass": 0
    }
  }
}
```

#### 返回字段

所有成功分支的 `data` 字段集合保持一致，不适用字段返回 `null`。

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `need_recontrol` | 是否需要补防 | boolean | 所有成功分支必返 |
| `recontrol_target` | 需要补防的杂草对象 | array / null | 需要补防时返回；不需要补防时为 `null` |
| `recommended_recontrol_date` | 推荐补防日期 | array / null | 需要补防且药害无需缓解时返回 `[YYYYmmdd, YYYYmmdd]`；其他分支为 `null` |
| `control_plan` | 补防方案 | object / null | 返回 `recommended_recontrol_date` 时返回，结构见“五、通用参数说明-防治方案”，兑水量为 `4 L/亩`；其他分支为 `null` |
| `additional_survey_date` | 后续补充调查日期 | string / null | 药害仍需缓解时返回，格式：`YYYYmmdd`；其他分支为 `null` |
| `injury_mitigation` | 药害缓解结果 | object / null | 药害仍需缓解时返回，字段结构见下表；其他分支为 `null` |
| `service_effect_evaluation_date` | 服务效果评估日期 | string / null | 不需要补防且无需药害缓解时返回，格式：`YYYYmmdd`；其他分支为 `null` |

`injury_mitigation` 字段说明：

| 字段 | 含义 | 类型 | 说明 |
|------|------|------|------|
| `need_mitigation` | 是否需要药害缓解 | boolean | `true` 表示需要缓解，`false` 表示无需缓解 |
| `measures` | 药害缓解措施 | array | 按药害等级和药害趋势返回对应措施 |
| `injury_trend` | 药害趋势 | string / null | 根据 `previous_injury_level` 与防效兼安全性调查 `rice_injury_level` 判断，可能为 `减轻`、`持平`、`加重` 或 `null` |
| `recommended_mitigation_date` | 建议执行药害缓解措施时间 | array | 防效兼安全性调查后 `0~2d`，格式为 `[YYYYmmdd, YYYYmmdd]` |

分支非空字段说明：

| 分支 | 非空字段 |
|------|----------|
| 需要补防且可立即补防 | `need_recontrol`、`recontrol_target`、`recommended_recontrol_date`、`control_plan` |
| 需要补防但需药害缓解 | `need_recontrol`、`recontrol_target`、`additional_survey_date`、`injury_mitigation` |
| 不需要补防且无需药害缓解 | `need_recontrol`、`service_effect_evaluation_date` |
| 不需要补防但需药害缓解 | `need_recontrol`、`additional_survey_date`、`injury_mitigation` |

#### 返回示例：需要补防且可立即补防

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "need_recontrol": true,
    "recontrol_target": ["BaiCao"],
    "recommended_recontrol_date": ["20260426", "20260427"],
    "control_plan": {
      "prescriptions": [
        {
          "pesticide": "示例农药",
          "formulation": "SC",
          "manufacturer": "示例厂商",
          "recommended_dosage": "100 ~ 150 mL/亩"
        }
      ],
      "water_volume": "4 L/亩"
    },
    "additional_survey_date": null,
    "injury_mitigation": null,
    "service_effect_evaluation_date": null
  }
}
```

#### 返回示例：需要补防但需药害缓解

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "need_recontrol": true,
    "recontrol_target": ["KuoYeCao"],
    "recommended_recontrol_date": null,
    "control_plan": null,
    "additional_survey_date": "20260429",
    "injury_mitigation": {
      "need_mitigation": true,
      "measures": ["尿素3～5公斤/亩"],
      "injury_trend": "减轻",
      "recommended_mitigation_date": ["20260426", "20260428"]
    },
    "service_effect_evaluation_date": null
  }
}
```

#### 返回示例：不需要补防且无需药害缓解

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "need_recontrol": false,
    "recontrol_target": null,
    "recommended_recontrol_date": null,
    "control_plan": null,
    "additional_survey_date": null,
    "injury_mitigation": null,
    "service_effect_evaluation_date": "20260502"
  }
}
```

#### 返回示例：不需要补防但需药害缓解

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "need_recontrol": false,
    "recontrol_target": null,
    "recommended_recontrol_date": null,
    "control_plan": null,
    "additional_survey_date": "20260429",
    "injury_mitigation": {
      "need_mitigation": true,
      "measures": ["尿素3～5公斤/亩"],
      "injury_trend": "减轻",
      "recommended_mitigation_date": ["20260426", "20260428"]
    },
    "service_effect_evaluation_date": null
  }
}
```

## 八、接口调用顺序

1. `/api/soil_treatment_diagnosis`
2. `/api/weed_survey_date_diagnosis`
3. `/api/weed_treatment_diagnosis`
4. `/api/after_treatment_survey_date_diagnosis`
5. `/api/injury_mitigation_diagnosis`
6. `/api/additional_treatment_diagnosis`


