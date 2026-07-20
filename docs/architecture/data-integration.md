# CropFlow Data Integration Design

> 本文档定义 CropFlow 的轻量数据集成层设计。目标不是复制完整数据平台，而是在现有 Plan-level MVP 架构中补齐外部数据、算法、文件和设备结果接入的统一边界。

---

# 1. 设计定位

CropFlow 当前已经有 `Event Module`、`Background Job Center`、各方向算法 adapter、`EventRecord`、`StagePredictionSnapshot`、`WeatherSnapshot` 和各类 `result_payload`。这些能力已经能支撑单条链路联调，但随着施肥、遥感、设备和更多算法接入，外部数据会越来越多。

`Data Integration Layer` 用来统一回答这些问题：

```text
1. 外部数据或算法结果从哪里来？
2. 什么时候拉取、谁触发、是否成功？
3. 原始输入和原始响应有没有留痕？
4. 数据是否通过最小质量检查？
5. 哪份外部数据最终影响了哪些业务对象？
6. 失败、重试、超时、版本变化如何追溯？
```

它不是新的业务决策中心，也不是通用工作流引擎。

---

# 2. 设计原则

```text
1. 外部接入统一进 Data Integration Layer。
2. Data Integration Layer 只负责连接、标准化、快照、质量检查和追溯。
3. 业务判断仍由 Stage Orchestrator / Task Module / Execution Module / Plan Orchestrator 完成。
4. 不让外部 adapter 直接创建 FarmingTask 或 OperationPlan。
5. 重要外部调用结果必须有快照或事件留痕。
6. 第一版保持轻量，优先复用 EventRecord 和现有 snapshot，不急于引入完整数据平台。
```

推荐链路：

```text
External source / algorithm / file / execution system
  -> Data Integration Layer
  -> ExternalDataSnapshot / EventRecord / standardized DTO
  -> Stage Orchestrator / Task Module / Execution Module / Plan Orchestrator
  -> CropFlow business objects
```

禁止链路：

```text
External source / algorithm / file
  -> directly create FarmingTask / OperationPlan / ReviewRequest
```

---

# 3. 和现有模块的关系

## 3.1 Event Module

`Event Module` 继续负责接收、标准化和记录系统可处理的事件。

`Data Integration Layer` 可以产生标准事件，例如：

```text
WeatherUpdated
ExternalDataImported
AlgorithmResultRecorded
RemoteSensingResultRecorded
SoilTestResultImported
ExecutionStatusUpdated
```

边界：

```text
Data Integration Layer 负责外部调用和数据接入事实。
Event Module 负责事件记录和转发。
Plan Orchestrator 负责后续业务编排。
```

## 3.2 Background Job Center

`Background Job Center` 继续负责调度周期性检查。

它可以触发 Data Integration Layer：

```text
DailyWeatherCheckJob -> WeatherIntegrationService
SurveyDateRecommendationJob -> AlgorithmIntegrationService
ExecutionStatusPollingJob -> ExternalExecutionIntegrationService
RemoteSensingProcessingJob -> RemoteSensingIntegrationService
```

Job 不直接拼外部接口 payload，也不直接解释业务结果。

## 3.3 Stage Orchestrator

生育期预测、天气变化和积温计算仍归 `Stage Orchestrator`。

Data Integration Layer 只负责：

```text
1. 调用气象或生育期预测外部服务。
2. 记录 request / response / dataVersion。
3. 做基础质量检查，例如日期连续性、地区字段、必填字段。
4. 返回标准化结果或产生标准事件。
```

`Stage Orchestrator` 决定是否更新：

```text
CropStageState
CropThermalTimeState
StagePredictionSnapshot
StageChanged
```

## 3.4 Task Module

农事日历、植保、灌溉、施肥等算法调用可以通过 Data Integration Layer 执行。

Data Integration Layer 返回算法结果和快照引用。`Task Module` 决定是否创建或更新：

```text
CalendarItem
TaskIntent
FarmingTask
OperationPlan
ReviewRequest
```

## 3.5 Execution Module

外部执行系统、无人机作业平台、设备状态查询可以通过 Data Integration Layer 统一记录外部调用和响应。

`Execution Module` 仍负责更新：

```text
Execution
ExecutionRecord
DeviceCommand
```

---

# 4. 第一版接入范围

第一版建议覆盖以下来源：

| 来源类型 | 示例 | 接入方式 | 业务落点 |
|---|---|---|---|
| weather_api | 气象实况 / 预报 | batch / pull | WeatherSnapshot / WeatherUpdated |
| stage_algorithm | 生育期预测接口 | sync call | StagePredictionSnapshot |
| agronomy_calendar_algorithm | 农事日历接口 | sync call / job | CalendarItem |
| plant_protection_algorithm | 植保诊断 / 防治推荐 | sync call | TaskIntent / ReviewRequest / OperationPlan |
| fertilization_algorithm | 施肥处方 / 变量处方图 | sync call | OperationPlan / ReviewRequest |
| soil_lab_file | 土壤检测报告 | file upload / manual import | ExecutionRecord / ExternalDataSnapshot |
| remote_sensing_algorithm | 影像拼接 / 长势监测 / 异常点 | async job / callback | ExecutionRecord / Evaluation / OperationPlan |
| external_execution_system | 设备 / 无人机 / 第三方作业平台 | callback / polling | Execution / ExecutionRecord |

库存相关接入第一版可先文档化，不要求落地。

---

# 5. 设计对象草案

这些对象是设计目标，不要求一次全部入库。第一版可以先用 `EventRecord`、业务 snapshot 和日志承接。

## 5.1 ExternalDataSource

外部数据源或算法服务定义。

| field | type | notes |
|---|---|---|
| id | id | 主键 |
| sourceKey | string | 稳定编码，如 `weather_api`、`fertilization_algorithm` |
| sourceType | enum | api / file / database / device / platform / manual |
| ownerModule | string | stage / task / execution / material |
| displayName | string | 展示名称 |
| endpointRef | string | endpoint 或配置引用，不直接保存敏感密钥 |
| authType | string | none / token / api_key / basic / custom |
| status | enum | active / inactive |
| metadata | json | 扩展配置 |

## 5.2 IntegrationRun

一次外部接入或算法调用运行记录。

| field | type | notes |
|---|---|---|
| id | id | 主键 |
| sourceId | id | ExternalDataSource |
| runType | enum | pull / push / callback / file_import / algorithm_call |
| triggerType | enum | job / event / user / orchestrator / api |
| triggerRef | json | 触发来源，例如 EventRecord id、jobKey、task id |
| status | enum | pending / running / succeeded / failed / cancelled |
| startedAt | datetime | 开始时间 |
| finishedAt | datetime | 结束时间 |
| requestHash | string | 请求摘要 hash，用于幂等和去重 |
| inputSummary | json | 输入摘要，不放敏感全文 |
| outputSummary | json | 输出摘要 |
| errorCode | string | 错误码 |
| errorMessage | text | 错误详情 |
| retryCount | integer | 重试次数 |
| idempotencyKey | string | 幂等键 |

## 5.3 ExternalDataSnapshot

外部数据或算法结果快照。

| field | type | notes |
|---|---|---|
| id | id | 主键 |
| sourceId | id | ExternalDataSource |
| integrationRunId | id | IntegrationRun |
| plantingPlanId | id | 可为空 |
| snapshotType | enum | request / response / file / normalized_payload / quality_report |
| dataVersion | string | 外部版本或系统生成版本 |
| schemaVersion | string | 映射结构版本 |
| contentHash | string | 内容 hash |
| payload | json | 小型 JSON 快照 |
| fileRef | string | 大文件引用，例如报告、影像、原始文件 |
| occurredAt | datetime | 外部数据发生时间 |
| receivedAt | datetime | 系统接收时间 |

## 5.4 DataQualityCheck

对接入数据的基础质量检查结果。

| field | type | notes |
|---|---|---|
| id | id | 主键 |
| integrationRunId | id | IntegrationRun |
| snapshotId | id | ExternalDataSnapshot |
| checkKey | string | 检查项编码 |
| checkType | enum | required_field / date_range / unit / schema / coverage / duplicate / custom |
| status | enum | passed / warning / failed |
| severity | enum | info / warning / error |
| message | text | 检查说明 |
| details | json | 结构化细节 |

## 5.5 DataLineageLink

外部数据和业务对象之间的影响关系。

| field | type | notes |
|---|---|---|
| id | id | 主键 |
| sourceType | string | external_snapshot / event_record / execution_record 等 |
| sourceId | id | 来源对象 id |
| relationType | string | used_as_input / produced / triggered / derived_from / superseded |
| targetType | string | OperationPlan / TaskIntent / ExecutionRecord 等 |
| targetId | id | 目标对象 id |
| evidenceEventId | id | 可选 EventRecord |
| reason | text | 关系说明 |
| createdAt | datetime | 创建时间 |

## 5.6 MappingSpec

外部字段到 CropFlow 对象字段的映射说明。第一版建议先文档化，后续再表结构化。

| field | type | notes |
|---|---|---|
| sourceKey | string | 外部来源编码 |
| sourceField | string | 外部字段路径 |
| targetObject | string | CropFlow 对象 |
| targetField | string | 字段路径 |
| transformRule | text | 转换规则 |
| required | boolean | 是否必填 |
| notes | text | 说明 |

---

# 6. 典型接入流程

## 6.1 气象数据

```text
DailyWeatherCheckJob
  -> WeatherIntegrationService
  -> IntegrationRun
  -> ExternalDataSnapshot(response)
  -> DataQualityCheck(date_range / required_field)
  -> EventRecord(WeatherUpdated)
  -> Stage Orchestrator
  -> WeatherSnapshot / StagePredictionSnapshot / CropStageState
```

关键规则：

```text
1. Integration 只判断数据是否完整、版本是否变化。
2. 是否触发生育期变化由 Stage Orchestrator 判断。
3. forecast / observed / climatology 必须保留来源类型。
```

## 6.2 算法调用

适用：生育期、农事日历、植保、施肥、遥感算法。

```text
Domain service requests algorithm call
  -> AlgorithmIntegrationService
  -> build request snapshot
  -> call external algorithm
  -> save response snapshot
  -> quality check
  -> return standardized DTO
  -> domain service maps DTO to TaskIntent / OperationPlan / ExecutionRecord
```

关键规则：

```text
1. 外部算法调用不要和数据库业务状态更新放在同一个强事务里。
2. request / response 都要能追溯。
3. 算法响应不直接等于 OperationPlan，必须由业务模块映射。
4. no_action / need_more_info / requires_review 是业务语义，不在 Integration 层做最终判断。
```

## 6.3 土壤检测报告导入

```text
User uploads soil test report
  -> FileIntegrationService
  -> IntegrationRun(file_import)
  -> ExternalDataSnapshot(file)
  -> DataQualityCheck(schema / required_field / unit)
  -> EventRecord(SoilTestResultImported)
  -> Task / Execution service
  -> ExecutionRecord.result_payload.soilTestResult
```

关键规则：

```text
1. 原始报告保留 fileRef。
2. 解析后的结构化结果保存 normalized_payload 快照。
3. 土样检测任务的 ExecutionRecord 保存业务可用结果。
4. 后续施肥处方通过 sourceExecutionRecordId 或 lineage 追溯检测结果。
```

## 6.4 遥感影像与长势监测

```text
Remote sensing task execution
  -> image upload
  -> FileIntegrationService
  -> RemoteSensingIntegrationService
  -> async algorithm call / callback
  -> ExternalDataSnapshot(file / response / normalized_payload)
  -> DataQualityCheck(coverage / schema / quality)
  -> ExecutionRecord / Evaluation / OperationPlan
```

关键规则：

```text
1. 原始影像、拼接结果、异常点结果、变量处方结果要分开留痕。
2. 大文件只保存 fileRef，不直接塞入 JSON payload。
3. 是否触发人工复核或变量穗肥处方由业务模块判断。
```

## 6.5 外部执行系统

```text
Execution Module creates execution intent
  -> ExternalExecutionIntegrationService
  -> send command / dispatch task
  -> IntegrationRun
  -> callback or polling result
  -> EventRecord(ExecutionStatusUpdated)
  -> Execution Module
  -> Execution / ExecutionRecord
```

关键规则：

```text
1. 外部平台回调先记录原始结果。
2. Execution Module 决定状态如何更新。
3. 轮询兜底和主动回调应复用同一套标准化结果。
```

---

# 7. 错误、重试和幂等

## 7.1 错误分类

| errorType | examples | default action |
|---|---|---|
| connectivity_error | timeout / DNS / refused | retry |
| auth_error | token invalid / permission denied | stop and notify |
| schema_error | missing field / unknown response | stop and create quality failure |
| data_quality_error | date gap / invalid unit / coverage missing | warning or stop by policy |
| business_rejection | algorithm says no_action / no feasible window | return to business module |
| external_processing_error | remote sensing job failed | retry or manual follow-up |

## 7.2 幂等键建议

| scenario | idempotencyKey |
|---|---|
| weather daily fetch | sourceKey + farmId + weatherDate + sourceType + dataVersion |
| stage prediction | sourceKey + plantingPlanId + inputHash |
| fertilization algorithm | sourceKey + plantingPlanId + sourceExecutionRecordId + inputHash |
| soil test import | sourceKey + fileHash + plantingPlanId |
| remote sensing callback | sourceKey + externalJobId + resultVersion |
| execution status polling | sourceKey + externalExecutionId + statusVersion |

---

# 8. Data quality 最小检查

第一版只做阻断开发风险最高的检查：

```text
1. required_field：必填字段是否存在。
2. date_range：日期是否连续、是否在合理窗口内。
3. schema：是否符合接口契约版本。
4. unit：面积、用量、温度、积温、药量、肥量单位是否可识别。
5. coverage：地块、采样点、影像、处方区域是否覆盖目标计划范围。
6. duplicate：是否重复导入同一外部结果。
```

检查结果不直接决定业务动作，除非调用方明确配置为阻断。

---

# 9. 和业务对象的映射原则

| 外部数据 | Integration 留痕 | 业务对象落点 |
|---|---|---|
| 气象日数据 | ExternalDataSnapshot / WeatherSnapshot | CropThermalTimeState / StagePredictionSnapshot |
| 生育期预测响应 | ExternalDataSnapshot | StagePredictionSnapshot |
| 农事日历响应 | ExternalDataSnapshot | CalendarItem |
| 植保诊断响应 | ExternalDataSnapshot | TaskIntent.rule_result / OperationPlan |
| 施肥处方响应 | ExternalDataSnapshot | OperationPlan.parameters / prescription_map |
| 土壤检测报告 | ExternalDataSnapshot(file / normalized_payload) | ExecutionRecord.result_payload |
| 遥感影像结果 | ExternalDataSnapshot(file / normalized_payload) | ExecutionRecord / Evaluation / OperationPlan |
| 外部执行状态 | ExternalDataSnapshot / EventRecord | Execution / ExecutionRecord |

原则：

```text
1. Integration 保存外部事实和快照。
2. 业务对象保存当前业务需要消费的结果。
3. 大文件保存 fileRef。
4. 结构稳定且高频查询的字段再逐步结构化。
```

---

# 10. 分阶段落地建议

## Phase A：文档和约束先行

```text
1. 新增本文档。
2. 在新方向 API contract 中补 MappingSpec 表。
3. 明确每个算法接口的 sourceKey、inputSummary、outputSummary 和质量检查项。
4. 不新增数据库表。
```

## Phase B：复用现有对象

```text
1. 使用 EventRecord 记录 integration 事件。
2. 使用各业务 snapshot 保存关键 request / response。
3. 统一 adapter 返回结构，至少包含 raw_response、normalized_result、source_key、data_version。
4. 在 OperationPlan / ExecutionRecord / TaskIntent 中记录 sourceEventId 或 sourceExecutionRecordId。
```

## Phase C：新增轻量表

优先顺序：

```text
1. cf_external_data_source
2. cf_integration_run
3. cf_external_data_snapshot
4. cf_data_quality_check
5. cf_data_lineage_link
```

暂不建议第一版就实现通用数据湖、CDC、对象存储权限体系或可视化 pipeline builder。

## Phase D：和 agent / ontology 对接

```text
1. DataLineageLink 为 agent 提供证据链。
2. IntegrationRun 为 agent 提供外部调用历史和失败原因。
3. ExternalDataSnapshot 为 agent 提供原始事实引用。
4. MappingSpec 为 agent 提供字段语义和对象落点。
```

---

# 11. 当前开放问题

```text
1. 是否所有算法调用都必须保存 request 快照，还是只保存 inputSummary？
2. 大文件 fileRef 未来使用本地路径、对象存储还是第三方文件系统？
3. 土壤检测报告是否由系统解析，还是先由人工录入结构化结果？
4. 遥感算法是同步调用、异步任务，还是外部平台回调？
5. 施肥处方图的区域粒度是地块、网格、采样点插值区，还是 GeoJSON 面？
6. IntegrationRun 和 EventRecord 是否一对一，还是一次 IntegrationRun 可产生多个 EventRecord？
7. 哪些 data_quality failed 应阻断业务推进，哪些只提示人工关注？
```

---

# 12. 当前结论

```text
1. CropFlow 需要 Data Integration Layer，但第一版应保持轻量。
2. 外部接口访问和原始结果应统一经过 Integration 边界。
3. Integration 不做最终业务决策，不直接创建任务或方案。
4. 当前先补设计、快照、质量检查和 lineage 口径。
5. 等施肥、遥感、土壤检测链路稳定后，再落独立表结构。
```
