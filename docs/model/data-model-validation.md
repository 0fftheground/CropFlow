# CropFlow Data Model Validation Checklist

> 本文档用于把 `docs/model/data-model.md` 与真实业务流程、外部算法服务、执行反馈和前端页面逐项核对。  
> 本文档不是新的数据模型，核对后如果发现字段或关系需要调整，应回写到 `docs/model/data-model.md`。

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

## 2.1 Farm / Field / Relation

当前模型：

```text
Farm:
  farmName
  boundaryWkt
  centroidLat
  centroidLon

Field:
  fieldName
  boundaryWkt
  centroidLat
  centroidLon
  areaHa

FarmFieldRelation:
  farmId
  fieldId
```

核对结论：

| 问题                                       | 结论     | 影响                                     |
| ---------------------------------------- | ------ | -------------------------------------- |
| Farm 的经纬度表示农场中心点还是默认地块点？                 | 中心点    | Farm.centroidLat / Farm.centroidLon    |
| Field.boundaryWkt 是否保留边界信息？ | 需要 | Field.boundaryWkt |
| 第一版是否需要 Field 名称？                    | 需要     | Field.fieldName      |
| 第一版是否需要地块面积？                             | 需要     | Field.areaHa |
| 第一版是否需要土壤类型、土壤肥力、前茬作物？                   | 不需要    | PlantingPlan.metadata |

处理结果：

```text
Farm 与 Field 的归属关系不再通过 Field.farmId 直接表达，而通过 FarmFieldRelation 维护。
Farm、Field 的字段口径优先对齐 ddl.sql 中的 agri_farm / agri_field。
```

## 2.2 PlantingPlan

当前模型重点字段：

```text
cropName
farmId
year
cultiTypeCode
varietyId
varietyName
sowingDate
expectedHarvestDate
plantingMethodCode
transplantDate
harvestDate
transplantLeafAge
taskGenerationWindowDays
```

核对结论：

| 问题                               | 结论              | 影响                                 |
| -------------------------------- | --------------- | ---------------------------------- |
| 创建计划时是否必须选择品种？                  | 必须              | PlantingPlan.varietyId / PlantingPlan.varietyName |
| PlantingPlan 是否需要 farmId？             | 需要              | PlantingPlan.farmId |
| 播种日期是否一定有？是否存在移栽日期？              | 播种日期一定要有，存在移栽日期 | PlantingPlan.sowingDate / PlantingPlan.transplantDate |
| expectedHarvestDate 是用户输入还是系统预测？ | 系统预测            | PlantingPlan.expectedHarvestDate   |
| 是否需要种植方式，例如直播、移栽？                | 需要              | PlantingPlan.plantingMethodCode        |
| 是否需要区分早稻、晚稻、中稻、再生稻等栽培类型？         | 需要              | PlantingPlan.cultiTypeCode / stageCode |
| PlantingPlan 是否直接保存 fieldId？         | 不直接保存           | PlantingPlanFieldRelation          |

---

## 2.3 RiceVariety

当前模型重点字段：

```text
name
approveYear
approveNo
approveRegion
suitableRegion
cultiTypeCode
subTypeCode
maturityCode
controlVariety
growthDays
compareDays
riceCode
```

处理结果：

```text
第一版新增独立 RiceVariety，对齐 agri_rice_variety。
PlantingPlan 创建时应选择 varietyId，并保留 varietyName 快照用于展示和历史追溯。
PlantingPlan.cultiTypeCode、PlantingPlan.plantingMethodCode、RiceVariety.subTypeCode 不直接存中文，而是引用 cf_code_dict.code。
当前业务值分别为：
1. cultiType：双季晚稻、早稻、一季晚稻、中稻、再生稻
2. plantingMethod：直播、抛秧、插秧
3. subType：籼、粳、籼粳交
```

# 3. 生育期预测算法核对

目标：确认 `StagePredictionSnapshot / CropStageState / CropThermalTimeState` 能否完整承接生育期算法输入输出。

## 3.1 算法输入

核对结论：

| 问题               | 结论                                                                                                                | 影响                                   |
| ---------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 生育期预测算法需要哪些计划字段？ | 品种名称、种植方式、播种日期、移栽日期 、移栽叶龄、气象数据（包含日期date、温度tmp） | StagePredictionSnapshot.inputPayload |
| 是否需要历史气象数据？      | 需要                                                                                                                | EventRecord / inputPayload           |
| 是否需要未来天气预报？      | 需要                                                                                                                | inputPayload                         |
| 是否需要品种积温阈值表？     | 需要                                                                                                                | thermalThresholds                    |
| 是否需要地理位置经纬度？     | 需要                                                                                                                | Farm / Field / inputPayload          |

处理结果：

```text
PlantingPlan 保留品种引用、品种名称快照、种植方式 code、播种日期、移栽日期、移栽叶龄、栽培类型 code 等计划创建和算法高频共用字段。
PlantingPlan 保留 farmId，对齐 agri_crop_season 的农场归属语义。
PlantingPlan 不再直接保存 fieldId，计划与地块关系通过 PlantingPlanFieldRelation 维护。
PlantingPlanFieldRelation 只负责保存计划与地块关联关系。
cropSeason / riceCroppingType 与 cultiTypeCode 语义重复，第一版不再单独建字段。
基础业务枚举统一通过 cf_code_dict 维护；cf_code_dict 的结构和初始化数据沿用 agri_code_dict，业务表只存原始 code。
气象数据、品种积温阈值表、实际记录生育期等算法运行期输入继续放在 StagePredictionSnapshot.inputPayload / thermalThresholds 或 EventRecord.payload。
审定亚种、审定区域、对照品种、生育期差距、返青天数等旧版本曾记录的扩展字段，当前 3、4 节未明确需要，第一版先放 PlantingPlan.metadata 或 StagePredictionSnapshot.inputPayload，开发时再判断是否结构化。
```

## 3.2 算法输出

核对结论：

| 问题                        | 结论                                | 影响                                        |
| ------------------------- | --------------------------------- | ----------------------------------------- |
| stageTimeline 的结构是什么？     | {<br>各生育期节点:日期,<br>种植计划id：id<br>} | StagePredictionSnapshot.stageTimeline     |
| thermalThresholds 的结构是什么？ | {<br>各生育期节点:日期,<br>种植计划id：id<br>} | StagePredictionSnapshot.thermalThresholds |
| 是否返回当前阶段，还是只返回预测时间线？      | 只返回预测时间线                          | CropStageState                            |
| 是否返回置信度或风险提示？             | 否                                 | 不需要新增字段                            |
| 是否需要记录算法版本？               | 否                                 | StagePredictionSnapshot.algorithmVersion 可为空 |

处理结果：

```text
StagePredictionSnapshot.algorithmVersion 保留为可空字段。
外部算法当前不返回版本时可以为空，但系统仍保留 algorithmCode 用于标识调用的算法接口。
人工录入真实生育期时，先修正 CropStageState.currentStageCode / effectiveDate；CropThermalTimeState 仍按 sowingDate 持续累计，不因人工反馈重新起算。
```

## 3.3 stageCode

核对结论：

| 问题                           | 结论                  | 影响                            |
| ---------------------------- | ------------------- | ----------------------------- |
| 第一版固定 stageCode 列表是什么？       | 作物种类、生育期阶段及对应code编码 | data-model.md                 |
| 不同作物是否共用同一套 stageCode？       | 否                   | CropStageState / CalendarItem |
| 人工录入真实生育期是否只能选择固定 stageCode？ | 是                   | ActualStageRecorded           |
| CalendarItem / FarmingTask 是否都必须有 stageCode？ | 否，仅阶段相关任务需要 | CalendarItem / FarmingTask |

处理结果：

```text
data-model.md 已补充 StageCode 说明：第一版使用固定编码，不同作物不强制共用同一套编码；人工录入真实生育期只能选择当前作物可用的固定 stageCode。
CalendarItem.stageCode / FarmingTask.targetStageCode 改为可空，仅在阶段驱动任务、算法明确返回阶段上下文或复核明确指定目标阶段时填写。
完整 stageCode 清单仍需后续补充。
```

---

# 4. 农事日历算法核对

目标：确认农事日历接口返回内容能映射到 `CalendarItem`。

## 4.1 算法输入

核对结论：

| 问题                 | 结论                                                                                            | 影响                                 |
| ------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------- |
| 农事日历接口需要哪些计划字段？    | 播种日期、移栽日期(如有)、移栽时叶龄（如有）、栽培类型、品种名称、播种方式 | EventRecord.payload / CalendarItem |
| 是否依赖生育期预测结果？       | 依赖                                                                                            | sourceSnapshotId                   |
| 是否依赖地块面积、位置、品种？    | 依赖品种和种植位置                                                                               | PlantingPlan / Farm / Field        |
| 是否依赖历史管理习惯或地区农艺规则？ | 依赖                                                                                           | metadata / ruleResult              |

处理结果：

```text
农事日历算法高频依赖字段已补充到 PlantingPlan，例如 cultiTypeCode、plantingMethodCode、transplantDate、transplantLeafAge。
历史管理习惯、地区农艺规则、未来天气、农事适宜度、推荐阈值等运行期或规则输入继续放在 PlantingPlan.metadata、EventRecord.payload 或算法调用 inputPayload 中。
```

## 4.2 算法输出

核对结论：

| 问题             | 结论                              | 影响                                     |
| -------------- | ------------------------------- | -------------------------------------- |
| 是否返回全周期农事项？    | 返回                              | CalendarItem                           |
| 是否返回建议开始和结束日期？ | 返回                              | suggestedStartDate / suggestedEndDate  |
| 是否返回对应生育期？     | 可返回，也允许不返回            | stageCode                              |
| 是否返回任务生成条件？    | 返回（不确定，农事日历生成的是通用的吧，条件生成不在该部分？） | CalendarItem.generationCondition |
| 是否返回优先级或风险等级？  | 否                               | CalendarItem      |
| 是否返回农事项说明和依据？  | 返回                              | CalendarItem.description               |

处理结果：

```text
CalendarItem 当前字段可以承接农事日历输出。
stageCode 允许为空，不要求所有农事项都携带阶段编码。
generationCondition 如算法暂不返回，可先由 Task Module 根据 CalendarItem 和任务生成窗口生成。
```

---

# 5. 农事类型核对

目标：确认 `taskCategory + taskSubtype` 是否足够覆盖第一版农事类型。

当前大类：

```text
irrigation
fertilization
plant_protection
field_management
field_inspection
soil_preparation
planting
material_management
harvest
manual
```

说明：

```text
遥感监测按业务方向独立分工，但第一版数据模型不新增 remote_sensing taskCategory。
缺苗识别、长势监测等遥感监测农事先归入 field_inspection，并通过 taskSubtype 区分。
```

当前建议子类：

```text
fertilization.base
fertilization.tillering
fertilization.panicle
fertilization.soil_test
fertilization.prescription_generation
fertilization.panicle_variable_prescription
fertilization.panicle_fertilizer_effect_check
fertilization.ratoon_seedling_fertilizer
fertilization.ratoon_bud_fertilizer
plant_protection.weed_control
plant_protection.pest_control
plant_protection.disease_control
plant_protection.sealing_stage_disease_pest_survey
plant_protection.sealing_stage_disease_pest_control
plant_protection.sudden_disease_pest_survey
plant_protection.sudden_disease_pest_control
plant_protection.heading_stage_disease_pest_survey
plant_protection.heading_stage_disease_pest_control
plant_protection.booting_stage_disease_pest_survey
plant_protection.booting_stage_disease_pest_control
plant_protection.service_effect_evaluation
field_management.service_area_setup
soil_preparation.rotary_tillage
soil_preparation.land_leveling
planting.transplanting
material_management.pesticide_stock_in
material_management.fertilizer_stock_in
irrigation.device_installation
irrigation.water_level_setup
harvest.combine_harvest
harvest.pre_harvest_drain
harvest.ratoon_dry_field
harvest.ratoon_harvest
field_inspection.field_patrol
field_inspection.missing_seedling_detection
field_inspection.growth_monitoring
field_inspection.lodging_detection
```

核对结论：

| 问题                         | 结论                   | 影响                          |
| -------------------------- | -------------------- | --------------------------- |
| 施肥子类是否需要区分基肥、分蘖肥、穗肥以外的类型？  | 是                    | taskSubtype                 |
| 植保是否只分杂草防治、虫害防治、病害防治？      | 只有草害和病虫害两类吧          | taskSubtype                 |
| 服务区 / 敏感区划分是否应归入整地？           | 不归入整地，归入 field_management | taskCategory / taskSubtype  |
| 旱整地、移栽、药剂和肥料入库、缺苗识别是否已覆盖？ | 已补充到流程矩阵和建议 subtype | taskCategory / taskSubtype  |
| 是否保留送嫁肥？                    | 暂不保留                 | taskSubtype / workflowKey   |
| 病虫调查和病虫防治是否是同一个农事？        | 不是，调查和防治拆成两个 FarmingTask | workflowKey / taskSubtype   |
| 调查时间推荐算法是否属于调查农事流程？        | 不属于，由后台定时任务调用并新建或修改调查日期 | Background Job / CalendarItem |
| 施肥效果抽查是否适用于所有施肥？           | 不是，仅穗肥后抽查            | taskSubtype                 |
| 再生季农事是否作为一个整体流程？           | 不作为整体流程，发苗肥、促芽肥、晒田、收割分别建农事 | taskSubtype / trigger condition |
| 整地是否需要旋耕、耙田、平田等细类？         | 需要细分                 | taskSubtype                 |
| 收割是否需要人工收割、机械收割、分批收割？      | 不区分                  | taskSubtype                 |
| 巡田是否只是人工任务，还是也可能由无人机或设备触发？ | 可能触发无人机（需要人工确认或天气判定） | executionMode / taskSubtype |
| 药剂 / 肥料入库是否需要独立库存表？        | 需要                    | InventoryItem / InventoryTransaction |
| 移栽作业是否需要 OperationPlan？         | 不需要，只记录执行结果和实际移栽日期 | FarmingTask / ExecutionRecord / PlantingPlan |
| 病虫害防治推荐算法是否共用？             | 不共用，按不同病虫害类别调用不同算法 | OperationPlan.algorithmCode |
| 缺苗识别是否自动触发补苗？              | 不自动触发，由人工判断        | ReviewRequest / TaskIntent |
| 长势监测异常是否自动触发归因分析？          | 不自动触发，由人工判断        | ReviewRequest / TaskIntent |
| generalFlowKey / chainKey 是否进入第一版表结构？ | workflow 文档已定义，是否全量入第一版表结构仍待单独确认 | data-model.md 待定 |
| 运行期触发的新任务是否需要记录前置任务 ID？ | 需要，并扩展到 CalendarItem / TaskIntent / FarmingTask | CalendarItem.parentTaskId / TaskIntent.parentTaskId / FarmingTask.parentTaskId |
| 运行期触发的新任务是否需要记录来源执行记录？ | 需要，并扩展到 CalendarItem / TaskIntent / FarmingTask | CalendarItem.sourceExecutionRecordId / TaskIntent.sourceExecutionRecordId / FarmingTask.sourceExecutionRecordId |

处理结果：

```text
1-5 节已核对内容与当前核心设计无冲突。
已回写 data-model.md 的字段：Field.fieldName、Field.area、Field.areaUnit、Field.boundaryGeometry，以及 PlantingPlan 中生育期预测和农事日历高频依赖字段。
仍未回写为第一版字段的内容：generalFlowKey / chainKey 是否全量入表，结论仍需单独确认。
运行期触发的新农事项、任务建议和正式任务应至少能追溯 parentTaskId 和 sourceExecutionRecordId。
```

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

核对结论：

| 问题 | 结论 | 影响 |
|---|---|---|
| 植保算法需要哪些输入？ | 已核对：province、year、cultivation_system、cultivation_pattern、strategy；茎叶除草需要 rice_leaf_age / target；突发病虫防治需要 stage；杂草诊断还需要经纬度、栽培日期、杂草萌发日期、调查日期、weed_survey 等 | TaskIntent.ruleResult / OperationPlan.parameters / EventRecord.payload / ExecutionRecord.resultPayload |
| 是否返回药剂、剂量、稀释倍数、作业窗口？ | 返回药剂、剂型、厂商、推荐用量、兑水量；防治日期、补防日期和药害缓解建议时间窗均可由杂草诊断接口直接返回 | TaskIntent.ruleResult / OperationPlan.parameters / OperationPlan.operationWindowStart / OperationPlan.operationWindowEnd |
| 是否需要天气窗口约束？ | 当前接口未显式返回天气窗口；日期推荐可能隐含天气或适宜度判断 | OperationPlan.basis / parameters |
| 杂草防治和病虫害防治参数是否不同？ | 不同；当前已确认的杂草主线 3 个诊断接口直接返回处方，病虫方向是否保留共用方案接口需后续单独确认 | taskSubtype / OperationPlan.parameters |
| 是否需要安全间隔期？ | 当前接口未返回安全间隔期，第一版不新增独立字段 | OperationPlan.parameters |

处理结果：

```text
植保接口文档与当前核心设计总体一致。
soil_treatment_diagnosis 返回土壤封闭推荐日期和防治方案；如该链路要求人工审核，则先进入 TaskIntent / ReviewRequest，审核通过后再生成正式 FarmingTask，并为其创建 OperationPlan。
weed_survey_date_diagnosis 返回茎叶除草药前调查日期，归入后台日期维护输入。
weed_treatment_diagnosis 在药前调查结果录入后调用；重新调查日期映射到 CalendarItem，推荐防治日期与防治方案先落 TaskIntent / ReviewRequest，审核通过后生成正式 FarmingTask，并为该任务创建 OperationPlan。
after_treatment_diagnosis 返回两个调查日期：安全性调查日期和防效兼安全性调查日期，均映射到调查类 CalendarItem。
injury_mitigation_diagnosis 返回 need_mitigation、measures 和 recommended_mitigation_date；药害缓解建议在审核通过前先保存在 TaskIntent.ruleResult / ReviewRequest.decisionPayload，审核通过后再生成正式 FarmingTask。
additional_treatment_diagnosis 返回无需补防、需缓解药害、待药害缓解后补充调查、立即补防等分支；additional_survey_date 和 service_effect_evaluation_date 继续映射 CalendarItem，补防或药害缓解建议先进入 TaskIntent / ReviewRequest，审核通过后生成正式 FarmingTask。
外部 endpoint 可以共用，但系统内部仍按 strategy / target / stage 区分算法语义。
```

---

# 7. 执行反馈核对

目标：确认执行系统或人工反馈能映射到 `Execution / ExecutionRecord / DeviceCommand`。

## 7.1 人工执行

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 人工执行需要上传哪些结果？ | 需要根据不同的作业类型区分 | ExecutionRecord.resultPayload |
| 是否需要图片附件？ | pending | attachments |
| 是否需要实际作业面积和用量？ | pending | actualArea / actualAmount |
| 是否允许部分完成？ | pending | Execution.status / Feedback |

当前对杂草防治链路已补充冻结结论：

```text
1. 杂草防治第一版执行结果仅考虑人工录入。
2. 第一版不要求图片附件、实际面积和实际用量。
3. 第一版不支持 partial。
4. 药后调查链路触发依赖执行完成时间；调查类任务在 ExecutionRecord.resultPayload 中至少要能记录调查日期及 weed_diagnosis_api.md 所需调查结果。
```

## 7.2 设备 / 无人机 / 第三方执行

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 外部执行系统是否有主动回调？ | pending | ExecutionStatusUpdated |
| 回调 payload 格式是什么？ | pending | ExecutionRecord.resultPayload |
| 一个 Execution 是否可能下发多个 DeviceCommand？ | pending | DeviceCommand |
| 是否需要轮询兜底？ | pending | ExecutionStatusPollingJob / EventRecord |
| 设备失败原因是否结构化？ | pending | failureReason / callbackPayload |

当前对杂草防治链路已补充冻结结论：

```text
杂草防治第一版不接设备回调或第三方执行系统回传；相关回调、轮询和 DeviceCommand 细节后续按其他农事项统一扩展。
```

---

# 8. Evaluation / Feedback 核对

目标：确认执行评价和反馈需要的输入、指标和输出。

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 每类任务的评价指标是什么？ | pending | Evaluation.metrics |
| pass / warning / fail 是否足够？ | pending | Evaluation.result |
| 是否需要区分算法评估、人评估等来源？ | 需要 | Evaluation.sourceType / Evaluation.sourceId |
| FeedbackType 是否覆盖业务反馈？ | pending | Feedback.feedbackType |
| 是否需要区分反馈是算法、人还是外部系统产生？ | 需要 | Feedback.sourceType / Feedback.sourceId |
| 哪些反馈必须进入人工复核？ | pending | Feedback.requiresReview / ReviewRequest |
| 反馈是否可能产生补救 TaskIntent？ | pending | FeedbackGeneratedHandler / TaskIntent |

当前对杂草防治链路已补充冻结结论：

```text
1. 运行期调查或诊断返回新的农事建议、补防建议、药害缓解建议时，先创建 TaskIntent，再进入 ReviewRequest。
2. 只有审核通过后，编排器才创建正式 FarmingTask；如果该任务需要执行方案，再为该正式任务创建 OperationPlan。
3. 农户反馈服务评价默认是一个正式 FarmingTask。
```

---

# 9. ReviewRequest 核对

目标：确认人工复核页面需要展示和填写的字段。

待核对：

| 问题 | 结论 | 影响 |
|---|---|---|
| 复核人需要看到哪些上下文？ | 已补充：至少包含算法来源、触发调查记录、建议任务类型、建议时间窗、建议处方/措施、推荐日期和拒绝理由输入位；结构化部分进入 decisionPayload.contextRefs | ReviewRequest.description / decisionPayload |
| decision 枚举 approve / reject / need_more_info / no_action / adjust 是否足够？ | pending | ReviewRequest.decision |
| adjust 是否需要结构化字段？ | 需要，至少保留 contextRefs / adjustments / reason | decisionPayload |
| 复核后是否可能直接触发生育期修正？ | pending | ReviewRequestResolvedHandler |
| 复核后是否可能生成多个 FarmingTask？ | pending | ReviewRequest / FarmingTask |
| 复核页是否要展示前置任务和触发调查记录？ | 需要，并建议从 decisionPayload.contextRefs 读取 | ReviewRequest.description / decisionPayload |

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
4. 将确认结果回写到 docs/model/data-model.md。
5. 数据模型稳定后生成 docs/model/er-diagram.md。
```
