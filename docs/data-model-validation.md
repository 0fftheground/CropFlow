# CropFlow Data Model Validation Checklist

> 本文档用于把 `docs/data-model.md` 与真实业务流程、外部算法服务、执行反馈和前端页面逐项核对。  
> 本文档不是新的数据模型，核对后如果发现字段或关系需要调整，应回写到 `docs/data-model.md`。

---

# 1. 使用方式

建议每次和业务、算法服务、前端或后端讨论时，按以下格式记录：

```text
结论：confirmed / missing / changed / not_needed / later
影响对象：例如 PlantingPlan / CalendarItem / OperationPlan
处理方式：更新 data-model.md / 更新流程文档 / 暂不处理
负责人：
日期：
```

---

# 2. 计划创建字段核对

目标：确认创建 `PlantingPlan` 时前端实际录入、业务实际需要、算法实际依赖的字段。

## 2.1 Farm / Field

当前模型：

```text
Farm:
  farmName
  longitude
  latitude
  address
  province

Field:
  farmId
  boundaryAddress
```

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| Farm 的经纬度表示农场中心点还是默认地块点？ | pending | Farm.longitude / Farm.latitude |
| Field.boundaryAddress 是否只是文本，还是需要边界坐标数组？ | pending | Field.boundaryAddress / Field.metadata |
| 第一版是否需要 Field 名称？ | pending | Field |
| 第一版是否需要地块面积？ | pending | Field / PlantingPlan.area |
| 第一版是否需要土壤类型、土壤肥力、前茬作物？ | pending | Field.metadata / PlantingPlan.metadata |

## 2.2 PlantingPlan

当前模型重点字段：

```text
cropName
varietyName
sowingDate
expectedHarvestDate
area
taskGenerationWindowDays
```

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 创建计划时是否必须录入品种 varietyName？ | pending | PlantingPlan.varietyName |
| 播种日期是否一定有？是否存在移栽日期？ | pending | PlantingPlan.sowingDate / metadata |
| expectedHarvestDate 是用户输入还是系统预测？ | pending | PlantingPlan.expectedHarvestDate |
| area 是计划种植面积还是地块面积快照？ | pending | PlantingPlan.area |
| 是否需要种植方式，例如直播、移栽？ | pending | PlantingPlan.metadata |
| 是否需要作物季次，例如早稻、晚稻？ | pending | PlantingPlan.metadata / stageCode |

---

# 3. 生育期预测算法核对

目标：确认 `StagePredictionSnapshot / CropStageState / CropThermalTimeState` 能否完整承接生育期算法输入输出。

## 3.1 算法输入

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 生育期预测算法需要哪些计划字段？ | pending | StagePredictionSnapshot.inputPayload |
| 是否需要历史气象数据？ | pending | EventRecord / inputPayload |
| 是否需要未来天气预报？ | pending | inputPayload |
| 是否需要品种积温阈值表？ | pending | thermalThresholds |
| 是否需要地理位置经纬度？ | pending | Farm / Field / inputPayload |

## 3.2 算法输出

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| stageTimeline 的结构是什么？ | pending | StagePredictionSnapshot.stageTimeline |
| thermalThresholds 的结构是什么？ | pending | StagePredictionSnapshot.thermalThresholds |
| 是否返回当前阶段，还是只返回预测时间线？ | pending | CropStageState |
| 是否返回置信度或风险提示？ | pending | StagePredictionSnapshot.metadata |
| 是否需要记录算法版本？ | pending | algorithmCode / algorithmVersion |

## 3.3 stageCode

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 第一版固定 stageCode 列表是什么？ | pending | data-model.md |
| 不同作物是否共用同一套 stageCode？ | pending | CropStageState / CalendarItem |
| 人工录入真实生育期是否只能选择固定 stageCode？ | pending | ActualStageRecorded |

---

# 4. 农事日历算法核对

目标：确认农事日历接口返回内容能映射到 `CalendarItem / TaskGenerationPlan`。

## 4.1 算法输入

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 农事日历接口需要哪些计划字段？ | pending | EventRecord.payload / CalendarItem |
| 是否依赖生育期预测结果？ | pending | sourceSnapshotId |
| 是否依赖地块面积、位置、品种？ | pending | PlantingPlan / Farm / Field |
| 是否依赖历史管理习惯或地区农艺规则？ | pending | metadata / ruleResult |

## 4.2 算法输出

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 是否返回全周期农事项？ | pending | CalendarItem |
| 是否返回建议开始和结束日期？ | pending | suggestedStartDate / suggestedEndDate |
| 是否返回对应生育期？ | pending | stageCode |
| 是否返回任务生成条件？ | pending | TaskGenerationPlan.generationCondition |
| 是否返回优先级或风险等级？ | pending | CalendarItem / TaskGenerationPlan |
| 是否返回农事项说明和依据？ | pending | CalendarItem.description |

---

# 5. 农事类型核对

目标：确认 `taskCategory + taskSubtype` 是否足够覆盖第一版农事类型。

当前大类：

```text
irrigation
fertilization
plant_protection
field_inspection
soil_preparation
harvest
manual
```

当前建议子类：

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

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 施肥子类是否需要区分基肥、分蘖肥、穗肥以外的类型？ | pending | taskSubtype |
| 植保是否只分杂草防治、虫害防治、病害防治？ | pending | taskSubtype |
| 整地是否需要旋耕、耙田、平田等细类？ | pending | taskSubtype |
| 收割是否需要人工收割、机械收割、分批收割？ | pending | taskSubtype |
| 巡田是否只是人工任务，还是也可能由无人机或设备触发？ | pending | executionMode / taskSubtype |

---

# 6. OperationPlan 与算法服务核对

目标：确认作业方案算法返回内容能映射到 `OperationPlan`。

## 6.1 灌溉方案

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 灌溉算法需要哪些输入？ | pending | OperationPlan.parameters / inputPayload |
| 是否返回灌溉量、时长、水层目标？ | pending | parameters |
| 是否需要分区灌溉？ | pending | operationArea / prescriptionMap |
| 是否需要设备参数？ | pending | parameters / DeviceCommand |
| 验收标准是什么？ | pending | acceptanceCriteria / Evaluation.metrics |

## 6.2 施肥方案

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 施肥算法需要哪些输入？ | pending | OperationPlan.parameters |
| 是否返回肥料类型、用量、浓度、面积？ | pending | parameters |
| 是否需要处方图？ | pending | prescriptionMap |
| 基肥、分蘖肥、穗肥的参数结构是否不同？ | pending | taskSubtype / parameters |
| 验收标准是什么？ | pending | acceptanceCriteria |

## 6.3 植保方案

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 植保算法需要哪些输入？ | pending | OperationPlan.parameters |
| 是否返回药剂、剂量、稀释倍数、作业窗口？ | pending | parameters / operationWindow |
| 是否需要天气窗口约束？ | pending | acceptanceCriteria / parameters |
| 杂草防治和病虫害防治参数是否不同？ | pending | taskSubtype / parameters |
| 是否需要安全间隔期？ | pending | OperationPlan.parameters |

---

# 7. 执行反馈核对

目标：确认执行系统或人工反馈能映射到 `Execution / ExecutionRecord / DeviceCommand`。

## 7.1 人工执行

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 人工执行需要上传哪些结果？ | pending | ExecutionRecord.resultPayload |
| 是否需要图片附件？ | pending | attachments |
| 是否需要实际作业面积和用量？ | pending | actualArea / actualAmount |
| 是否允许部分完成？ | pending | Execution.status / Feedback |

## 7.2 设备 / 无人机 / 第三方执行

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 外部执行系统是否有主动回调？ | pending | ExecutionStatusUpdated |
| 回调 payload 格式是什么？ | pending | ExecutionRecord.resultPayload |
| 一个 Execution 是否可能下发多个 DeviceCommand？ | pending | DeviceCommand |
| 是否需要轮询兜底？ | pending | ExecutionStatusPollingJob / EventRecord |
| 设备失败原因是否结构化？ | pending | failureReason / callbackPayload |

---

# 8. Evaluation / Feedback 核对

目标：确认执行评价和反馈需要的输入、指标和输出。

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 每类任务的评价指标是什么？ | pending | Evaluation.metrics |
| pass / warning / fail 是否足够？ | pending | Evaluation.result |
| FeedbackType 是否覆盖业务反馈？ | pending | Feedback.feedbackType |
| 哪些反馈必须进入人工复核？ | pending | Feedback.requiresReview / ReviewRequest |
| 反馈是否可能产生补救 TaskIntent？ | pending | FeedbackGeneratedHandler / TaskIntent |

---

# 9. ReviewRequest 核对

目标：确认人工复核页面需要展示和填写的字段。

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 复核人需要看到哪些上下文？ | pending | ReviewRequest.description / decisionPayload |
| decision 枚举 approve / reject / need_more_info / no_action / adjust 是否足够？ | pending | ReviewRequest.decision |
| adjust 是否需要结构化字段？ | pending | decisionPayload |
| 复核后是否可能直接触发生育期修正？ | pending | ReviewRequestResolvedHandler |
| 复核后是否可能生成多个 FarmingTask？ | pending | ReviewRequest / FarmingTask |

---

# 10. 前端页面字段核对

目标：确认主流程页面是否有数据模型未覆盖的展示字段。

待核对：

| 页面 | 需要核对的字段 |
|---|---|
| 计划创建页 | Farm / Field / PlantingPlan 必填字段 |
| 计划详情页 | 当前生育期、积温、任务概览、复核待办 |
| 农事项列表 | CalendarItem 状态、日期、生育期、来源 |
| 任务列表 | FarmingTask 状态、类型、时间窗口、优先级 |
| 任务详情 | OperationPlan、执行记录、反馈、复核状态 |
| 复核页 | ReviewRequest 上下文、决策、补充信息 |
| 执行反馈页 | ExecutionRecord 上传字段 |

---

# 11. 核对输出模板

每次核对后建议追加记录：

```text
日期：
参与人：
核对范围：
确认事项：
发现缺口：
需要更新的文档：
下一步：
```

---

# 12. 下一步

```text
1. 用本文档先和业务流程负责人核对计划创建、农事类型和人工复核。
2. 再和算法服务负责人核对生育期预测、农事日历、灌溉、施肥、植保接口。
3. 再和前端负责人核对页面字段和 API mock 需求。
4. 将确认结果回写到 docs/data-model.md。
5. 数据模型稳定后生成 docs/er-diagram.md。
```
