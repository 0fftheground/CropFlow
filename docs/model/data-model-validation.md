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
  fieldName
  area
  areaUnit
  boundaryAddress
  boundaryGeometry
```

核对结论：

| 问题                                       | 结论     | 影响                                     |
| ---------------------------------------- | ------ | -------------------------------------- |
| Farm 的经纬度表示农场中心点还是默认地块点？                 | 中心点    | Farm.longitude / Farm.latitude         |
| Field.boundaryAddress 是否只是文本，还是需要边界坐标数组？ | 边界坐标数组 | Field.boundaryGeometry；boundaryAddress 可保留文件地址或描述 |
| 第一版是否需要 Field 名称？                        | 需要     | Field.fieldName                        |
| 第一版是否需要地块面积？                             | 需要     | Field.area / Field.areaUnit / PlantingPlan.area |
| 第一版是否需要土壤类型、土壤肥力、前茬作物？                   | 不需要    | Field.metadata / PlantingPlan.metadata |

## 2.2 PlantingPlan

当前模型重点字段：

```text
cropName
varietyName
sowingDate
expectedHarvestDate
area
plantingMethod
transplantDate
transplantLeafAge
cropSeason
riceCroppingType
taskGenerationWindowDays
```

核对结论：

| 问题                               | 结论              | 影响                                 |
| -------------------------------- | --------------- | ---------------------------------- |
| 创建计划时是否必须录入品种 varietyName？       | 必须              | PlantingPlan.varietyName           |
| 播种日期是否一定有？是否存在移栽日期？              | 播种日期一定要有，存在移栽日期 | PlantingPlan.sowingDate / PlantingPlan.transplantDate |
| expectedHarvestDate 是用户输入还是系统预测？ | 系统预测            | PlantingPlan.expectedHarvestDate   |
| area 是计划种植面积还是地块面积快照？            | 地块面积            | PlantingPlan.area                  |
| 是否需要种植方式，例如直播、移栽？                | 需要              | PlantingPlan.plantingMethod        |
| 是否需要作物季次，例如早稻、晚稻？                | 需要              | PlantingPlan.cropSeason / stageCode |

---

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
PlantingPlan 保留品种名称、种植方式、播种日期、移栽日期、移栽叶龄等计划创建和算法高频共用字段。
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
```

## 3.3 stageCode

核对结论：

| 问题                           | 结论                  | 影响                            |
| ---------------------------- | ------------------- | ----------------------------- |
| 第一版固定 stageCode 列表是什么？       | 作物种类、生育期阶段及对应code编码 | data-model.md                 |
| 不同作物是否共用同一套 stageCode？       | 否                   | CropStageState / CalendarItem |
| 人工录入真实生育期是否只能选择固定 stageCode？ | 是                   | ActualStageRecorded           |

处理结果：

```text
data-model.md 已补充 StageCode 说明：第一版使用固定编码，不同作物不强制共用同一套编码；人工录入真实生育期只能选择当前作物可用的固定 stageCode。
完整 stageCode 清单仍需后续补充。
```

---

# 4. 农事日历算法核对

目标：确认农事日历接口返回内容能映射到 `CalendarItem`。

## 4.1 算法输入

核对结论：

| 问题                 | 结论                                                                                            | 影响                                 |
| ------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------- |
| 农事日历接口需要哪些计划字段？    | 播种日期、移栽日期(如有)、移栽时叶龄（如有）、稻作类型、品种名称、播种方式 | EventRecord.payload / CalendarItem |
| 是否依赖生育期预测结果？       | 依赖                                                                                            | sourceSnapshotId                   |
| 是否依赖地块面积、位置、品种？    | 依赖品种和种植位置                                                                               | PlantingPlan / Farm / Field        |
| 是否依赖历史管理习惯或地区农艺规则？ | 依赖                                                                                           | metadata / ruleResult              |

处理结果：

```text
农事日历算法高频依赖字段已补充到 PlantingPlan，例如 plantingMethod、transplantDate、transplantLeafAge、riceCroppingType。
历史管理习惯、地区农艺规则、未来天气、农事适宜度、推荐阈值等运行期或规则输入继续放在 PlantingPlan.metadata、EventRecord.payload 或算法调用 inputPayload 中。
```

## 4.2 算法输出

核对结论：

| 问题             | 结论                              | 影响                                     |
| -------------- | ------------------------------- | -------------------------------------- |
| 是否返回全周期农事项？    | 返回                              | CalendarItem                           |
| 是否返回建议开始和结束日期？ | 返回                              | suggestedStartDate / suggestedEndDate  |
| 是否返回对应生育期？     | 返回（也可不返回，生育期算法会返回存储）            | stageCode                              |
| 是否返回任务生成条件？    | 返回（不确定，农事日历生成的是通用的吧，条件生成不在该部分？） | CalendarItem.generationCondition |
| 是否返回优先级或风险等级？  | 否                               | CalendarItem      |
| 是否返回农事项说明和依据？  | 返回                              | CalendarItem.description               |

处理结果：

```text
CalendarItem 当前字段可以承接农事日历输出。
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
| generalFlowKey / chainKey 是否进入第一版表结构？ | 暂未确定                 | data-model.md 待定 |

处理结果：

```text
1-5 节已核对内容与当前核心设计无冲突。
已回写 data-model.md 的字段：Field.fieldName、Field.area、Field.areaUnit、Field.boundaryGeometry，以及 PlantingPlan 中生育期预测和农事日历高频依赖字段。
仍未回写为第一版字段的内容：generalFlowKey / chainKey，因结论仍为暂未确定。
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
| 植保算法需要哪些输入？ | 已核对：province、year、cultivation_system、cultivation_pattern、strategy；茎叶除草需要 rice_leaf_age / target；突发病虫防治需要 stage；杂草诊断还需要经纬度、栽培日期、杂草萌发日期、调查日期、weed_survey 等 | OperationPlan.parameters / EventRecord.payload / ExecutionRecord.resultPayload |
| 是否返回药剂、剂量、稀释倍数、作业窗口？ | 返回药剂、剂型、厂商、推荐用量、兑水量、复配提示；防治日期由诊断接口返回，不是 control_plan 接口返回 | OperationPlan.parameters / OperationPlan.operationWindowStart / OperationPlan.operationWindowEnd |
| 是否需要天气窗口约束？ | 当前接口未显式返回天气窗口；日期推荐可能隐含天气或适宜度判断 | OperationPlan.basis / parameters |
| 杂草防治和病虫害防治参数是否不同？ | 不同；外部可共用 `/api/get_control_plan` endpoint，但系统内部按 strategy / target / stage 区分 algorithmCode 和参数结构 | taskSubtype / OperationPlan.parameters |
| 是否需要安全间隔期？ | 当前接口未返回安全间隔期，第一版不新增独立字段 | OperationPlan.parameters |

处理结果：

```text
植保接口文档与当前核心设计总体一致。
soil_treatment_diagnosis 返回土壤封闭推荐日期和茎叶除草药前调查日期，归入后台日期维护或日历维护输入。
weed_treatment_diagnosis 在药前调查结果录入后调用，可返回重新调查日期或推荐防治日期与 control_plan_input。
/api/get_control_plan 返回最终防治处方，映射到 OperationPlan.parameters。
after_treatment_diagnosis 返回药后调查日期。
additional_treatment_diagnosis 返回无需补防、暂缓补防并补充调查、立即补防；立即补防必须人工确认后才能生成补防 TaskIntent / FarmingTask。
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
4. 将确认结果回写到 docs/model/data-model.md。
5. 数据模型稳定后生成 docs/model/er-diagram.md。
```
