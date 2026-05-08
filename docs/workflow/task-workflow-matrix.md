# CropFlow Task Workflow Matrix

> 本文档基于 `docs/workflow/total-workflow.pdf` 整理农事项、执行步骤、算法服务、人工录入点和条件分支。  
> PDF 当前是图片流程图，本文先按可识别节点结构化整理；标记为 `needs_check` 的内容需要后续和业务/算法负责人复核。

---

# 1. 建模原则

```text
1. 本文档不是工作流引擎设计。
2. workflowKey 表示具体农事项或后台任务。
3. generalFlowKey 表示可复用的业务通用流程。
4. chainKey 表示跨农事项链路。
5. CalendarItem 仍然是预备农事项，不是正式任务。
6. FarmingTask 仍然是正式任务，是 Execution Module 的入口。
7. OperationPlan 仍然是具体作业方案 / 处方方案。
8. 分支结果优先生成 TaskIntent / ReviewRequest / OperationPlan / FarmingTask，不新增 Recommendation。
9. MVP 阶段不实现通用工作流引擎，但数据模型需要能追溯 workflowKey / workflowStepKey / generalFlowKey / chainKey / parentTaskId。
```

---

# 2. 字段说明

通用流程步骤表使用以下字段：

| 字段 | 说明 |
|---|---|
| generalFlowKey | 通用业务流程编码 |
| stepId | 通用流程内步骤 ID |
| stepName | 步骤名称 |
| stepType | calendar / algorithm / manual_task / input / execution / feedback / policy / review / end |
| trigger | 触发来源 |
| inputData | 需要的输入 |
| algorithmService | 调用的算法服务 |
| outputData | 输出结果 |
| createdEntity | 生成或更新的对象 |
| nextStep | 默认下一步 |
| notes | 备注 |

具体农事项表使用以下字段：

| 字段 | 说明 |
|---|---|
| workflowKey | 具体农事项流程编码 |
| taskCategory | 农事大类 |
| taskSubtype | 农事子类 |
| generalFlowKey | 复用的通用流程；无则为 none |
| trigger | 触发条件 |
| specificLogic | 该农事项独有逻辑 |
| output | 主要输出 |
| notes | 备注或待核对点 |

分支规则表使用以下字段：

| 字段 | 说明 |
|---|---|
| branchId | 分支规则 ID |
| sourceKey | 来源 workflowKey / generalFlowKey / chainKey |
| fromStepId | 来源步骤 |
| conditionType | threshold / result / risk / manual_decision / execution_result / time_window |
| conditionDescription | 分支条件说明 |
| targetKey | 目标 workflowKey / generalFlowKey / chainKey |
| output | 分支输出对象 |

---

# 3. 农事项流程总览

| workflowKey | taskCategory | taskSubtype | generalFlowKey | 流程名称 | 主要算法或服务 | 备注 |
|---|---|---|---|---|---|---|
| WF_SERVICE_AREA | field_management | service_area_setup | none | 服务区 / 敏感区划分 | fieldExtractionAlgorithm | 地块/服务区数字化，不属于整地 |
| WF_IRRIGATION_DEVICE | irrigation | device_installation | none | 灌溉执行硬件设备安装与测试 | none | 种植前准备 |
| WF_PESTICIDE_STOCK_IN | material_management | pesticide_stock_in | GENERAL_MATERIAL_STOCK_IN | 药剂入库 | none | 支撑植保方案可用药剂 |
| WF_FERTILIZER_STOCK_IN | material_management | fertilizer_stock_in | GENERAL_MATERIAL_STOCK_IN | 肥料入库 | none | 支撑施肥处方和施肥作业 |
| WF_SOIL_TEST | fertilization | soil_test | none | 采土与测土 | samplingPointPlanningAlgorithm / soilInterpolationAlgorithm | 支撑施肥处方 |
| WF_FERTILIZER_PRESCRIPTION | fertilization | prescription_generation | none | 施肥处方生成 | fertilizerPrescriptionAlgorithm | 生成施肥处方 |
| WF_DRY_LAND_PREPARATION | soil_preparation | rotary_tillage | none | 旱整地 / 旋耕整地 | none | 种植前准备 |
| WF_LAND_LEVELING | soil_preparation | land_leveling | none | 水整地 / 平地效果评估 | landLevelingEvaluationAlgorithm | 水整地后评估 |
| WF_WATER_LEVEL_SETUP | irrigation | water_level_setup | none | 水位计 / 水位尺布设 | waterLevelDevicePlacementAlgorithm | 水整地 / 平地效果评估完成后 |
| WF_TRANSPLANTING | planting | transplanting | none | 移栽 | none | 非直播时存在 |
| WF_SOIL_SEAL_WEED | plant_protection | soil_sealing_weed_control | GENERAL_PLANT_PROTECTION_CONTROL | 土壤封闭除草 | soilTreatmentDiagnosisAlgorithm / controlPlanAlgorithm | FarmingTask 不调用调查日期推荐算法；后台可用 soil_treatment_diagnosis 维护土壤封闭日期 |
| WF_STEM_LEAF_WEED | plant_protection | stem_leaf_weed_control | GENERAL_PLANT_PROTECTION_SURVEY + GENERAL_PLANT_PROTECTION_CONTROL | 茎叶除草 | soilTreatmentDiagnosisAlgorithm / weedTreatmentDiagnosisAlgorithm / controlPlanAlgorithm / afterTreatmentDiagnosisAlgorithm / additionalTreatmentDiagnosisAlgorithm | 药前调查日期由 soil_treatment_diagnosis 返回 |
| WF_DISEASE_PEST_SEALING_SURVEY | plant_protection | sealing_stage_disease_pest_survey | GENERAL_PLANT_PROTECTION_SURVEY | 封行病虫调查 | diseaseControlRecommendationAlgorithm / pestControlRecommendationAlgorithm / categorySpecificControlAlgorithm | 调查不一定触发防治 |
| WF_DISEASE_PEST_SEALING_CONTROL | plant_protection | sealing_stage_disease_pest_control | GENERAL_PLANT_PROTECTION_CONTROL | 封行病虫防治 | none | 纯打药作业，消费调查后生成的 OperationPlan |
| WF_DISEASE_PEST_SUDDEN_SURVEY | plant_protection | sudden_disease_pest_survey | GENERAL_PLANT_PROTECTION_SURVEY | 突发病虫调查 | diseaseControlRecommendationAlgorithm / pestControlRecommendationAlgorithm / categorySpecificControlAlgorithm | 调查不一定触发防治 |
| WF_DISEASE_PEST_SUDDEN_CONTROL | plant_protection | sudden_disease_pest_control | GENERAL_PLANT_PROTECTION_CONTROL | 突发病虫防治 | none | 纯打药作业，消费调查后生成的 OperationPlan |
| WF_DISEASE_PEST_HEADING_SURVEY | plant_protection | heading_stage_disease_pest_survey | GENERAL_PLANT_PROTECTION_SURVEY | 齐穗病虫调查 | diseaseControlRecommendationAlgorithm / pestControlRecommendationAlgorithm / categorySpecificControlAlgorithm | 调查不一定触发防治 |
| WF_DISEASE_PEST_HEADING_CONTROL | plant_protection | heading_stage_disease_pest_control | GENERAL_PLANT_PROTECTION_CONTROL | 齐穗病虫防治 | none | 纯打药作业，消费调查后生成的 OperationPlan |
| WF_DISEASE_PEST_BOOTING_SURVEY | plant_protection | booting_stage_disease_pest_survey | GENERAL_PLANT_PROTECTION_SURVEY | 破口病虫调查 | diseaseControlRecommendationAlgorithm / pestControlRecommendationAlgorithm / categorySpecificControlAlgorithm | 调查不一定触发防治 |
| WF_DISEASE_PEST_BOOTING_CONTROL | plant_protection | booting_stage_disease_pest_control | GENERAL_PLANT_PROTECTION_CONTROL | 破口病虫防治 | none | 纯打药作业，消费调查后生成的 OperationPlan |
| WF_BASE_FERTILIZER | fertilization | base | GENERAL_FERTILIZATION_OPERATION | 施基肥 | farmingRuleLibrary | 施基肥范围后续由专门农事规则库维护 |
| WF_TILLERING_FERTILIZER | fertilization | tillering | GENERAL_FERTILIZATION_OPERATION | 施分蘖肥 | none / prescription | BBCH21-22 |
| WF_PANICLE_VARIABLE_PRESCRIPTION | fertilization | panicle_variable_prescription | GENERAL_GROWTH_MONITORING | 穗肥前长势监测与变量处方图 | growthMonitoringAlgorithm / panicleVariablePrescriptionAlgorithm | 施穗肥前单独执行 |
| WF_PANICLE_FERTILIZER | fertilization | panicle | GENERAL_FERTILIZATION_OPERATION | 施穗肥 | panicleVariablePrescriptionAlgorithm | BBCH41-42 |
| WF_MISSING_SEEDLING_DETECTION | field_inspection | missing_seedling_detection | none | 缺苗识别 | missingSeedlingDetectionAlgorithm | 遥感；低空面状 RGB，时间与移栽同步 |
| WF_GROWTH_MONITOR | field_inspection | growth_monitoring | GENERAL_GROWTH_MONITORING | 长势监测 | ndviGrowthMonitoringAlgorithm / abnormalCauseRecognitionAlgorithm | 不包含稳肥变量推荐和产量预测 |
| WF_PANICLE_FERTILIZER_EFFECT_CHECK | fertilization | panicle_fertilizer_effect_check | GENERAL_GROWTH_MONITORING | 穗肥施肥效果抽查 | growthMonitoringAlgorithm | 穗肥后 7-10 天，不适用于所有施肥 |
| WF_PLANT_PROTECTION_SERVICE_EVALUATION | plant_protection | service_effect_evaluation | none | 植保服务效果评估收集 | none | 与收割前晒田分开 |
| WF_PRE_HARVEST_DRAIN | harvest | pre_harvest_drain | none | 收割前晒田 | none | 收割前 12 天 |
| WF_HARVEST | harvest | harvest | none | 收割 | none | 不细分人工/机械 |
| WF_LODGING_DETECTION | field_inspection | lodging_detection | none | 倒伏识别 | lodgingDetectionAlgorithm | 触发任务状态更新 |
| WF_RATOON_SEEDLING_FERTILIZER | fertilization | ratoon_seedling_fertilizer | GENERAL_FERTILIZATION_OPERATION | 再生季施发苗肥 | none / prescription | 仅稻作类型为再生稻时存在 |
| WF_RATOON_BUD_FERTILIZER | fertilization | ratoon_bud_fertilizer | GENERAL_FERTILIZATION_OPERATION | 再生季施促芽肥 | none / prescription | 仅稻作类型为再生稻时存在 |
| WF_RATOON_DRY_FIELD | harvest | ratoon_dry_field | none | 再生季晒田 | none | 仅稻作类型为再生稻时存在 |
| WF_RATOON_HARVEST | harvest | ratoon_harvest | none | 再生季收割 | none | 仅稻作类型为再生稻时存在 |

---

# 3.1 后台任务：调查日期推荐

以下逻辑不属于农事项，也不生成 FarmingTask。后台定时任务调用调查日期推荐算法，并新建或修改调查类 CalendarItem。

| jobKey | 调用算法 | 维护对象 | 说明 |
|---|---|---|---|
| SurveyDateRecommendationJob | soilTreatmentDiagnosisAlgorithm | 土壤封闭 CalendarItem、茎叶除草药前调查 CalendarItem | 调用 `/api/soil_treatment_diagnosis`，使用土壤封闭推荐日期和推荐茎叶除草药前调查日期 |
| SurveyDateRecommendationJob | diseasePestSurveyDateRecommendationAlgorithm | 病虫调查 CalendarItem | 按 stage / subtype 维护封行、突发、齐穗、破口等病虫调查日期 |
| SurveyDateRecommendationJob | pestSurveyDateRecommendationAlgorithm | 虫害调查 CalendarItem | 如虫害调查与病虫调查需要合并，后续统一接口 |

```text
1. 调查日期推荐算法由 Background Job Center 周期性调用。
2. 算法结果只负责新建或更新调查类 CalendarItem。
3. 调查农事本身只从已有调查日期开始，执行调查和结果录入。
4. 调查结果录入后，才调用防治推荐算法生成防治日期和防治方案。
5. 草害调查和虫害调查的推荐日期都由后台任务获取，不在调查 FarmingTask 内调用。
6. 茎叶除草药前调查日期由 soil_treatment_diagnosis 接口返回。
7. 土壤封闭除草 FarmingTask 不调用调查日期推荐算法；soil_treatment_diagnosis 属于后台日期维护或日历维护输入。
```

---

# 4. 通用流程矩阵

## 4.1 GENERAL_PLANT_PROTECTION_SURVEY：植保调查

适用：杂草调查、封行病虫调查、突发病虫调查、齐穗病虫调查、破口病虫调查。

| stepId | stepName | stepType | trigger | inputData | algorithmService | outputData | createdEntity | nextStep | notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 调查任务生成 | manual_task | 调查类 CalendarItem 到期 | Field / 调查日期 / surveyType | none | 调查 FarmingTask | FarmingTask | S2 | 调查日期由 SurveyDateRecommendationJob 维护 |
| S2 | 调查执行 | manual_task | 调查任务到期 | Field / surveyType | none | 调查结果待录入 | Execution / ExecutionRecord | S3 | 可人工调查，也可结合遥感或设备结果 |
| S3 | 调查结果录入 | input | 调查完成 | 杂草密度 / 草相 / 病虫类型 / 发生程度 | none | 调查结果 | ExecutionRecord / FieldConditionReported | S4 |  |
| S4 | 防治推荐 | algorithm | 调查结果录入 | 调查结果 / 天气 / Field / 防治阈值 | weedTreatmentDiagnosisAlgorithm / diseaseControlRecommendationAlgorithm / pestControlRecommendationAlgorithm / categorySpecificControlAlgorithm | no_action / 重新调查 / 需防治 / 防治日期 / 防治方案输入 | TaskIntent / OperationPlan / CalendarItem | BRANCH | 杂草诊断可返回重新调查日期或 control_plan_input；病虫害按病害、虫害、发生类别分别调用，不视为共用算法 |

## 4.2 GENERAL_PLANT_PROTECTION_CONTROL：植保防治

适用：土壤封闭除草、茎叶除草、病虫防治、补防。

| stepId | stepName | stepType | trigger | inputData | algorithmService | outputData | createdEntity | nextStep | notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 防治任务生成 | policy | OperationPlan active / 防治日期到期 | OperationPlan / 防治日期 / 防治方案 | none | 防治 FarmingTask | FarmingTask | S2 | 防治推荐算法不在本流程调用 |
| S2 | 作业前保持水层 | manual_task | 防治作业前 | 水层要求 / OperationPlan | none | 水层确认 | ExecutionRecord | S3 | 施肥和打药统一作业流程 |
| S3 | 防治作业 | execution | 水层确认 | OperationPlan | none / external | 作业结果 | Execution / ExecutionRecord | S4 |  |
| S4 | 作业后保持水层 | manual_task | 作业完成 | OperationPlan | none | 水层管理结果 | ExecutionRecord | S5 |  |
| S5 | 农事作业反馈 | feedback | 作业完成 | ExecutionRecord | none | Feedback | Feedback | END_COMPLETED |  |

## 4.3 GENERAL_FERTILIZATION_OPERATION：施肥作业

适用：基肥、分蘖肥、穗肥、再生季发苗肥、再生季促芽肥。

| stepId | stepName | stepType | trigger | inputData | algorithmService | outputData | createdEntity | nextStep | notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 施肥任务生成 | manual_task | 施肥类 CalendarItem 到期 | PlantingPlan / OperationPlan / taskSubtype | none | 施肥 FarmingTask | FarmingTask | S2 | 施基肥范围由农事规则库维护 |
| S2 | 作业前保持水层 | manual_task | 施肥作业前 | 水层要求 | none | 水层确认 | ExecutionRecord | S3 | 施肥和打药统一作业流程 |
| S3 | 施肥作业 | execution | 水层确认 | OperationPlan | none / external | 施肥结果 | Execution / ExecutionRecord | S4 |  |
| S4 | 作业后保持水层 | manual_task | 施肥完成 | OperationPlan | none | 水层管理结果 | ExecutionRecord | S5 |  |
| S5 | 农事作业反馈 | feedback | 作业完成 | ExecutionRecord | none | Feedback | Feedback | END_COMPLETED |  |

## 4.4 GENERAL_GROWTH_MONITORING：长势监测

适用：普通长势监测、穗肥前长势监测、穗肥效果抽查。

| stepId | stepName | stepType | trigger | inputData | algorithmService | outputData | createdEntity | nextStep | notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 长势监测任务生成 | manual_task | 监测类 CalendarItem 到期 | Field / 时间窗口 / monitorPurpose | none | 监测 FarmingTask | FarmingTask | S2 | monitorPurpose 区分普通监测、穗肥前、穗肥后抽查 |
| S2 | 影像上传 | input | 航测完成 | 多光谱影像 / RGB 影像 | none | 影像文件 | ExecutionRecord | S3 |  |
| S3 | 影像拼接 | algorithm | 影像上传 | 影像文件 | imageStitchingAlgorithm | 拼接影像 | ExecutionRecord | S4 |  |
| S4 | 长势检测 | algorithm | 拼接影像就绪 | 拼接影像 | growthMonitoringAlgorithm / ndviGrowthMonitoringAlgorithm | 长势结果 | ExecutionRecord / FieldConditionReported | S5 |  |
| S5 | 结果任务状态更新 | feedback | 算法完成 | 长势结果 | none | 状态更新 | FarmingTask | END_OR_EXTENSION | 普通监测可继续异常点位和归因分析 |

## 4.5 GENERAL_MATERIAL_STOCK_IN：物料入库

支撑流程，不属于农事执行流程。适用：药剂入库、肥料入库。

| stepId | stepName | stepType | trigger | inputData | algorithmService | outputData | createdEntity | nextStep | notes |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 入库任务 | calendar / manual_task | 种植前准备或物料到货 | 物料类型 / 批次 | none | 入库任务 | CalendarItem / FarmingTask | S2 | 用 taskSubtype 区分药剂和肥料 |
| S2 | 物料信息录入 | input | S1 | 名称 / 规格 / 有效期 / 批次 / 数量 | none | 物料记录 | InventoryItem / InventoryTransaction / EventRecord | S3 | 需要独立库存表 |
| S3 | 入库确认 | review / feedback | 录入完成 | 物料记录 | none | 库存可用状态 | InventoryTransaction / Feedback / EventRecord | END_COMPLETED |  |

---

# 5. 具体农事项矩阵

| workflowKey | generalFlowKey | trigger | specificLogic | output | notes |
|---|---|---|---|---|---|
| WF_SERVICE_AREA | none | 种植前准备 | 航测、影像拼接、田块提取、人工确认服务区、上传 shape 文件 | Field.metadata / EventRecord | 地块/服务区数字化 |
| WF_IRRIGATION_DEVICE | none | 种植前准备 | 灌溉硬件安装与测试 | ExecutionRecord | 设备信息字段后续确认 |
| WF_PESTICIDE_STOCK_IN | GENERAL_MATERIAL_STOCK_IN | 药剂到货或种植前准备 | 药剂信息录入和入库确认 | InventoryItem / InventoryTransaction / EventRecord / Feedback | 支撑植保方案 |
| WF_FERTILIZER_STOCK_IN | GENERAL_MATERIAL_STOCK_IN | 肥料到货或种植前准备 | 肥料信息录入和入库确认 | InventoryItem / InventoryTransaction / EventRecord / Feedback | 支撑施肥处方 |
| WF_SOIL_TEST | none | 最晚种植前 13 天 | 采样点规划、采土、实验室检测、测土数据入库、土壤插值 | OperationPlan.basis / EventRecord | 是否生成一维码待确认 |
| WF_FERTILIZER_PRESCRIPTION | none | 种植前三天 / 测土结果就绪 | 获取测土、品种、面积、目标产量等输入，调用施肥处方算法 | OperationPlan | 处方图结构待确认 |
| WF_DRY_LAND_PREPARATION | none | 种植前准备 / 农事日历 | 旋耕整地作业和反馈 | Feedback |  |
| WF_LAND_LEVELING | none | 水整地后 | RGB 影像上传，平地效果评估 | ExecutionRecord / EventRecord |  |
| WF_WATER_LEVEL_SETUP | none | 水整地 / 平地效果评估完成后 | 航测、影像拼接、水位布设区域推荐 | OperationPlan |  |
| WF_TRANSPLANTING | none | plantingMethod = transplanting | 移栽作业，只记录执行结果和实际移栽日期 | Feedback / PlantingPlan / EventRecord | 不需要 OperationPlan |
| WF_SOIL_SEAL_WEED | GENERAL_PLANT_PROTECTION_CONTROL | soil_treatment_diagnosis 或农事规则推荐执行时间 | 调用 control_plan 接口按 strategy=土壤封闭生成 OperationPlan，再执行植保防治 | OperationPlan / Feedback | 正式作业不调用调查日期推荐算法 |
| WF_STEM_LEAF_WEED | GENERAL_PLANT_PROTECTION_SURVEY + GENERAL_PLANT_PROTECTION_CONTROL | soil_treatment_diagnosis 返回的药前调查日期到期 | 药前调查后调用 weed_treatment_diagnosis；如返回需防治，再调用 control_plan 生成 OperationPlan；补防诊断结果需人工确认 | OperationPlan / Feedback / ReviewRequest | 跨农事链路见 CHAIN_STEM_LEAF_WEED |
| WF_DISEASE_PEST_SEALING_SURVEY | GENERAL_PLANT_PROTECTION_SURVEY | 封行病虫调查日期到期 | 调查结果录入后按病虫类别调用对应防治推荐算法 | TaskIntent / OperationPlan | 调查不一定触发防治 |
| WF_DISEASE_PEST_SEALING_CONTROL | GENERAL_PLANT_PROTECTION_CONTROL | 防治推荐算法返回需防治 | 纯打药作业 | Feedback | 消费调查后生成的 OperationPlan |
| WF_DISEASE_PEST_SUDDEN_SURVEY | GENERAL_PLANT_PROTECTION_SURVEY | 突发病虫调查日期到期 | 调查结果录入后按病虫类别调用对应防治推荐算法 | TaskIntent / OperationPlan | 调查不一定触发防治 |
| WF_DISEASE_PEST_SUDDEN_CONTROL | GENERAL_PLANT_PROTECTION_CONTROL | 防治推荐算法返回需防治 | 纯打药作业 | Feedback | 消费调查后生成的 OperationPlan |
| WF_DISEASE_PEST_HEADING_SURVEY | GENERAL_PLANT_PROTECTION_SURVEY | 齐穗病虫调查日期到期 | 调查结果录入后按病虫类别调用对应防治推荐算法 | TaskIntent / OperationPlan | 调查不一定触发防治 |
| WF_DISEASE_PEST_HEADING_CONTROL | GENERAL_PLANT_PROTECTION_CONTROL | 防治推荐算法返回需防治 | 纯打药作业 | Feedback | 消费调查后生成的 OperationPlan |
| WF_DISEASE_PEST_BOOTING_SURVEY | GENERAL_PLANT_PROTECTION_SURVEY | 破口病虫调查日期到期 | 调查结果录入后按病虫类别调用对应防治推荐算法 | TaskIntent / OperationPlan | 调查不一定触发防治 |
| WF_DISEASE_PEST_BOOTING_CONTROL | GENERAL_PLANT_PROTECTION_CONTROL | 防治推荐算法返回需防治 | 纯打药作业 | Feedback | 消费调查后生成的 OperationPlan |
| WF_BASE_FERTILIZER | GENERAL_FERTILIZATION_OPERATION | 农事规则推荐执行时间 | 施基肥作业 | Feedback | 范围由 farmingRuleLibrary 维护 |
| WF_TILLERING_FERTILIZER | GENERAL_FERTILIZATION_OPERATION | 农事规则推荐执行时间 | 施分蘖肥作业 | Feedback |  |
| WF_PANICLE_VARIABLE_PRESCRIPTION | GENERAL_GROWTH_MONITORING | 施穗肥前 | 长势结果进入穗肥变量处方图算法 | OperationPlan | 施穗肥使用该处方图 |
| WF_PANICLE_FERTILIZER | GENERAL_FERTILIZATION_OPERATION | 农事规则推荐执行时间 / 穗肥处方就绪 | 施穗肥作业 | Feedback | 依赖穗肥变量处方图 |
| WF_PANICLE_FERTILIZER_EFFECT_CHECK | GENERAL_GROWTH_MONITORING | 穗肥后 7-10 天 | 长势检测结果作为穗肥效果抽查结果 | FieldConditionReported / Feedback | 不适用于所有施肥 |
| WF_GROWTH_MONITOR | GENERAL_GROWTH_MONITORING | 生育期 / 定期 | 普通长势监测后可生成异常点位，并触发定点低空 RGB 归因分析 | FieldConditionReported / ReviewRequest | 不包含稳肥变量推荐和产量预测 |
| WF_MISSING_SEEDLING_DETECTION | none | 与移栽同步 | 低空面状 RGB，缺苗识别算法生成缺苗区域矢量文件，人工判断是否触发补苗 | EventRecord / ReviewRequest / TaskIntent | 补苗任务不自动触发 |
| WF_LODGING_DETECTION | none | 倒伏反馈后 | 高空 RGB，倒伏识别算法 | EventRecord / FarmingTask status update |  |
| WF_PLANT_PROTECTION_SERVICE_EVALUATION | none | 植保服务后 / 收割前窗口 | 农户反馈、服务人员现场调查、实际情况反馈录入 | Feedback | 与收割前晒田分开 |
| WF_PRE_HARVEST_DRAIN | none | 收获前 12 天 | 晒田作业和反馈 | Feedback |  |
| WF_HARVEST | none | 达到收割条件 | 收割作业和反馈 | Feedback | 不细分人工/机械 |
| WF_RATOON_SEEDLING_FERTILIZER | GENERAL_FERTILIZATION_OPERATION | riceCroppingType = ratoon_rice / 农事规则推荐执行时间 | 再生季施发苗肥 | Feedback |  |
| WF_RATOON_BUD_FERTILIZER | GENERAL_FERTILIZATION_OPERATION | riceCroppingType = ratoon_rice / 农事规则推荐执行时间 | 再生季施促芽肥 | Feedback |  |
| WF_RATOON_DRY_FIELD | none | riceCroppingType = ratoon_rice / 农事规则推荐执行时间 | 再生季晒田作业 | Feedback |  |
| WF_RATOON_HARVEST | none | riceCroppingType = ratoon_rice / 农事规则推荐执行时间 | 再生季收割作业 | Feedback |  |

---

# 6. 跨农事链路

## 6.1 CHAIN_PLANT_PROTECTION_SURVEY_TO_CONTROL：植保调查到防治

```text
SurveyDateRecommendationJob
→ 调查类 CalendarItem
→ TaskDueCheckJob
→ 植保调查 FarmingTask
→ 调查结果录入
→ 防治推荐算法
→ no_action 或 OperationPlan
→ 植保防治 FarmingTask
```

## 6.2 CHAIN_STEM_LEAF_WEED：茎叶除草和补防

```text
后台调用 soil_treatment_diagnosis 维护药前调查日期
→ 药前调查
→ 调查结果录入
→ weed_treatment_diagnosis
→ 重新调查 或 推荐防治日期 + control_plan_input
→ control_plan 生成 OperationPlan
→ 茎叶除草作业
→ after_treatment_diagnosis 推荐药后调查日期
→ 药后调查
→ 药害识别算法
→ 药害识别结果人工复核
→ additional_treatment_diagnosis
→ 无需补防 / 暂缓补防并补充调查 / 立即补防
→ 立即补防时进入人工确认
→ no_action / ReviewRequest / 补防 TaskIntent
```

## 6.3 CHAIN_PANICLE_FERTILIZER：穗肥前监测到穗肥效果抽查

```text
穗肥前长势监测
→ 穗肥变量处方图生成
→ 施穗肥
→ 穗肥后 7-10 天施肥效果抽查
```

## 6.4 CHAIN_RATOON_SEASON：再生季农事

```text
PlantingPlan.riceCroppingType = ratoon_rice
→ 再生季施发苗肥
→ 再生季施促芽肥
→ 再生季晒田
→ 再生季收割
```

## 6.5 CHAIN_SERVICE_EVALUATION_AND_HARVEST：服务效果评估和收割前农事

```text
植保服务效果评估收集
收割前晒田
收割
```

说明：植保服务效果评估收集、收割前晒田和收割是三个独立农事，不应合并为同一个 FarmingTask。

---

# 7. 分支规则表

| branchId | sourceKey | fromStepId | conditionType | conditionDescription | targetKey | output |
|---|---|---|---|---|---|---|
| B_SERVICE_01 | WF_SERVICE_AREA | S2 | manual_decision | 不需要更新服务区 | END_NO_ACTION | TaskIntent(no_action) |
| B_SERVICE_02 | WF_SERVICE_AREA | S2 | manual_decision | 需要更新服务区 | WF_SERVICE_AREA.S3 | FarmingTask |
| B_PP_SURVEY_01 | GENERAL_PLANT_PROTECTION_SURVEY | S4 | threshold | 分类防治推荐算法返回需要防治，并给出防治日期和防治方案 | GENERAL_PLANT_PROTECTION_CONTROL.S1 | TaskIntent / OperationPlan / FarmingTask |
| B_PP_SURVEY_02 | GENERAL_PLANT_PROTECTION_SURVEY | S4 | threshold | 推荐算法返回不需要防治 | END_NO_ACTION | TaskIntent(no_action) |
| B_PP_SURVEY_03 | GENERAL_PLANT_PROTECTION_SURVEY | S4 | risk | 推荐算法结果不确定、方案风险高或天气窗口不确定 | REVIEW | ReviewRequest |
| B_WEED_DIAG_01 | CHAIN_STEM_LEAF_WEED | weed_treatment_diagnosis | result | 算法返回 5d 后重新调查 | GENERAL_PLANT_PROTECTION_SURVEY.S1 | CalendarItem |
| B_WEED_DIAG_02 | CHAIN_STEM_LEAF_WEED | weed_treatment_diagnosis | result | 算法返回推荐防治日期和 control_plan_input | GENERAL_PLANT_PROTECTION_CONTROL.S1 | OperationPlan / FarmingTask |
| B_WEED_POST_01 | CHAIN_STEM_LEAF_WEED | additional_treatment_diagnosis | manual_decision | 算法返回需要立即补防，人工确认后执行 | GENERAL_PLANT_PROTECTION_CONTROL.S1 | ReviewRequest / TaskIntent / OperationPlan |
| B_WEED_POST_02 | CHAIN_STEM_LEAF_WEED | additional_treatment_diagnosis | result | 算法返回无需补防 | END_CLOSED | Feedback / TaskIntent(no_action) |
| B_WEED_POST_04 | CHAIN_STEM_LEAF_WEED | additional_treatment_diagnosis | result | 算法返回需待药害缓解后补充调查 | GENERAL_PLANT_PROTECTION_SURVEY.S1 | CalendarItem |
| B_WEED_POST_03 | CHAIN_STEM_LEAF_WEED | herbicide_damage_recognition | risk | 药害识别算法结果不确定或风险高，需要人工复核 | REVIEW | ReviewRequest |
| B_SEEDLING_01 | WF_MISSING_SEEDLING_DETECTION | recognition_result | manual_decision | 识别出缺苗区域后，人工判断需要补苗 | REVIEW_OR_TASK_INTENT | ReviewRequest / TaskIntent |
| B_SEEDLING_02 | WF_MISSING_SEEDLING_DETECTION | recognition_result | result | 未识别出缺苗区域 | END_CLOSED | FarmingTask status update |
| B_GROWTH_01 | GENERAL_GROWTH_MONITORING | S5 | manual_decision | 普通长势监测发现异常点位后，人工判断需要触发定点低空 RGB 归因分析 | LOW_ALTITUDE_RGB_CAUSE_ANALYSIS | FarmingTask / EventRecord |
| B_GROWTH_02 | GENERAL_GROWTH_MONITORING | S5 | result | 普通长势监测未发现异常点位 | END_CLOSED | FarmingTask status update |
| B_GROWTH_03 | GENERAL_GROWTH_MONITORING | cause_analysis | risk | 归因结果不确定或需要人工确认 | REVIEW | ReviewRequest |
| B_EXEC_01 | * | execution_result | execution_result | 作业失败 | REVIEW | Feedback / ReviewRequest |
| B_EXEC_02 | * | execution_result | execution_result | 作业部分完成 | REVIEW | Feedback / ReviewRequest |

---

# 8. 对 data-model.md 的潜在影响

基于具体农事项、通用流程、跨农事链路三层结构，建议后续评估是否增加轻量追踪字段：

```text
TaskIntent.workflowKey
TaskIntent.workflowStepKey
TaskIntent.generalFlowKey
TaskIntent.chainKey
TaskIntent.parentTaskId

FarmingTask.workflowKey
FarmingTask.workflowStepKey
FarmingTask.generalFlowKey
FarmingTask.chainKey
FarmingTask.parentTaskId

OperationPlan.workflowKey
OperationPlan.workflowStepKey
OperationPlan.generalFlowKey
OperationPlan.chainKey

Execution.workflowKey
Execution.workflowStepKey
Execution.generalFlowKey
Execution.chainKey

ReviewRequest.workflowKey
ReviewRequest.workflowStepKey
ReviewRequest.generalFlowKey
ReviewRequest.chainKey

EventRecord.workflowKey
EventRecord.workflowStepKey
EventRecord.generalFlowKey
EventRecord.chainKey
```

暂不建议新增：

```text
GeneralFlowDefinition
WorkflowDefinition
WorkflowInstance
WorkflowStepInstance
ChainDefinition
```

已确认需要新增或保留的支撑数据对象：

```text
InventoryItem
InventoryTransaction
```

说明：药剂和肥料入库需要独立库存表，不再只作为 EventRecord / ExecutionRecord 附属信息。

原因：

```text
1. MVP 当前目标不是做通用工作流平台。
2. generalFlowKey / chainKey 可以先作为枚举或字符串编码。
3. 多步骤流程可以先由 Handler / Policy / Strategy 编排。
4. 如果后续流程配置化需求明确，再引入定义表和实例表。
```

---

# 9. 复核结论与剩余待定

```text
1. PDF 中红色部分先不处理，不转成正式待办。
2. 图片中结构有误：草害调查和虫害调查的推荐日期都由后台任务获取。
3. 封闭除草不调用杂草调查日期推荐算法。
4. 药后调查结果可进入 additional_treatment_diagnosis；算法返回需要立即补防时，必须人工确认后才能生成补防任务。
5. 病虫害防治推荐可以共用外部 endpoint，但系统内部按 strategy / target / stage 区分算法语义和 algorithmCode。
6. 长势监测异常点位生成后，由人工判断是否触发定点低空 RGB 归因分析。
7. 缺苗识别结果由人工判断是否触发补苗任务。
8. 药剂 / 肥料入库需要独立库存表。
9. 移栽作业不需要 OperationPlan，只记录执行结果和实际移栽日期。
10. 再生季施发苗肥、施促芽肥、晒田、收割的执行时间由农事规则推荐。
11. generalFlowKey / chainKey 是否进入第一版表结构暂未确定。
12. 茎叶除草药前调查日期由 soil_treatment_diagnosis 接口返回。
```

---

# 10. 下一步

```text
1. 用本文档和业务负责人逐项确认 workflowKey / generalFlowKey / chainKey / taskSubtype。
2. 将确认后的 taskSubtype 回写到 docs/model/data-model.md。
3. 评估是否在 data-model.md 增加 workflowKey / workflowStepKey / generalFlowKey / chainKey / parentTaskId。
4. 再生成 docs/model/er-diagram.md。
```
