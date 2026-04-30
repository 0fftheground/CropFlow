# CropFlow Plan-level MVP Data Model

> 本文档定义 CropFlow MVP 的逻辑数据模型草案。  
> 当前技术栈尚未确定，因此本文不绑定具体数据库、ORM、DDL 或迁移工具。

---

# 1. 建模原则

```text
1. 以单个 PlantingPlan 为主要业务边界。
2. 不引入独立 Recommendation Entity。
3. CalendarItem 是预备农事项，不是正式任务。
4. FarmingTask 是正式任务，是 Execution Module 的入口。
5. OperationPlan 是具体作业方案 / 处方方案。
6. Execution Module 只消费 FarmingTask + OperationPlan。
7. Feedback 不直接生成 FarmingTask，必须回到 Plan Orchestrator。
8. ReviewRequestResolved 不直接绕过编排器，必须回到 Plan Orchestrator。
9. NeedMoreInfo / NoAction 是 TaskIntent 状态或规则判断结果，不是独立核心对象。
10. EventRecord 是事件接入和追溯记录，不是业务决策对象。
11. Farm / Field 在 MVP 第一版进入数据模型，但不做跨农场、多计划全局调度。
12. 农事类型采用 taskCategory + taskSubtype 两级表达，允许后续新增 subtype。
```

---

# 2. 逻辑类型约定

本文使用以下逻辑类型：

```text
id：唯一标识，后续可落为 UUID、雪花 ID 或数据库自增 ID。
string：短文本。
text：长文本。
date：日期。
datetime：日期时间。
decimal：精确数值。
integer：整数。
boolean：布尔值。
enum：枚举值。
json：结构化扩展数据。
```

---

# 3. 通用字段

## 3.1 审计字段

多数持久化对象建议包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 主键 |
| createdAt | datetime | 创建时间 |
| updatedAt | datetime | 最近更新时间 |
| createdByType | enum | user / system / external |
| createdById | string | 创建者标识，可为空 |
| version | integer | 乐观锁或业务版本 |

## 3.2 追溯字段

由事件、规则、复核或外部系统生成的对象建议包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| sourceType | enum | 来源类型，例如 calendar / rule / review / feedback / manual / external |
| sourceEventId | id | 来源 EventRecord |
| sourceEntityType | string | 来源对象类型 |
| sourceEntityId | id | 来源对象 ID |
| reason | text | 生成或变更原因 |
| idempotencyKey | string | 业务幂等键 |

---

# 4. 实体清单

## 4.1 计划与生育期

```text
Farm
Field
PlantingPlan
CropStageState
CropThermalTimeState
StagePredictionSnapshot
```

## 4.2 农事项与任务

```text
CalendarItem
TaskGenerationPlan
TaskIntent
FarmingTask
OperationPlan
```

## 4.3 执行与反馈

```text
Execution
ExecutionRecord
DeviceCommand
Evaluation
Feedback
```

## 4.4 复核与通知

```text
ReviewRequest
SystemNotification
```

## 4.5 事件记录

```text
EventRecord
```

`EventRecord` 用于 Event Module 接收、标准化和记录事件，支撑幂等、追溯和重放分析。

---

# 5. 实体关系

```text
Farm 1 - N Field
Field 1 - N PlantingPlan

PlantingPlan 1 - 1 CropStageState
PlantingPlan 1 - 1 CropThermalTimeState
PlantingPlan 1 - N StagePredictionSnapshot

PlantingPlan 1 - N CalendarItem
CalendarItem 1 - N TaskGenerationPlan
TaskGenerationPlan 0..1 - N FarmingTask

PlantingPlan 1 - N TaskIntent
TaskIntent 0..1 - N FarmingTask

PlantingPlan 1 - N FarmingTask
FarmingTask 1 - N OperationPlan
FarmingTask 1 - N Execution

OperationPlan 0..1 - N Execution
Execution 1 - N ExecutionRecord
Execution 1 - 0..N DeviceCommand
Execution 1 - N Evaluation
Evaluation 1 - N Feedback

Feedback 0..1 - N ReviewRequest
TaskIntent 0..1 - N ReviewRequest
ReviewRequest 0..1 - N FarmingTask

PlantingPlan 1 - N SystemNotification
PlantingPlan 1 - N EventRecord
```

说明：

```text
1. OperationPlan 可以有 0 个、1 个或多个；提醒类任务可以没有复杂 OperationPlan。
2. ReviewRequest 的处理结果不能直接绕过 Plan Orchestrator。
3. EventRecord 可以关联多个后续业务对象，但业务对象不应依赖 EventRecord 执行业务判断。
4. DeviceCommand 只在设备、无人机或第三方系统执行场景出现；是否限制一对一留到后续确认。
```

---

# 6. 字段草案

## 6.1 Farm

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 农场 ID |
| farmName | string | 农场名称 |
| longitude | decimal | 经度 |
| latitude | decimal | 纬度 |
| address | string | 地址 |
| province | string | 省份 |
| metadata | json | 扩展信息 |

## 6.2 Field

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 地块 ID |
| farmId | id | 所属 Farm |
| boundaryAddress | text | 地块边界地址或边界描述 |
| metadata | json | 扩展信息 |

说明：

```text
Farm / Field 当前只保留已确认的最小字段。
地块面积、地块名称、土壤信息、地理边界坐标、种植区块等字段后续再按实际需要新增。
```

## 6.3 PlantingPlan

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 种植计划 ID |
| planCode | string | 计划编号 |
| planName | string | 计划名称 |
| farmId | id | 所属 Farm |
| fieldId | id | 所属 Field |
| cropName | string | 作物 |
| varietyName | string | 品种 |
| fieldCode | string | 地块编号 |
| fieldName | string | 地块名称 |
| area | decimal | 种植面积 |
| areaUnit | string | 面积单位 |
| regionCode | string | 区域编码 |
| regionName | string | 区域名称 |
| sowingDate | date | 播种日期 |
| expectedHarvestDate | date | 预计采收日期 |
| status | enum | 计划状态 |
| taskGenerationWindowDays | integer | 默认任务生成窗口 |
| metadata | json | 计划扩展信息 |

说明：

```text
fieldCode / fieldName / regionCode / regionName 在 PlantingPlan 中保留一份快照，避免后续地块信息变化影响历史计划展示。
```

## 6.4 CropStageState

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 生育期状态 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| currentStageCode | string | 当前生育期编码 |
| currentStageName | string | 当前生育期名称 |
| stageSource | enum | predicted / manual / system_adjusted |
| effectiveDate | date | 当前阶段生效日期 |
| sourceSnapshotId | id | 来源 StagePredictionSnapshot |
| lastUpdatedAt | datetime | 最近更新时间 |
| version | integer | 版本 |

## 6.5 CropThermalTimeState

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 积温状态 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| accumulatedThermalTime | decimal | 当前累计积温 |
| thermalTimeUnit | string | 积温单位 |
| baseTemperature | decimal | 基准温度 |
| startDate | date | 起算日期 |
| lastCalculatedDate | date | 最近计算日期 |
| thresholdSnapshotId | id | 使用的阈值快照 |
| dataVersion | string | 气象或计算数据版本 |

## 6.6 StagePredictionSnapshot

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 快照 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| predictionVersion | integer | 预测版本 |
| predictionSource | enum | initial / weather_update / manual_adjustment / plan_change |
| algorithmCode | string | 预测算法编码 |
| algorithmVersion | string | 预测算法版本 |
| generatedAt | datetime | 生成时间 |
| inputPayload | json | 预测输入快照 |
| stageTimeline | json | 生育期时间线 |
| thermalThresholds | json | 生育期积温阈值 |
| sourceEventId | id | 来源事件 |

## 6.7 CalendarItem

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 预备农事项 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| stageCode | string | 关联生育期编码 |
| taskCategory | enum | 农事大类 |
| taskSubtype | string | 农事子类 |
| title | string | 农事项标题 |
| description | text | 农事项说明 |
| suggestedStartDate | date | 建议开始日期 |
| suggestedEndDate | date | 建议结束日期 |
| status | enum | 预备农事项状态 |
| calendarVersion | integer | 日历版本 |
| sourceSnapshotId | id | 来源预测或日历快照 |
| invalidatedReason | text | 失效原因 |
| idempotencyKey | string | 幂等键 |

## 6.8 TaskGenerationPlan

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 任务生成计划 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| calendarItemId | id | 来源 CalendarItem |
| taskCategory | enum | 农事大类 |
| taskSubtype | string | 农事子类 |
| generationWindowStart | date | 生成窗口开始 |
| generationWindowEnd | date | 生成窗口结束 |
| generationCondition | json | 生成条件 |
| status | enum | 生成计划状态 |
| lastCheckedAt | datetime | 最近检查时间 |
| generatedTaskId | id | 已生成任务，可为空 |
| idempotencyKey | string | 幂等键 |

## 6.9 TaskIntent

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 任务意图 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| taskCategory | enum | 建议农事大类 |
| taskSubtype | string | 建议农事子类 |
| priority | enum | low / normal / high / urgent |
| status | enum | 任务意图状态 |
| triggerType | enum | field_condition / sensor / device / feedback / review / manual |
| triggerSummary | text | 触发摘要 |
| ruleResult | json | 规则判断结果 |
| suggestedAction | text | 建议处理方向 |
| needMoreInfoFields | json | 需要补充的信息 |
| noActionReason | text | 无需动作原因 |
| convertedTaskId | id | 转换后的 FarmingTask，可为空 |
| sourceEventId | id | 来源事件 |
| idempotencyKey | string | 幂等键 |

## 6.10 FarmingTask

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 正式任务 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| calendarItemId | id | 来源 CalendarItem，可为空 |
| taskGenerationPlanId | id | 来源 TaskGenerationPlan，可为空 |
| taskIntentId | id | 来源 TaskIntent，可为空 |
| reviewRequestId | id | 来源 ReviewRequest，可为空 |
| taskCategory | enum | 农事大类 |
| taskSubtype | string | 农事子类 |
| title | string | 任务标题 |
| description | text | 任务说明 |
| targetStageCode | string | 目标生育期 |
| plannedStartAt | datetime | 计划开始时间 |
| plannedEndAt | datetime | 计划结束时间 |
| priority | enum | low / normal / high / urgent |
| status | enum | 正式任务状态 |
| executionMode | enum | manual / device / drone / third_party |
| generationReason | text | 任务生成原因 |
| idempotencyKey | string | 幂等键 |

## 6.11 OperationPlan

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 作业方案 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| farmingTaskId | id | 所属 FarmingTask |
| planType | enum | 作业方案类型，通常与 taskCategory 对齐 |
| status | enum | 作业方案状态 |
| version | integer | 方案版本 |
| algorithmCode | string | 算法接口编码 |
| algorithmVersion | string | 算法版本 |
| operationArea | json | 作业区域 |
| operationWindowStart | datetime | 作业窗口开始 |
| operationWindowEnd | datetime | 作业窗口结束 |
| executionMode | enum | manual / device / drone / third_party |
| parameters | json | 作业参数，例如灌溉量、施肥量、药剂量 |
| prescriptionMap | json | 处方图或区域处方 |
| acceptanceCriteria | json | 验收标准 |
| basis | text | 方案依据 |
| sourceEventId | id | 来源事件 |
| idempotencyKey | string | 幂等键 |

说明：

```text
同一 FarmingTask 同一时间只允许一个 active OperationPlan。
历史方案通过 superseded / invalidated 状态保留。
```

## 6.12 Execution

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 执行实例 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| farmingTaskId | id | 关联 FarmingTask |
| operationPlanId | id | 关联 OperationPlan，可为空 |
| executionMode | enum | manual / device / drone / third_party |
| status | enum | 执行状态 |
| assignedToType | enum | user / device / external_system |
| assignedToId | string | 执行主体标识 |
| externalSystemCode | string | 外部系统编码 |
| externalExecutionId | string | 外部执行编号 |
| startedAt | datetime | 开始时间 |
| completedAt | datetime | 完成时间 |
| failureReason | text | 失败原因 |

说明：

```text
同一 FarmingTask 允许多次 Execution，用于失败重试、分批执行或补执行。
```

## 6.13 ExecutionRecord

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 执行记录 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| executionId | id | 所属 Execution |
| recordType | enum | status_update / result / manual_upload / device_callback |
| recordTime | datetime | 记录时间 |
| actualStartAt | datetime | 实际开始时间 |
| actualEndAt | datetime | 实际结束时间 |
| actualArea | decimal | 实际作业面积 |
| actualAmount | decimal | 实际用量 |
| amountUnit | string | 用量单位 |
| resultPayload | json | 外部回调或人工上传明细 |
| attachments | json | 图片、轨迹、文件等 |

## 6.14 DeviceCommand

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 设备指令 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| executionId | id | 所属 Execution |
| deviceId | string | 设备标识 |
| commandType | enum | 指令类型 |
| commandPayload | json | 指令内容 |
| status | enum | 指令状态 |
| sentAt | datetime | 下发时间 |
| acknowledgedAt | datetime | 确认时间 |
| callbackPayload | json | 回调结果 |

## 6.15 Evaluation

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 评价 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| executionId | id | 所属 Execution |
| operationPlanId | id | 关联 OperationPlan，可为空 |
| result | enum | pass / warning / fail / unknown |
| score | decimal | 评价分数，可为空 |
| metrics | json | 评价指标 |
| conclusion | text | 评价结论 |
| evaluatedAt | datetime | 评价时间 |

## 6.16 Feedback

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 反馈 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| evaluationId | id | 来源 Evaluation |
| executionId | id | 来源 Execution |
| feedbackType | enum | completed / incomplete / abnormal / remedial_needed / adjust_future |
| severity | enum | info / warning / critical |
| status | enum | 反馈状态 |
| summary | text | 反馈摘要 |
| details | json | 反馈明细 |
| requiresReview | boolean | 是否需要人工复核 |
| feedbackVersion | integer | 反馈版本 |
| idempotencyKey | string | 幂等键 |

## 6.17 ReviewRequest

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 复核事项 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| reviewType | enum | task_intent / feedback / execution_exception / plan_change / stage_change |
| status | enum | 复核状态 |
| priority | enum | low / normal / high / urgent |
| sourceEntityType | string | 来源对象类型 |
| sourceEntityId | id | 来源对象 ID |
| title | string | 复核标题 |
| description | text | 复核说明 |
| decision | enum | approve / reject / need_more_info / no_action / adjust |
| decisionPayload | json | 复核结论明细 |
| resolvedBy | string | 处理人 |
| resolvedAt | datetime | 处理时间 |
| idempotencyKey | string | 幂等键 |

说明：

```text
MVP 阶段 ReviewRequest.decision 先采用简单枚举。
复杂复核结论暂放 decisionPayload，不单独建复核结论模型。
```

## 6.18 SystemNotification

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 通知 ID |
| plantingPlanId | id | 所属 PlantingPlan |
| notificationType | enum | review_required / task_due / task_updated / execution_alert / info |
| targetUserId | string | 接收用户 |
| title | string | 通知标题 |
| content | text | 通知内容 |
| status | enum | unread / read / dismissed |
| sourceEntityType | string | 来源对象类型 |
| sourceEntityId | id | 来源对象 ID |
| createdAt | datetime | 创建时间 |
| readAt | datetime | 阅读时间 |

## 6.19 EventRecord

| 字段 | 类型 | 说明 |
|---|---|---|
| id | id | 事件记录 ID |
| plantingPlanId | id | 所属 PlantingPlan，可为空 |
| eventType | string | 事件类型 |
| eventCategory | enum | input / domain |
| eventSource | enum | user / job / external / module |
| sourceSystem | string | 来源系统 |
| sourceRecordId | string | 外部来源记录 ID |
| payload | json | 标准化事件内容 |
| occurredAt | datetime | 事件发生时间 |
| receivedAt | datetime | 系统接收时间 |
| processedAt | datetime | 处理完成时间 |
| processingStatus | enum | received / processing / processed / failed / ignored |
| idempotencyKey | string | 幂等键 |
| errorMessage | text | 处理错误 |

---

# 7. 状态枚举草案

## 7.1 TaskCategory

第一版农事大类：

```text
irrigation
fertilization
plant_protection
field_inspection
soil_preparation
harvest
manual
```

## 7.2 TaskSubtype

`taskSubtype` 不建议在第一版全部固定死。MVP 可以先用字符串编码，并维护一份建议值：

```text
fertilization.base
fertilization.tillering
fertilization.panicle
plant_protection.weed_control
plant_protection.pest_control
plant_protection.disease_control
soil_preparation.rotary_tillage
soil_preparation.land_leveling
harvest.combine_harvest
inspection.field_patrol
```

后续新增农事细分类时，优先新增 `taskSubtype`，不新增核心对象。

## 7.3 PlantingPlanStatus

```text
created
initializing
active
completed
archived
failed
```

## 7.4 CalendarItemStatus

```text
active
converted
invalidated
cancelled
```

## 7.5 TaskGenerationPlanStatus

```text
active
generated
skipped
invalidated
cancelled
```

## 7.6 TaskIntentStatus

```text
pending_confirm
pending_more_info
confirmed
rejected
converted
no_action
expired
```

## 7.7 FarmingTaskStatus

```text
pending
confirmed
pending_review
pending_execute
executing
completed
failed
cancelled
expired
invalidated
```

## 7.8 OperationPlanStatus

```text
draft
active
superseded
invalidated
cancelled
```

## 7.9 ExecutionStatus

```text
created
dispatched
accepted
executing
completed
failed
cancelled
timeout
```

## 7.10 DeviceCommandStatus

```text
created
sent
acknowledged
succeeded
failed
timeout
cancelled
```

## 7.11 FeedbackStatus

```text
created
pending_review
handled
ignored
closed
```

## 7.12 ReviewRequestStatus

```text
open
in_review
resolved
cancelled
expired
```

---

# 8. 幂等键建议

| 场景 | 幂等键建议 |
|---|---|
| WeatherUpdated | plantingPlanId + weatherDate + dataVersion |
| TaskDueCheckTriggered | plantingPlanId + checkDate + generationWindow |
| FieldConditionReported | plantingPlanId + sourceType + sourceRecordId |
| ActualStageRecorded | plantingPlanId + stageCode + effectiveDate + sourceRecordId |
| ReviewRequestResolved | reviewRequestId + resolvedVersion |
| FeedbackGenerated | executionId + feedbackVersion |
| CalendarItem 生成 | plantingPlanId + calendarVersion + stageCode + taskCategory + taskSubtype + suggestedStartDate |
| FarmingTask 生成 | plantingPlanId + sourceEntityType + sourceEntityId + taskCategory + taskSubtype |
| OperationPlan 生成 | farmingTaskId + planType + version |

关键幂等键建议在数据库层建立唯一约束：

```text
EventRecord.idempotencyKey
FarmingTask.idempotencyKey
ReviewRequest.idempotencyKey
```

---

# 9. 版本与历史策略

```text
1. StagePredictionSnapshot 只追加，不覆盖。
2. CalendarItem 被新预测影响时，旧记录标记 invalidated，不物理删除。
3. TaskGenerationPlan 被替代时，旧记录标记 invalidated 或 skipped。
4. FarmingTask 未执行前可以更新；已执行或执行中的任务应保留历史，通过新任务或状态变更处理。
5. OperationPlan 刷新时生成新 version，旧版本标记 superseded 或 invalidated。
6. ExecutionRecord 只追加，不覆盖。
7. Feedback 可以通过 feedbackVersion 表示同一执行结果的多次反馈版本。
8. ReviewRequest resolved 后原则上不再修改结论；如需修正，应产生新复核事项或记录补充结论。
```

---

# 10. JSON 字段边界

允许先使用 JSON 承载外部算法、设备或评价明细：

```text
StagePredictionSnapshot.inputPayload
StagePredictionSnapshot.stageTimeline
StagePredictionSnapshot.thermalThresholds
TaskGenerationPlan.generationCondition
TaskIntent.ruleResult
OperationPlan.operationArea
OperationPlan.parameters
OperationPlan.prescriptionMap
OperationPlan.acceptanceCriteria
ExecutionRecord.resultPayload
Evaluation.metrics
Feedback.details
ReviewRequest.decisionPayload
EventRecord.payload
```

不建议放入 JSON 的内容：

```text
1. planId / taskId / executionId 等关联字段。
2. status / taskType / stageCode 等高频查询字段。
3. plannedStartAt / plannedEndAt / occurredAt 等时间筛选字段。
4. idempotencyKey 等幂等字段。
```

---

# 11. 暂不建模对象

MVP 阶段暂不建立以下独立实体：

```text
Recommendation
GlobalResourceSchedule
ApprovalFlow
RuleConfigAdmin
ExternalExecutionSystem
```

说明：

```text
1. Farm / Field 已进入 MVP 数据模型，但不代表支持多农场多计划全局调度。
2. 外部执行系统先通过 Execution.externalSystemCode、externalExecutionId、DeviceCommand.deviceId 等字段表达。
3. 规则配置后台暂不建模，运行期规则结果先保存在 TaskIntent.ruleResult 或 EventRecord.payload 中。
4. 多农场、多计划、跨计划资源调度不进入当前数据模型。
```

---

# 12. 已确认决策

基于当前讨论，第一版数据模型按以下决策推进：

```text
1. EventRecord 进入第一版正式数据模型。
2. Farm / Field 进入第一版正式数据模型。
3. 当前没有用户体系，createdById、targetUserId、resolvedBy 先用字符串占位。
4. stageCode 当前按固定编码处理。
5. 农事类型采用 taskCategory + taskSubtype，两级表达；大类先固定，子类允许后续新增。
6. 同一 FarmingTask 同一时间只允许一个 active OperationPlan。
7. 同一 FarmingTask 允许多次 Execution。
8. 附件、图片、无人机轨迹 MVP 先放 JSON。
9. 关键幂等键建议数据库唯一约束。
10. 软删除先统一使用业务 status，不引入 deletedAt。
11. DeviceCommand 与 Execution 的关系目前暂不强行确定，先允许一个 Execution 关联 0..N 个 DeviceCommand。
12. ReviewRequest.decision 先采用最简单枚举，复杂内容放 decisionPayload。
13. Farm 第一版字段为：farmName、longitude、latitude、address、province。
14. Field 第一版字段为：farmId、boundaryAddress。
```

---

# 13. 后续仍需确定

```text
1. 固定 stageCode 的完整枚举值。
2. 第一版 taskSubtype 建议清单是否需要进一步收敛。
3. 技术栈、数据库类型、ID 生成方式和命名风格。
```

---

# 14. 技术栈建议

在 3-4 人团队、Plan-level MVP、团队更熟悉 Python、且后续需要清晰模块边界和数据一致性的前提下，建议优先考虑：

```text
后端：Python + FastAPI
数据库：PostgreSQL
迁移：Alembic
ORM：SQLAlchemy
数据校验 / DTO：Pydantic
接口：REST API + OpenAPI
前端：由前端负责人选择
ID：UUID 或数据库生成 ID
命名：数据库 snake_case，代码 camelCase
```

前端技术栈暂不强制指定，但需要遵守接口契约：

```text
1. 接口协议：REST API。
2. API 文档：OpenAPI。
3. Mock：基于 OpenAPI 或固定 JSON 示例。
4. API 字段命名：camelCase。
5. 时间格式：ISO 8601。
6. 枚举值：与 docs/data-model.md 保持一致。
```

推荐理由：

```text
1. FastAPI 对 Python 团队上手成本低，自动生成 OpenAPI，适合前后端并行。
2. PostgreSQL 对关系模型、JSON 字段、唯一约束和事务支持都足够稳。
3. SQLAlchemy + Alembic 可以覆盖表结构、关系映射和迁移管理。
4. Pydantic 适合定义请求 / 响应 DTO，减少字段漂移。
5. REST + OpenAPI 便于前后端并行开发和 mock。
6. 前端框架由前端负责人选择，不影响后端模型和接口契约。
```

备选方案：

```text
1. 如果需要后台管理能力优先，可以考虑 Django + Django REST Framework + PostgreSQL。
2. 如果后端团队更熟 TypeScript，可以考虑 Node.js + NestJS + PostgreSQL + Prisma。
3. 如果后续有强企业集成、复杂事务和团队 Java 经验，再考虑 Java + Spring Boot + PostgreSQL。
```

当前默认推荐：Python + FastAPI + PostgreSQL。
