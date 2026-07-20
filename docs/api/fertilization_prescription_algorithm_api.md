# Fertilization Prescription Algorithm API

本文档是施肥处方算法的开发入口 contract。原始资料来自 `docs/references/raw/施肥算法接口.md`，本文件只整理 CropFlow 调用、校验和对象映射口径。

## 1. 接口概览

| 项目 | 说明 |
|---|---|
| 服务名称 | `fertility_split` |
| 默认地址 | `http://{host}:8090` |
| 接口 | `POST /run` |
| Content-Type | `application/json` |
| 用途 | 根据采样点土壤检测数据计算 N/P/K 施肥推荐方案 |
| 系统落点 | `OperationPlan.parameters` |

注意：算法 HTTP 200 仍可能表示业务失败，必须同时检查响应体 `code`。只有 `code=0` 且 `data` 为数组时，系统才生成待审核施肥处方。

## 2. 请求字段

| 字段 | 类型 | 必填 | CropFlow 来源 | 说明 |
|---|---|---|---|---|
| `waysType` | string | 是 | 人工选择 / 默认规则 | `soil / healthy / M3` |
| `targetYield` | number | 是 | 人工录入 | 目标产量，单位 `kg/亩` |
| `varietyType` | string | 是 | 品种映射 | `0=籼稻, 1=粳稻, 2=杂交稻（籼粳交）` |
| `riceType` | string | 是 | 稻作类型映射 | `3=双季晚稻, 4=早稻, 5=一季晚稻, 6=中稻, 8=再生稻` |
| `fertilizerA` | string | 否 | 平台配置 / 人工补录 | N-P-K 比例，如 `46-0-0` |
| `fertilizerB` | string | 否 | 平台配置 / 人工补录 | N-P-K 比例，如 `18-46-0` |
| `fertilizerC` | string | 否 | 平台配置 / 人工补录 | N-P-K 比例，如 `0-0-60` |
| `excelData` | array | 是 | 土壤检测结果表按采样点组装 | 采样点级检测数据 |

`fertilizerA/B/C` 均为空或 `0-0-0` 时，算法服务使用默认肥料：磷酸二铵、尿素、氯化钾。

## 3. `excelData[]`

| 字段 | 类型 | 必填 | 适用 `waysType` | CropFlow 来源 |
|---|---|---|---|---|
| `采样点ID` | string | 是 | all | 采样点表 |
| `经度` | number | 是 | all | 采样点坐标 |
| `纬度` | number | 是 | all | 采样点坐标 |
| `国标PH` | number | 是 | all | 土壤检测结果表 |
| `有机质（%）` | number | 是 | all | 土壤检测结果表；原始样表 `有机质` 组装时转为该字段 |
| `有效磷-M3` | number/string | 是 | all | 土壤检测结果表 |
| `有效钾-M3` | number/string | 是 | all | 土壤检测结果表 |
| `Buffer PH` | number | 是 | M3 / healthy | 土壤检测结果表 |
| `有效钙-M3` | number/string | 是 | M3 / healthy | 土壤检测结果表 |
| `有效镁-M3` | number/string | 是 | M3 / healthy | 土壤检测结果表 |
| `碱解氮` | number | 是 | soil | 土壤检测结果表 |

其他原始样表字段可保留在土壤检测结果表中，但不作为 `/run` 必需入参。

## 4. 响应字段

成功响应：HTTP 200 且 `code=0`。

| 字段 | 类型 | CropFlow 落点 | 说明 |
|---|---|---|---|
| `sectionId` | string | `sourceSamplingPointIds[]` | 采样点 ID |
| `sectionCropsId` | string | `algorithmSummary.sectionCropsId` | 当前通常为 `"0"` |
| `nRatio / pRatio / kRatio` | object | `parameters.nutrientRatio` | N/P/K 在基肥、分蘖肥、穗肥的分配比例 |
| `avgData` | object | `parameters.algorithmSummary.avgData` | N/P/K 总量摘要，原始格式如 `12.0_kg/亩` |
| `project[]` | array | `parameters.fieldPlans[]` | 各阶段施肥方案 |
| `NPK[]` | array | `parameters.npkMapping` | N/P/K 对应肥料名称 |

`project[].fertilizerType` 映射：

| 值 | 算法名称 | CropFlow `fertilizerStage` | 对应 taskSubtype |
|---|---|---|---|
| `0` | 基肥 | `base_fertilizer` | `fertilization.base_fertilizer` |
| `1` | 分蘖肥 | `tillering_fertilizer` | `fertilization.tillering_fertilizer` |
| `2` | 穗肥 | `panicle_fertilizer` | `fertilization.panicle_fertilizer` |

## 5. `OperationPlan.parameters` 映射

```json
{
  "fieldPlans": [
    {
      "fieldId": 101,
      "fieldName": "9号田块",
      "sourceSamplingPointIds": ["344ecfb3-bc70-4597-aa36-74d9f3b6738c"],
      "fertilizerStage": "base_fertilizer",
      "fertilizerStageName": "基肥",
      "fertilizers": [
        {
          "name": "尿素",
          "amountPerArea": 7.2,
          "amountUnit": "kg/亩",
          "ratio": "46-0-0",
          "rawAmount": "7.2_kg/亩"
        }
      ],
      "area": 12.5,
      "areaUnit": "亩"
    }
  ],
  "nutrientRatio": {
    "nRatio": { "base": 5, "tiller": 3, "ear": 2 },
    "pRatio": { "base": 10, "tiller": 0, "ear": 0 },
    "kRatio": { "base": 5, "tiller": 5, "ear": 0 }
  },
  "algorithmSummary": {
    "avgData": {
      "avgOfN": "12.0_kg/亩",
      "avgOfP": "5.0_kg/亩",
      "avgOfK": "3.0_kg/亩"
    }
  },
  "npkMapping": [{ "N": "尿素" }, { "P": "磷酸二铵" }, { "K": "氯化钾" }]
}
```

算法返回的是采样点单位面积施肥量。系统侧负责把采样点结果映射 / 补充为地块维度单位面积施肥量；第一版不要求算法返回地块绝对施肥总量。

## 6. 错误处理

| HTTP | `code` | 场景 | 系统动作 |
|---|---|---|---|
| 200 | `1` | 业务参数错误，例如 `waysType` 与内部 flag 不匹配 | 不生成处方，记录失败事件，提示补数或人工处理 |
| 400 | `400` | 必填字段缺失、枚举非法、`excelData` 解析失败 | 不生成处方，返回结构化校验错误 |
| 422 | `422` | 请求体 JSON 或字段类型不符合 Pydantic 校验 | 不生成处方，记录字段级错误 |
| 500 | `500` | 算法服务异常 | 记录失败事件，允许重试 |

## 7. 审核展示

施肥处方审核页至少展示：

1. 土壤检测数据：采样点、土样编号、地块、坐标、原始检测字段、被算法使用字段。
2. 算法入参：`waysType`、`targetYield`、`varietyType`、`riceType`、肥料 A/B/C、`excelData` 摘要。
3. 算法处方：三阶段 `fieldPlans[]`、肥料名称、N-P-K 比例、单位面积用量、算法原始摘要。

穗肥变量处方审核页至少展示穗肥基础处方、穗肥前长势监测记录、遥感后续任务 id、变量处方图 URL / 预览入口和叠加后的穗肥方案摘要。
