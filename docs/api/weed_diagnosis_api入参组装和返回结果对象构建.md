# weed_diagnosis_api 入参组装和返回结果对象构建

## 统一口径

- 只有“未来调查/评估日期推荐”这类结果，才直接落 `CalendarItem`。
- 只要接口已经返回具体作业方案或处置措施，并附带执行时间窗，就先落 `TaskIntent`。
- `TaskIntent` 进入人工 `ReviewRequest` 后，审核通过再生成正式 `FarmingTask`。
- `OperationPlan` 不直接挂在 `TaskIntent` 或 `CalendarItem` 上；它只在正式 `FarmingTask` 创建后，作为该任务的执行依据被创建。
- 仅在调用杂草防治外部接口时，如 `PlantingPlan` 的种植制度为 `再生稻`，请求参数里的 `cultivation_system` 归一化为 `早稻`；系统内部上下文仍保留 `再生稻` 原值。

## 1. `soil_treatment_diagnosis`

入参来源：

- `province`：从种植计划关联农场信息获取。
- `cultivation_system`、`cultivation_pattern`、`cultivation_date`：从 `PlantingPlan` 获取。

返回承接：

- `soil_treatment_recommended_date`、`farming_operation`、`control_plan`：
  共同组成“土壤封闭建议”，先写入 `TaskIntent.ruleResult`。
- 人工审核通过后：
  生成 `WF_SOIL_SEAL_WEED` 的正式 `FarmingTask`。
- 正式任务创建后：
  再创建 `OperationPlan`，其中：
  `soil_treatment_recommended_date` -> `operationWindowStart / operationWindowEnd`
  `control_plan` -> `OperationPlan.parameters`
  `farming_operation` -> 任务标题、说明或 `parameters.operationAction`

## 2. `weed_survey_date_diagnosis`

入参来源：

- `weather_data`：通过外部气象接口获取，由核心后端 / adapter 组装。
- `rice_type`、`cultivation_system`、`cultivation_pattern`、`cultivation_date`：从 `PlantingPlan` 获取。

返回承接：

- `pre_stem_leaf_herbicide_survey_date`：
  新增或更新一个茎叶除草药前调查 `CalendarItem`。

## 3. `weed_treatment_diagnosis`

入参来源：

- `province`：从种植计划关联农场信息获取。
- `weather_data`：通过外部气象接口获取，由核心后端 / adapter 组装。
- `rice_type`、`cultivation_system`、`cultivation_pattern`、`cultivation_date`：从 `PlantingPlan` 获取。
- `survey_data_before_treatment`：从对应药前调查 `FarmingTask` 的 `ExecutionRecord.resultPayload` 获取。
- `last_survey_date`：从上一次药前调查的 `ExecutionRecord.actualEndAt` 获取；如首次调查则为 `null`。

返回承接：

- `pre_stem_leaf_herbicide_survey_date` 非空：
  新增或更新一个茎叶除草药前调查 `CalendarItem`。
- `control_target`、`recommended_control_date`、`control_plan` 非空：
  共同组成“茎叶除草建议”，先写入 `TaskIntent.ruleResult`。
- 人工审核通过后：
  生成正式 `WF_STEM_LEAF_WEED` `FarmingTask`。
- 正式任务创建后：
  再创建 `OperationPlan`，其中：
  `recommended_control_date` -> `operationWindowStart / operationWindowEnd`
  `control_target`、`control_plan` -> `OperationPlan.parameters`

## 4. `after_treatment_survey_date_diagnosis`

入参来源：

- `operation_date`：从茎叶除草正式任务的 `ExecutionRecord.actualEndAt` 获取。

返回承接：

- `rice_safety_survey_date`：
  新增安全性调查 `CalendarItem`。
- `control_effect_survey_date`：
  新增防效兼安全性调查 `CalendarItem`。

## 5. `injury_mitigation_diagnosis`

入参来源：

- `survey_date`：从安全性调查任务的 `ExecutionRecord.actualEndAt` 获取。
- `rice_injury_level`：从安全性调查任务的 `ExecutionRecord.resultPayload` 获取。

返回承接：

- `need_mitigation=false`：
  记录为 `TaskIntent(no_action)` 或作为复核结论中的无动作结果。
- `need_mitigation=true` 且 `measures`、`recommended_mitigation_date` 非空：
  共同组成“药害缓解建议”，先写入 `TaskIntent.ruleResult`，再进入人工 `ReviewRequest`。
- 人工审核通过后：
  生成正式 `FarmingTask`。
- 正式任务创建后：
  如需要执行方案，再创建 `OperationPlan`，其中：
  `recommended_mitigation_date` -> `operationWindowStart / operationWindowEnd`
  `measures` -> `OperationPlan.parameters`

## 6. `additional_treatment_diagnosis`

入参来源：

- `province`：从种植计划关联农场信息获取。
- `cultivation_system`、`cultivation_pattern`、`cultivation_date`：从 `PlantingPlan` 获取。
- `control_date`：从茎叶除草正式任务的 `ExecutionRecord.actualEndAt` 获取。
- `previous_injury_level`：从安全性调查任务的 `ExecutionRecord.resultPayload` 获取。
- `survey_data_before_treatment`：从药前调查任务的 `ExecutionRecord.resultPayload` 获取。
- `survey_data_after_treatment`：从防效兼安全性调查任务的 `ExecutionRecord.resultPayload` 获取。

返回承接：

- `need_recontrol=true` 且 `recontrol_target`、`recommended_recontrol_date`、`control_plan` 非空：
  共同组成“补防建议”，先写入 `TaskIntent.ruleResult`，再进入人工 `ReviewRequest`。
- 人工审核通过后：
  生成正式 `WF_STEM_LEAF_WEED` `FarmingTask`。
- 正式任务创建后：
  再创建 `OperationPlan`，其中：
  `recommended_recontrol_date` -> `operationWindowStart / operationWindowEnd`
  `recontrol_target`、`control_plan` -> `OperationPlan.parameters`
- `additional_survey_date` 非空：
  新增补充调查 `CalendarItem`。
- `injury_mitigation.need_mitigation=true`：
  将 `injury_mitigation.measures`、`injury_mitigation.recommended_mitigation_date` 作为“药害缓解建议”写入 `TaskIntent.ruleResult`，再进入人工 `ReviewRequest`。
- `service_effect_evaluation_date` 非空：
  新增服务效果评估 `CalendarItem`。
