# 生育阶段 GDD 阈值接口契约

本文档用于 CropFlow 后端与生育阶段 GDD 阈值算法服务联调，约定当前 FastAPI 服务的请求和响应格式。

## 0. 当前状态说明

1. 当前接口只负责匹配并返回生育阶段累计积温阈值，不负责根据天气序列推导阶段日期。
2. 当前接口内部读取本地 `config.yml`、`gdd_new_20250710.xlsx` 和 `variety_gdd.xlsx`，调用方不需要传入码表或积温表。
3. 返回字段使用 BBCH 编码作为 key。普通稻返回头季阶段；当 `cultiType == 8` 表示再生稻时，额外返回再生季 `Z_` 阶段。
4. 当前不返回 `再生季抽穗期`，因为接口返回编码列表中未包含 `Z_BBCH55`，且现有规则未单独计算该阶段。
5. 当前接口返回的累计积温阈值包含移栽场景下 `BBCH13 -> BBCH21` 的返青期积温；当 CropFlow 计划为直播时，后端在消费阈值前会按 `BBCH21 - BBCH13` 计算返青期积温差，并从 `BBCH21` 及后续阶段阈值中扣除。

## 1. 基本信息

- algorithmCode: `growth_stage_gdd_thresholds`
- algorithmName: 生育阶段 GDD 阈值匹配
- purpose: 根据品种、区域、熟制、稻作类型和亚种信息，匹配水稻各生育阶段累计积温阈值，并按 BBCH 编码返回
- owner: 生育期算法接口开发同事
- endpoint: `POST /growth-stage-gdd-thresholds`
- method: `POST`
- healthEndpoint: `GET /health`
- auth: 当前版默认内网服务，无额外鉴权；如后续增加鉴权，需保持 JSON body 不变

说明：

1. Docker 默认监听端口为 `15638`。
2. 本地可通过 `python main.py` 或 `uvicorn main:app --host 0.0.0.0 --port 15638` 启动。
3. 服务端参考地址为 `http://47.99.129.235`。

## 2. 触发时机

- upstream workflowKey / jobKey: `StagePredictionRefreshJob`
- trigger event:
  - `PlanCreated`
  - `PlanKeyInfoChanged`
  - 阈值表或码表版本变化后的人工作业重算
- trigger step: 后端需要初始化或刷新生育阶段阈值规则时调用
- whether sync or async: 同步调用

说明：

1. 天气更新不需要直接重调本接口。
2. 后端应基于本接口返回的阈值和自身天气序列，独立完成积温累计与阶段日期推导。
3. 如果计划信息中会影响阈值匹配的字段发生变化，应重新调用本接口。

## 3. 职责边界

### 3.1 CropFlow 后端负责

1. 组织种植计划基础字段和区域字段。
2. 调用本接口获取 BBCH 阶段累计积温阈值。
3. 获取天气数据并计算逐日积温、累计积温。
4. 根据累计积温和阶段阈值推导阶段日期。
5. 维护阶段状态、快照、重算和幂等控制。
6. 对直播计划做阈值换算：使用 `BBCH21 - BBCH13` 扣除移栽返青期积温，并把调整后的阈值写入 `StagePredictionSnapshot.thermal_thresholds`。
7. 处理接口失败后的重试、告警或人工排查流程。

### 3.2 GDD 阈值算法服务负责

1. 根据请求字段匹配品种积温表或通用积温标准表。
2. 返回当前业务需要的 BBCH 阶段累计积温阈值。
3. 根据 `cultiType == 8` 判断是否追加再生季阈值。
4. 不负责拉取天气数据。
5. 不负责计算阶段日期或返回完整 `stage_timeline`。

## 4. 请求输入

| field              | type    | required | default | source              | example        | notes                                                                |
| ------------------ | ------- | -------- | ------- | ------------------- | -------------- | -------------------------------------------------------------------- |
| `apprArea`       | string  | 是       | 无      | 品种/计划审定区域   | `长江中下游` | 用于通用积温表兜底匹配，也用于判断再生季地区参数                     |
| `controlSpec`    | string  | 是       | 无      | 对照品种 / 标准品种 | `五优308`    | 用于通用积温表匹配 `标准品种`                                      |
| `maturType`      | integer | 否       | `5`   | 熟制编码            | `5`          | 通过 `config.yml.codeDict.maturType` 转成中文值后匹配 `熟制`     |
| `cultiType`      | integer | 否       | `0`   | 实际稻作类型编码    | `8`          | `8` 表示再生稻；只有此时返回再生季 `Z_` 阈值                     |
| `apprCultiType`  | integer | 否       | `0`   | 审定稻作类型编码    | `6`          | 通过 `config.yml.codeDict.cultiType` 转成中文值后匹配 `稻作类型` |
| `subsType`       | integer | 否       | `0`   | 亚种编码            | `0`          | 通过 `config.yml.codeDict.subsType` 转成中文值后匹配 `亚种`      |
| `variety_name`   | string  | 否       | `""`  | 品种名称            | `黄广农占`   | 优先用于匹配品种积温表的 `品种`                                    |
| `farm_area_name` | string  | 否       | `""`  | 农场所处地区        | `湖南`       | 优先用于匹配品种积温表的 `审定地区`                                |

说明：

1. `apprArea` 和 `controlSpec` 为当前接口必填字段。
2. `variety_name + farm_area_name` 命中品种积温表时，优先使用品种积温表。
3. 品种积温表未命中时，接口使用通用积温标准表兜底。
4. 请求体不包含 `weather_data`，也不包含日期字段。

## 5. 请求示例

### 5.1 普通稻

```json
{
  "apprArea": "长江中下游",
  "controlSpec": "五优308",
  "maturType": 5,
  "cultiType": 6,
  "apprCultiType": 6,
  "subsType": 0,
  "variety_name": "不存在",
  "farm_area_name": "不存在"
}
```

### 5.2 再生稻

```json
{
  "apprArea": "长江中下游",
  "controlSpec": "五优308",
  "maturType": 5,
  "cultiType": 8,
  "apprCultiType": 6,
  "subsType": 0,
  "variety_name": "不存在",
  "farm_area_name": "不存在"
}
```

## 6. 响应输出

当前 FastAPI 实现直接返回 `data`，不额外包装 `code/msg`。

| field           | type   | meaning                       | example     | targetObject                                           | targetField                      |
| --------------- | ------ | ----------------------------- | ----------- | ------------------------------------------------------ | -------------------------------- |
| `data`        | object | BBCH 编码到累计积温阈值的映射 | 见下方      | `StagePredictionSnapshot` / `CropThermalTimeState` | `thermalThresholds` / 对应字段 |
| `data.BBCH13` | number | 三叶一心累计积温阈值          | `364.52`  | `threshold_rule.stage_thresholds`                    | `BBCH13`                       |
| `data.BBCH21` | number | 分蘖始期 / 分蘖期累计积温阈值 | `558.275` | `threshold_rule.stage_thresholds`                    | `BBCH21`                       |
| `data.BBCH50` | number | 破口期累计积温阈值            | `1411.0`  | `threshold_rule.stage_thresholds`                    | `BBCH50`                       |
| `data.BBCH58` | number | 齐穗期累计积温阈值            | `1521.0`  | `threshold_rule.stage_thresholds`                    | `BBCH58`                       |
| `data.BBCH89` | number | 成熟期累计积温阈值            | `2086.0`  | `threshold_rule.stage_thresholds`                    | `BBCH89`                       |

说明：

1. 普通稻返回 12 个头季 BBCH 阈值。
2. 再生稻在 12 个头季阈值基础上，额外返回 3 个 `Z_` 阈值。
3. value 为累计积温阈值，不是阶段日期。
4. CropFlow 保存到 `StagePredictionSnapshot.thermal_thresholds` 的阈值可能已按计划种植方式调整；直播计划会带有 `direct_seeding_threshold_adjustment` 标记，避免天气刷新或人工生育期重算时重复扣减。

### 6.1 普通稻返回字段

```json
[
  "BBCH13",
  "BBCH21",
  "BBCH28",
  "BBCH41",
  "BBCH42",
  "BBCH44",
  "BBCH45",
  "BBCH50",
  "BBCH51",
  "BBCH55",
  "BBCH58",
  "BBCH89"
]
```

### 6.2 再生稻额外返回字段

```json
[
  "Z_BBCH51",
  "Z_BBCH58",
  "Z_BBCH89"
]
```

### 6.3 BBCH 字段映射

| rawStageCode | stageName         | returnCondition            | notes                                              |
| ------------ | ----------------- | -------------------------- | -------------------------------------------------- |
| `BBCH13`   | 三叶一心          | 始终返回                   | 头季阶段点                                         |
| `BBCH21`   | 分蘖始期 / 分蘖期 | 始终返回                   | 当前数据表字段为 `分蘖期`，代码兼容 `分蘖始期` |
| `BBCH28`   | 有效分蘖终止期    | 始终返回                   | 头季阶段点                                         |
| `BBCH41`   | 幼穗分化1期       | 始终返回                   | 头季阶段点                                         |
| `BBCH42`   | 幼穗分化2期       | 始终返回                   | 头季阶段点                                         |
| `BBCH44`   | 幼穗分化4期       | 始终返回                   | 头季阶段点                                         |
| `BBCH45`   | 孕穗期            | 始终返回                   | 头季阶段点                                         |
| `BBCH50`   | 破口期            | 始终返回                   | 当前业务关键节点                                   |
| `BBCH51`   | 始穗期            | 始终返回                   | 头季阶段点                                         |
| `BBCH55`   | 抽穗期            | 始终返回                   | 头季阶段点                                         |
| `BBCH58`   | 齐穗期            | 始终返回                   | 当前业务关键节点                                   |
| `BBCH89`   | 成熟期            | 始终返回                   | 当前业务关键节点                                   |
| `Z_BBCH51` | 再生季始穗期      | 仅 `cultiType == 8` 返回 | 再生季阶段点                                       |
| `Z_BBCH58` | 再生季齐穗期      | 仅 `cultiType == 8` 返回 | 再生季阶段点                                       |
| `Z_BBCH89` | 再生季成熟期      | 仅 `cultiType == 8` 返回 | 再生季阶段点                                       |

## 7. 响应示例

### 7.1 普通稻响应

```json
{
  "data": {
    "BBCH13": 364.52,
    "BBCH21": 558.275,
    "BBCH28": 810.065,
    "BBCH41": 927.1,
    "BBCH42": 984.726,
    "BBCH44": 1224.47333,
    "BBCH45": 1296.74,
    "BBCH50": 1411.0,
    "BBCH51": 1441.0,
    "BBCH55": 1490.35,
    "BBCH58": 1521.0,
    "BBCH89": 2086.0
  }
}
```

### 7.2 再生稻响应

```json
{
  "data": {
    "BBCH13": 364.52,
    "BBCH21": 558.275,
    "BBCH28": 810.065,
    "BBCH41": 927.1,
    "BBCH42": 984.726,
    "BBCH44": 1224.47333,
    "BBCH45": 1296.74,
    "BBCH50": 1411.0,
    "BBCH51": 1441.0,
    "BBCH55": 1490.35,
    "BBCH58": 1521.0,
    "BBCH89": 2086.0,
    "Z_BBCH51": 2696.0,
    "Z_BBCH58": 2806.0,
    "Z_BBCH89": 3186.0
  }
}
```

## 8. 内部数据来源和匹配规则

### 8.1 内部数据来源

| data           | loader                 | file                             | notes                          |
| -------------- | ---------------------- | -------------------------------- | ------------------------------ |
| 编码字典       | `load_code_dict()`   | `config.yml` 中的 `codeDict` | 将请求中的编码转换为中文匹配值 |
| 通用积温标准表 | `load_common_gdd()`  | `gdd/gdd_new_20250710.xlsx`    | 品种积温表未命中时兜底使用     |
| 品种积温表     | `load_variety_gdd()` | `gdd/variety_gdd.xlsx`         | 优先按地区和品种名匹配         |

### 8.2 匹配顺序

1. 优先使用品种积温表，根据 `farm_area_name + variety_name` 匹配：

```text
审定地区 == farm_area_name
品种 == variety_name
```

2. 如果品种积温表未匹配到，则使用通用积温标准表，按以下顺序兜底：

```text
标准品种 + 稻作类型
熟制 + 审定地区 + 稻作类型 + 亚种
审定地区 + 稻作类型 + 亚种
长江中下游 + 稻作类型 + 亚种
```

3. 多条记录匹配时，使用第一条记录。

### 8.3 再生季阈值规则

仅当 `cultiType == 8` 时追加再生季阈值。再生季阈值以头季 `成熟期` 阈值为基准累加：

| 地区 / 条件                   | `Z_BBCH51`        | `Z_BBCH58`        | `Z_BBCH89`        |
| ----------------------------- | ------------------- | ------------------- | ------------------- |
| 安徽且 `apprCultiType == 6` | `成熟期 + 442.76` | `成熟期 + 561.79` | `成熟期 + 985.95` |
| 安徽且 `apprCultiType != 6` | `成熟期 + 431.9`  | `成熟期 + 530.56` | `成熟期 + 994.86` |
| 非安徽地区                    | `成熟期 + 610`    | `成熟期 + 720`    | `成熟期 + 1100`   |

## 9. 异常返回

当前 FastAPI 实现使用 HTTP status 表达错误，不返回统一 `code/msg` 包装。

| httpStatus | meaning                                  | retryable | fallbackAction                                 | notes                                 |
| ---------- | ---------------------------------------- | --------- | ---------------------------------------------- | ------------------------------------- |
| `422`    | 请求字段缺失或类型非法                   | 否        | 修正请求字段后重试                             | FastAPI / Pydantic 自动返回           |
| `404`    | 品种积温表和通用积温标准表都无法匹配数据 | 否        | 记录失败事件，人工排查品种、区域、码表或阈值表 | 当前代码捕获普通 `Exception` 后返回 |
| `500`    | 匹配记录缺少必需的生育阶段字段           | 是        | 排查阈值表字段完整性                           | 当前代码捕获 `KeyError` 后返回      |

## 10. 当前版约束

1. 当前版只支持水稻 GDD 阈值匹配。
2. 当前版不接收天气数据，不返回阶段日期。
3. 当前版不返回完整规则包，例如基础温度、积温计算方法、取整规则和生效日规则；这些仍由后端或上层规则另行维护。
4. 当前版响应不包含 `algorithm_code`、`algorithm_version`、`threshold_rule_id` 和 `threshold_rule_version`。
5. 普通稻不返回 `Z_BBCH*` 节点。
6. 再生稻当前只返回 `Z_BBCH51 / Z_BBCH58 / Z_BBCH89`，不返回 `Z_BBCH55`。
7. 直播阈值扣减属于 CropFlow 后端消费规则，不要求算法服务按种植方式返回两套阈值。
8. 如后续需要对齐 `growth_stage_prediction_api.md` 中的规则包结构，可在不改变请求字段的前提下，将响应扩展为 `code/msg/data.threshold_rule.stage_thresholds`。

## 11. 调用地址

本地：

```text
GET  http://localhost:15638/health
POST http://localhost:15638/growth-stage-gdd-thresholds
```

服务器：

```text
GET  http://47.99.129.235/health
POST http://47.99.129.235/growth-stage-gdd-thresholds
```
