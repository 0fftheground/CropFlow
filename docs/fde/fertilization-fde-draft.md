# 施肥方向 FDE 输出初稿

> 用途：作为“如何把施肥方向需求梳理到可开发”的参考初稿。  
> 当前定位：施肥方向当前事实源；已冻结口径以本文为准，后续正式 API / workflow / model 文档按本文同步。
> 使用方式：
> 1. 先按本文补齐缺失口径、分支和字段
> 2. 再把已冻结的系统事实回写到 `docs/domain/`、`docs/workflow/`、`docs/api/`
> 3. 未冻结项继续保留在“待决问题”里，不要提前伪装成正式系统规则

## 1. 基本信息

- 业务名称：施肥方向农事项闭环
- 建议流程标识：`fertilization_task_flow`
- 所属业务线 / 模块：Fertilization / Task Module / Plan Orchestrator / Review Module / Material & Inventory Module
- 当前阶段：
  - P1 可开发契约收口；已可支撑任务拆分、数据模型草案、API contract 和后端骨架设计
- 适用范围：
  - 水稻种植计划下的测土、施肥处方、基肥 / 分蘖肥 / 穗肥、穗肥前长势监测与变量处方、分阶段施肥后的效果评估
- 不适用范围：
  - 复杂库存结转和完整仓储管理
  - 自动设备闭环执行
  - 所有作物通用施肥口径
  - 再生稻发苗肥、促芽肥暂不纳入本轮 FDE
- 关联角色：
  - 发起方：系统编排器、后台 Job、人工操作人员
  - 执行方：农服人员、实验室、无人机服务人员、种植户
  - 审核方：农艺师、处方审核人员
  - 结果使用方：任务中心、处方查看页、执行反馈页、后续编排链路

## 2. 业务目标

- 这条流程解决什么问题：
  - 把“采土测土 -> 施肥处方 -> 分阶段施肥 -> 穗肥前监测 -> 变量穗肥 -> 施肥效果评估”整理成可以开发和联调的系统闭环
- 系统为什么需要感知它：
  - 施肥不是单次作业，而是依赖采样、检测、算法处方、阶段窗口、长势监测和执行反馈的连续链路
- 最终希望输出什么结果：
  - 可追溯的施肥处方
  - 分阶段施肥 `CalendarItem / FarmingTask / OperationPlan`
  - 可选的人工审核、变量处方图、通用施肥效果评估和异常后续处理入口

## 3. 闭环结束条件

- 什么情况下视为完成：
  - 常规场景下，施基肥 / 施分蘖肥 / 施穗肥及必要的效果评估完成，且无异常后续动作
- 什么情况下转入下一流程：
  - 土样采集完成后转土样检测
  - 土样检测完成或复用历史检测结果后转施肥处方生成
  - 施肥处方保存后先转施基肥、施分蘖肥和分蘖末期遥感长势监测 `CalendarItem`；施穗肥 `CalendarItem` 待分蘖末期遥感长势监测完成并产出变量处方后再生成
  - 穗肥前长势监测完成后转变量穗肥处方
  - 施肥执行完成后可转效果评估；当前 checklist 已覆盖基肥、施蘖肥和施穗肥完成后 7-10 天的评估场景
- 什么情况下仅记录，不继续推进：
  - 施肥效果评估结果正常，当前不触发后续复核或补施肥
- 什么情况下转人工：
  - 施肥处方需要人工审核或人工调整
  - 穗肥前监测发现异常但算法无法直接给出变量处方
  - 施肥效果评估异常，需要人工判断是否复核、补施肥或仅记录

## 4. 触发规则

- 触发来源：
  - 计划创建
  - 人工勾选新增采土任务
  - 土样结果上传
  - 复用历史土样检测数据
  - 生育期 / 农事规则推荐窗口
  - 长势监测结果
  - 执行完成反馈
- 具体触发事件：
  - `soil_sampling`：计划创建时人工选择新增采土任务
  - `soil_testing`：采土任务完成并生成土样编号后，生成土样检测任务
  - `prescription_generation`：历史检测数据复用或新检测结果上传完成
  - `base_fertilizer / tillering_fertilizer / tillering_growth_monitoring`：施肥处方就绪后，由规则或阶段窗口生成对应 `CalendarItem`
  - `panicle_fertilizer`：分蘖末期遥感长势监测完成并产出变量处方后，由规则或阶段窗口生成施穗肥 `CalendarItem`
  - `effect_evaluation`：施基肥、施蘖肥或施穗肥 `FarmingTask` 完成后 7-10 天，生成通用施肥效果评估 `CalendarItem`
- 前置条件：
  - `PlantingPlan` 存在，且地块归属合法
  - 采样点、土样、检测结果、品种、面积等关键输入可用
  - 施肥处方算法必需参数已具备
- 阻断条件：
  - 没有采样点或检测结果
  - 算法必需参数未补齐
  - 关键上游对象失效
  - 变量穗肥依赖的长势监测结果不存在
- 是否允许重算：
  - 是
- 重算触发条件：
  - 已上传的土样检测结果发生纠错更正（少见场景）
- 重算后旧对象如何处理：
  - 施肥处方建议：
    - 如果因土样检测结果纠错而重算，整份施肥处方都应重新计算；之前的处方结果需要保留，但置为不启用，由新处方替代
  - 已生成但未执行的施肥 `CalendarItem`：
    - 建议允许更新或失效重建
  - 已执行的正式任务：
    - 不应被静默覆盖
- 幂等建议：
  - `plan_id + taskSubtype + source_execution_record_id + input_hash`

## 5. 输入字段来源

| 字段 | 是否必填 | 来源对象 / 来源系统 | 来源字段 / 录入位置 | 示例 | 缺失时动作 | 备注 |
|---|---|---|---|---|---|---|
| planting_plan_id | 是 | PlantingPlan | id | `pp_1001` | 阻断并报错 | 全链路主追溯键 |
| farm_id / field_ids | 是 | Farm / Field | id | `1 / [10, 11]` | 阻断并报错 | 用于采样、插值、执行 |
| variety_id | 常用 | PlantingPlan | varietyId | `1` | 阻断或转人工 | 影响处方算法 |
| crop_stage | 分阶段施肥常用 | CropStageState | currentStage | `tillering` | 延后生成或转人工 | 决定施肥窗口 |
| sampling_points | 土样采集必填 | PlantingPlan / 采样点规划算法 | 默认取种植计划各地块中心；后续可由接口返回 | `[{pointId: ..., fieldId: ..., location: ...}]` | 阻断采样任务 | 第一版默认使用 `PlantingPlan` 各地块中心，后续可能接入采样点规划接口 |
| soil_sample_ids | 土样检测必填 | 土样采集任务 | 任务生成时按采样点自动生成 | `["S-001"]` | 阻断检测任务 | 与采样点一一对应，不依赖采样结果回传；第一版不生成二维码 |
| soil_test_result | 处方生成必填 | 独立土壤检测结果表 / 历史复用 | 测土任务录入后按原始检测样表格式入库 | `{国标PH: 6.83, 有机质: 1.38, 有效磷-M3: 4.007, ...}` | 阻断处方生成 | 建议落独立土壤检测结果表，便于历史复用；存储时保留原始检测样表字段，算法调用时再按需取必要字段 |
| target_yield | 是 | 人工补录 / 规则 | 页面录入 | `400` | 等待补录 | 施肥算法接口要求单位为 `kg/亩` |
| fertilization_algorithm_params | 常用 | 人工补录 / 系统聚合 | 页面录入 / 聚合结果 | `{waysType: "M3", varietyType: "0", riceType: "4"}` | 等待补录 | 已从 `docs/references/raw/施肥算法接口.md` 提取核心参数 |
| growth_monitoring_result | 变量穗肥必填 | 无人机监测任务执行记录 / 遥感后续任务 | 业务人员到场执行无人机监测后，录入执行记录及遥感后续任务 id（影像上传、影像拼接） | `{remoteSensingTaskId: "...", zones: [...]}` | 阻断变量穗肥 | 长势监测流程为业务人员到达农场、执行无人机监测任务、完成后录入执行记录和遥感后续任务 id |
| execution_feedback | 施肥效果评估常用 | 执行完成页 | 反馈录入 | `{operationDate: ...}` | 不直接生成下游评估 | 至少需要来源施肥任务完成记录 |

补充说明：

- 施肥算法调用字段已按 `docs/references/raw/施肥算法接口.md` 收口：`waysType`、`targetYield`、`varietyType`、`riceType`、`excelData` 必填；`fertilizerA/B/C` 可选，不传或全为 `0-0-0` 时算法服务走默认肥料。
- `excelData` 从独立土壤检测结果表按采样点组装，必须包含采样点 ID、经纬度、国标 PH、有机质、有效磷-M3、有效钾-M3；`waysType=M3/healthy` 时还必须包含 Buffer PH、有效钙-M3、有效镁-M3；`waysType=soil` 时还必须包含碱解氮。
- 算法返回结果落点已按 `OperationPlan.parameters.fieldPlans[] / nutrientRatio / algorithmSummary / npkMapping` 收口，系统内正式处方按地块维度表达单位面积施肥量，不要求算法返回地块绝对施肥总量。
- 施肥方向和植保不同，前置数据更偏离散化结构化字段，而不是单次调查结果。
- 变量穗肥第一版只要求系统保存并透传变量处方图公开 URL；图内分区 / 插值区细节由外部处方图服务承载，不在 CropFlow 内展开。

## 6. 外部接口 / 规则调用

| interfaceCode / ruleCode | 接口 / 规则名 | 调用时机 | 关键输入 | 关键输出 | 成功后系统动作 | 失败兜底 |
|---|---|---|---|---|---|---|
| `samplingPointPlanningAlgorithm` | 采样点规划算法 | 第一版不调用，保留后续扩展 | 地块范围、采样规则 | 采样点清单 | 当前无系统动作 | 暂不接入 |
| `soilInterpolationAlgorithm` | 土壤插值算法 | 仅当存在未录入采样点检测结果的地块时调用 | 已有采样点检测结果、地块范围 | 补齐缺失地块的田块指标 | 为缺失地块补齐处方生成输入 | 无法补齐时转人工 |
| `fertilizerPrescriptionAlgorithm` | 施肥处方算法 `POST /run` | 土样检测结果就绪或历史数据复用后 | `waysType`、`targetYield`、`varietyType`、`riceType`、`fertilizerA/B/C`、`excelData` | 基肥 / 分蘖肥 / 穗肥处方、N/P/K 分配比例、样本点单位面积施肥量 | 生成处方建议 / OperationPlan 参数正文 | 记录失败并等待补数 |
| `growthMonitoringAlgorithm` | 长势监测算法 | 穗肥前监测 | 影像、区域范围 | 长势结果 / 异常区域 | 提供变量处方依据 | 转人工判断 |
| `panicleVariablePrescriptionAlgorithm` | 变量穗肥处方算法 | 穗肥前长势结果可用后 | 长势结果、地块范围、穗肥规则 | 变量处方图 / 分区施肥量 | 更新穗肥作业方案 | 仅保留长势结果，不自动生成变量处方 |
| `farmingCalendarApi` | 农事日历接口 | 施基肥 / 施分蘖肥 / 施穗肥窗口生成时 | 生育期、种植制度、阶段规则 | 推荐日期 / 时间窗 | 创建施肥 `CalendarItem` | 保留待定，人工处理 |

补充说明：

- 施肥处方算法原始文档在 `docs/references/raw/施肥算法接口.md`，开发入口 contract 为 `docs/api/fertilization_prescription_algorithm_api.md`，主接口是 `POST /run`。
- 当前接口返回里即使包含采样点级信息，系统内正式施肥方案也统一转换成按地块表达的 `OperationPlan.parameters.fieldPlans[]`。
- 第一版不调用采样点规划算法，默认使用 `PlantingPlan` 各地块中心作为采样点。
- 土壤插值算法只在存在未录入采样点检测结果的地块时调用；已有采样点检测结果的地块内，所有像元默认填充该采样点检测结果的值。
- 所有施肥处方都必须先人工审核，审核通过后才能进入后续正式方案和任务生成。
- 施肥算法 HTTP 200 仍可能返回业务失败，系统必须同时检查响应体 `code`；只有 `code=0` 且 `data` 为数组时才视为处方计算成功。
- 参数错误、枚举错误、`excelData` 解析失败等 4xx / `code!=0` 场景不生成 `OperationPlan`，只记录失败事件并停留在待补数 / 待审核状态。

## 7. 结果分支

| 分支编号 | 触发条件 / 返回特征 | 系统判断 | 下游动作 | 是否人工确认 | 备注 |
|---|---|---|---|---|---|
| `F-01` | 土样检测结果齐全 | 可生成处方 | 进入施肥处方生成任务 | 否 |  |
| `F-02` | 复用历史检测数据 | 可生成处方 | 跳过新检测，直接进入施肥处方生成任务 | 否 | 人工确认发生在施肥处方生成任务内，不额外增加审核分支 |
| `F-03` | 处方算法成功返回基肥 / 分蘖肥 / 穗肥三个处方 | 可推进 | 先进入人工审核；审核通过后保存三个处方，并生成施基肥 / 施分蘖肥 / 分蘖末期遥感长势监测 `CalendarItem` | 是 | 穗肥基础处方也需要保存，后续再叠加长势监测结果生成变量处方 |
| `F-04` | 穗肥前长势监测正常且变量处方生成成功 | 可推进 | 先进入人工审核；审核通过后用变量处方更新穗肥方案 | 是 | 在已保存的穗肥基础处方上叠加变量处方 |
| `F-05` | 长势监测异常但无法直接给出变量处方 | 需人工判断 | 创建 `ReviewRequest` | 是 |  |
| `F-06` | 施肥效果评估正常 | 闭环收口 | 记录结果，无后续动作 | 否 | 当前统一覆盖基肥、施蘖肥和施穗肥 |
| `F-07` | 施肥效果评估异常 | 需后续处理 | 触发人工处理农事，并保留评估结果与上下文 | 是 | 人工处理结果目前仅记录并结束 |

## 8. 对象映射

| 结果 / 动作 | 生成或更新对象 | 关键字段 | 说明 |
|---|---|---|---|
| 采样点 | 独立采样点表 / `CalendarItem` / `OperationPlan` | `samplingPointId`, `fieldId`, `location`, `soilSampleId` | 需要独立采样点表；采土任务和后续处方都引用同一批采样点 |
| 土样采集任务 | `CalendarItem` / `FarmingTask` | `taskSubtype=fertilization.soil_sampling` | 采土和测土是两个独立任务，采土任务负责生成采样点对应的土样编号 |
| 土样检测任务与结果 | `CalendarItem` / `FarmingTask` / 独立土壤检测结果表 | `taskSubtype=fertilization.soil_testing`, `resultPayload` | 土壤检测结果在测土任务中录入后落独立结果表，是处方生成的直接输入 |
| 施肥处方生成结果 | 施肥处方生成任务下的 `OperationPlan` | `taskSubtype=fertilization.prescription_generation`, `parameters`, `prescriptionMap` | 处方结果优先挂在施肥处方生成任务下，审核后再推进后续施肥事项 |
| 施基肥 / 施蘖肥 / 施穗肥预备事项 | `CalendarItem` | `taskSubtype=fertilization.base_fertilizer / fertilization.tillering_fertilizer / fertilization.panicle_fertilizer` | 仍是预备事项，不是正式任务；`taskSubtype` 需要保留明确施肥语义 |
| 分蘖末期遥感长势监测预备事项 | `CalendarItem` / `FarmingTask` | `taskSubtype=fertilization.tillering_growth_monitoring` | 处方生成完成后先生成，用于产出穗肥变量处方 |
| 施肥正式执行 | `FarmingTask` | `plannedTime`, `taskSubtype` | 到期后由 `TaskDueCheckJob` 生成 |
| 施肥作业方案 | `OperationPlan` | `operationWindow`, `parameters`, `prescriptionMap`, `riskNotes` | 正式执行依据 |
| 穗肥前监测结果 | `ExecutionRecord` / `FieldConditionReported` | `monitorPurpose=panicle_variable_prescription` | 变量穗肥输入 |
| 施肥效果评估结果 | `Feedback` / `Evaluation` / `ExecutionRecord` | `resultPayload` | 当前以人工现场评估为主；建议记录 `evaluatedTaskSubtype` 和来源施肥任务引用 |
| 施肥效果评估预备事项 | `CalendarItem` / `FarmingTask` | `taskSubtype=fertilization.effect_evaluation` | 当前统一覆盖基肥、施蘖肥和施穗肥，靠上下文字段区分被评估对象 |
| 异常后人工处理农事 | `CalendarItem` / `FarmingTask` | `taskSubtype=fertilization.manual_follow_up`, `contextRefs` | 施肥效果评估异常时触发，用于人工到田处理和后续判断 |

补充说明：

- 采土和测土在系统实现中按两个独立任务节点处理，不再只作为同一 workflowKey 下的两个松散子步骤。
- 施肥处方生成结果优先落在施肥处方生成任务下的 `OperationPlan`，而不是直接生成正式执行任务。

## 9. 人工录入字段

### 9.1 调查 / 采集 / 填报字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| sample_date | date | 采样时必填 | 实际采样日期 | `2026-06-25` | `resultPayload.sampleDate` |  |
| sample_operator | string | 否 | 采样人员 | `张三` | `resultPayload.operatorName` |  |
| logistics_no | string | 土样检测可选 | 快递单号 | `SF123...` | `resultPayload.logisticsNo` | 当前不作为土样检测任务的主触发条件，可保留为实验室流转补充信息 |
| soil_test_result | json | 检测后必填 | 检测结果正文 | `{国标PH: 6.83, Buffer PH: 7.04, 有机质: 1.38, 有效磷-M3: 4.007, 有效钾-M3: 103.551}` | 独立土壤检测结果表 | 建议单独建表存储，不放在 payload 中，便于历史复用；入库时按原始检测样表字段保留，算法调用时再按需提取必要字段 |
| reused_result_ref | string | 历史复用时必填 | 历史检测结果引用 | `soil_test_record_001` | `resultPayload.reusedResultRef` |  |
| ways_type | string | 处方生成必填 | 施肥方式 | `soil / healthy / M3` | `resultPayload.algorithmInputPatch.waysType` | 接口附录已定义 |
| target_yield | number | 处方生成必填 | 目标产量 | `400` | `resultPayload.algorithmInputPatch.targetYield` | 单位 `kg/亩` |
| variety_type | string | 处方生成必填 | 品种类型 | `0` | `resultPayload.algorithmInputPatch.varietyType` | `0=籼稻, 1=粳稻, 2=杂交稻（籼粳交）` |
| rice_type | string | 处方生成必填 | 稻作类型 | `4` | `resultPayload.algorithmInputPatch.riceType` | `4=早稻, 6=中稻, 8=再生稻...` |
| fertilizer_ratio_a | string | 否 | 肥料 A 的 N-P-K 比例 | `46-0-0` | `resultPayload.algorithmInputPatch.fertilizerA` | 不传时可走默认肥料 |
| fertilizer_ratio_b | string | 否 | 肥料 B 的 N-P-K 比例 | `18-46-0` | `resultPayload.algorithmInputPatch.fertilizerB` |  |
| fertilizer_ratio_c | string | 否 | 肥料 C 的 N-P-K 比例 | `0-0-60` | `resultPayload.algorithmInputPatch.fertilizerC` |  |

### 9.2 正式执行反馈字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| operation_date | datetime | 是 | 实际施肥时间 | `2026-07-01T09:00:00+08:00` | `completionPayload.operationDate` |  |
| actual_end_at | datetime | 否 | 实际完成时间 | `2026-07-01T10:30:00+08:00` | `completionPayload.actualEndAt` |  |
| fertilizer_items | array | 常用 | 实际使用肥料品类和数量 | `[{materialId:..., dosage:...}]` | `completionPayload.materialsUsed` | 后续可与库存联动 |
| operation_area | number | 否 | 实际作业面积 | `12.5` | `completionPayload.operationArea` |  |
| operator_name | string | 否 | 作业人 | `李四` | `completionPayload.operatorName` |  |
| execution_remark | string | 否 | 现场备注 | `局部减量撒施` | `completionPayload.remark` |  |

### 9.3 评价 / 反馈字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| effect_level | enum | 抽查时常用 | 施肥效果等级 | `normal / warning / fail` | `evaluation.result.effectLevel` |  |
| abnormal_area | array | 否 | 异常地块编号列表 | `["field-101", "field-102"]` | `evaluation.result.abnormalFieldIds` | 按地块编号存储 |
| suspected_reason | string / enum | 否 | 异常原因猜测 | `缺肥 / 积水 / 非施肥原因` | `evaluation.result.reason` | 可人工判断 |
| follow_up_suggestion | string | 否 | 后续建议 | `补施穗肥` | `feedback.result.followUpSuggestion` |  |

## 10. 方案或执行对象最小结构

本节不是重新定义一套新的 `OperationPlan` 结构，而是说明施肥场景如何延用系统既有 `OperationPlan` 字段，以及第一版实际会使用到的最小字段子集。下面表格中的字段都默认归属于 `OperationPlan`，为避免歧义，直接使用 `对象.字段` 写法。

当前口径：

```text
1. 施肥处方生成任务、施基肥、施蘖肥、施穗肥都延用既有 `OperationPlan` 基础字段。
2. 基肥、分蘖肥和穗肥处方都按“地块 -> 施肥量”表达，不再以采样点级结果作为系统内正式方案表达。
3. 穗肥变量处方图系统内只保存一个远程 URL，用于指向外部生成的处方图地址。
4. 穗肥变量处方图 URL 第一版采用直接公开 URL，不做签名 URL 或平台代理转发。
```

| 字段 | 是否必填 | 含义 | 来源 | 示例 | 备注 |
|---|---|---|---|---|---|
| `OperationPlan.operationWindowStart` | 否 | 建议开始时间 | 农事规则 / 算法 | `2026-07-01T06:00:00+08:00` |  |
| `OperationPlan.operationWindowEnd` | 否 | 建议结束时间 | 农事规则 / 算法 | `2026-07-03T18:00:00+08:00` |  |
| `OperationPlan.parameters.fieldPlans[]` | 是 | 施肥方案正文 | 处方算法 / 人工审核结果 | `[{fieldId:101, fertilizerStage:"base_fertilizer", fertilizers:[{name:"尿素", amountPerArea:7.2, amountUnit:"kg/亩"}]}]` | 基肥、分蘖肥、穗肥处方都按地块维度表达单位面积施肥量，无需在这里重复写肥料阶段语义 |
| `OperationPlan.prescriptionMap.url` | 否 | 穗肥变量处方图远程地址 | 变量穗肥算法 | `"https://remote.example.com/prescription-map/123.png"` | 系统内只保存远程公开 URL，不存完整图内容；第一版不做签名 URL 或平台代理转发 |
| `OperationPlan.operationArea` | 否 | 作用面积 | 计划 / 算法 | `12.5ha` |  |
| `OperationPlan.basis` | 否 | 方案依据 | 检测 / 监测 / 规则 | `soil_test + target_yield` |  |
| `OperationPlan.riskNotes` | 否 | 风险提示 | 算法 / 人工 | `雨前不建议施肥` |  |
| `OperationPlan.acceptanceCriteria` | 否 | 验收标准 | 业务约定 | `撒施均匀，无明显漏施` | 当前缺明确口径 |

`OperationPlan.parameters.fieldPlans[]` 第一版结构建议：

| 字段 | 是否必填 | 含义 | 来源 | 示例 | 备注 |
|---|---|---|---|---|---|
| `fieldId` | 是 | 系统内部地块 ID | 采样点到地块映射 | `101` | 使用 `Field.id`，不是外部地块编号 |
| `fieldName` | 否 | 地块名称 | Field | `9号田块` | 展示用 |
| `sourceSamplingPointIds[]` | 是 | 来源采样点 ID | 算法返回 `sectionId` / 系统映射 | `["344ecf..."]` | 支持追溯算法来源 |
| `fertilizerStage` | 是 | 施肥阶段 | 算法 `fertilizerType` 映射 | `base_fertilizer` | `0=base_fertilizer, 1=tillering_fertilizer, 2=panicle_fertilizer` |
| `fertilizerStageName` | 是 | 阶段中文名 | 算法 `fertilizerTypeName` | `基肥` | 展示用 |
| `fertilizers[]` | 是 | 肥料用量明细 | 算法 `project[].fertilizerList[]` | `[{name:"尿素", amountPerArea:7.2, amountUnit:"kg/亩", ratio:"46-0-0"}]` | `amount` 原始字符串需解析为单位面积量 |
| `area` | 否 | 地块面积 | Field / PlantingPlan | `12.5` | 第一版不要求据此计算绝对总量 |
| `areaUnit` | 否 | 面积单位 | Field / PlantingPlan | `亩` | 与后续总量换算保持一致 |
| `totalAmount` | 否 | 地块绝对总量 | 系统可选派生 | `90` | 第一版不强制生成；算法不返回该字段 |
| `totalAmountUnit` | 否 | 绝对总量单位 | 系统可选派生 | `kg` | 仅当系统侧按面积换算时填写 |

`fertilizers[]` 字段建议：

| 字段 | 是否必填 | 含义 | 来源 | 示例 |
|---|---|---|---|---|
| `name` | 是 | 肥料名称 | `project[].fertilizerList[].name` | `尿素` |
| `amountPerArea` | 是 | 单位面积推荐用量数值 | 解析 `amount` | `7.2` |
| `amountUnit` | 是 | 单位面积用量单位 | 解析 `amount` | `kg/亩` |
| `ratio` | 否 | N-P-K 比例 | `project[].fertilizerList[].ratio` | `46-0-0` |
| `rawAmount` | 是 | 算法原始用量字符串 | `project[].fertilizerList[].amount` | `7.2_kg/亩` |

## 10.1 土壤检测样表字段整理

以下字段来自 `docs/references/raw/土壤检测数据样表.xlsx`，适合作为“检测结果样表 -> 系统字段草案”的第一版基础。

| 样表列名 | 类型推测 | 建议优先级 | 含义 | 单位 / 示例 | 备注 |
|---|---|---|---|---|---|
| 序号 | integer | 低 | 样表内部行号 | `1` | 不一定要入系统 |
| 实验室编号 | string | 中 | 实验室检测单编号 | `S-26-136-04050` | 适合追溯检测来源 |
| 样品编号 | string | 高 | 样品唯一标识 | `026071-1` | 建议保留 |
| 检测农场 | string | 中 | 样品所属农场 / 地块描述 | `庐江万亩农场9号田块` | 可与系统地块做映射 |
| 地块编号 | string | 高 | 外部地块编号 | `地块88` | 建议与 `external_field_id` 对齐讨论 |
| 样品袋编号 | string | 中 | 样品袋编号 | 空 | 是否必需待定 |
| 国标PH | number | 高 | 土壤 pH | `6.83` | 建议原样存入土壤检测结果表 |
| Buffer PH | number | 中 | Buffer pH | `7.04` | 建议原样存入土壤检测结果表；`waysType=M3/healthy` 按必需字段组装入参 |
| 有机质 | number | 高 | 有机质含量 | `1.38 %` | 建议原样存入土壤检测结果表 |
| 有效钾-M3 | number | 高 | 有效钾 | `103.551 mg/kg` | 建议原样存入土壤检测结果表 |
| 有效钙-M3 | number | 中 | 有效钙 | `2163.829 mg/kg` | |
| 有效钠-M3 | number | 低 | 有效钠 | `134.153 mg/kg` | 原接口文档未提及 |
| 有效镁-M3 | number | 中 | 有效镁 | `677.466 mg/kg` | |
| 有效铝-M3 | number | 低 | 有效铝 | `796.975 mg/kg` | |
| 有效铁-M3 | number | 低 | 有效铁 | `158.197 mg/kg` | |
| 有效磷-M3 | number/string | 高 | 有效磷 | `4.007 mg/kg` | 建议原样存入土壤检测结果表 |
| 有效锌-M3 | number | 低 | 有效锌 | `1.217 mg/kg` | |
| 有效硼-M3 | number | 低 | 有效硼 | `0.136 mg/kg` | |
| 有效锰-M3 | number | 低 | 有效锰 | `148.796 mg/kg` | |
| 有效硫-M3 | number | 低 | 有效硫 | `20.910 mg/kg` | |
| 有效铜-M3 | number | 低 | 有效铜 | `2.418 mg/kg` | |
| 有效硅-M3 | number | 低 | 有效硅 | `0.370 mg/kg` | |

当前建议：

```text
1. 独立土壤检测结果表建议尽量按原始检测样表格式存储，不在入库时先裁剪成算法最小字段集。
2. 施肥算法调用时，再从结果表里提取必要字段；当前优先关注样品编号、地块编号、国标PH、有机质、有效磷-M3、有效钾-M3。
3. M3 / healthy 模式必需字段已确认；Buffer PH、有效钙-M3、有效镁-M3 按需保留并用于算法入参组装。
```

## 10.2 施肥算法 POST /run 映射草案

### 请求字段

| 接口字段 | 是否必填 | 当前来源建议 | 示例 | 备注 |
|---|---|---|---|---|
| waysType | 是 | 人工选择 / 业务规则 | `M3` | `soil / healthy / M3` |
| targetYield | 是 | 人工录入 | `400` | 单位 `kg/亩` |
| varietyType | 是 | 品种类型映射 | `0` | `0=籼稻, 1=粳稻, 2=杂交稻（籼粳交）` |
| riceType | 是 | 稻作类型映射 | `4` | `4=早稻, 8=再生稻 ...` |
| fertilizerA | 否 | 配方 / 平台配置 / 人工补录 | `46-0-0` | 不传可走默认值 |
| fertilizerB | 否 | 配方 / 平台配置 / 人工补录 | `18-46-0` | |
| fertilizerC | 否 | 配方 / 平台配置 / 人工补录 | `0-0-60` | |
| excelData | 是 | 从土壤检测结果表读取并组装 | `[{采样点ID: ..., 国标PH: ...}]` | 不是用户手工输入，而是系统从土壤检测结果表提取并按接口要求组装的采样点级输入 |

`excelData[]` 必需字段：

| 字段 | 适用 waysType | 是否必填 | 系统来源 |
|---|---|---|---|
| `采样点ID` | all | 是 | 采样点表 / 土样编号映射 |
| `经度` | all | 是 | 采样点坐标 |
| `纬度` | all | 是 | 采样点坐标 |
| `国标PH` | all | 是 | 土壤检测结果表 |
| `有机质（%）` | all | 是 | 土壤检测结果表；如原始样表列名为 `有机质`，系统组装请求时转换为接口列名 |
| `有效磷-M3` | all | 是 | 土壤检测结果表 |
| `有效钾-M3` | all | 是 | 土壤检测结果表 |
| `Buffer PH` | M3 / healthy | 是 | 土壤检测结果表 |
| `有效钙-M3` | M3 / healthy | 是 | 土壤检测结果表 |
| `有效镁-M3` | M3 / healthy | 是 | 土壤检测结果表 |
| `碱解氮` | soil | 是 | 土壤检测结果表；M3 / healthy 可传 `0` 或省略，按算法接口实际校验处理 |

### 响应字段

| 接口字段 | 建议系统落点 | 示例 | 备注 |
|---|---|---|---|
| sectionId | 中间映射字段，不直接作为正式方案结构暴露 | `344ecf...` | 可先用于把算法输出关联回采样点 / 地块 |
| sectionCropsId | 中间映射字段，不直接作为正式方案结构暴露 | `0` | 当前看是固定值 |
| nRatio / pRatio / kRatio | `OperationPlan.parameters.nutrientRatio` | `{base:5,tiller:3,ear:2}` | 表达三阶段 N/P/K 分配比例 |
| avgData | `OperationPlan.parameters.algorithmSummary` | `{avgOfN:"12.0_kg/亩"}` | 建议保留原始单位字符串，作为算法摘要 |
| project | `OperationPlan.parameters.fieldPlans[]` | `[{fieldId:101, fertilizerStage:"base_fertilizer", fertilizers:[{name:"尿素", amountPerArea:7.2, amountUnit:"kg/亩"}]}]` | 系统内正式处方按地块维度表达单位面积施肥量；阶段语义由挂载它的施肥任务 / `taskSubtype` 区分 |
| NPK | `OperationPlan.parameters.npkMapping` | `[{N:"尿素"}]` | 供页面解释和人工审核使用 |

补充说明：

```text
1. 当前接口返回里即使包含采样点级信息，系统内正式施肥方案仍统一转换成“地块 -> 施肥量”结构。
2. 穗肥变量处方图在系统内只保留远程 URL，不保存完整图内容。
3. `project[].fertilizerList[]` 经过地块映射 / 补齐后，已足够支撑前端展示“地块 -> 阶段 -> 肥料名称 -> 单位面积用量 -> 单位”。
4. 算法只需要返回样本点的单位面积施肥量；系统侧负责把样本点结果映射 / 补充为地块维度的单位面积施肥量，不要求算法返回地块绝对施肥总量。
5. 如前端或执行侧需要绝对总量，系统可在展示或执行方案生成阶段按 `amountPerArea * area` 派生，但该字段不作为算法接口要求。
```

## 11. 人工判断规则

- 是否需要人工判断：
  - 需要；当前已明确施肥处方和变量穗肥处方都必须经过人工审核
- 判断类型建议：
  - `review_fertilization_prescription`
  - `review_panicle_variable_prescription`
- 触发原因：
  - 处方算法输出需要人工确认
  - 人工调整施肥量
  - 变量穗肥图异常或原因不清
  - 施肥效果评估异常后，需要触发人工处理农事
- 人工需要看到的上下文：
  - 计划、地块、品种、生育期
  - 土样 / 检测结果
  - 处方参数与算法依据
  - 历史施肥执行记录
  - 穗肥前 / 穗肥后长势监测结果
  - 施肥处方审核页必须展示：
    - 土壤检测数据：采样点、土样编号、地块、坐标、原始检测字段、被算法使用的字段、历史复用来源
    - 算法入参：`waysType`、`targetYield`、`varietyType`、`riceType`、肥料 A/B/C、组装后的 `excelData` 摘要
    - 算法处方：基肥、分蘖肥、穗肥三阶段的地块维度 `fieldPlans[]`、肥料名称、N-P-K 比例、单位面积用量、算法原始 `project` 摘要
  - 穗肥变量处方审核页必须展示：
    - 穗肥基础处方
    - 穗肥前长势监测执行记录
    - 遥感后续任务 id（影像上传、影像拼接）
    - 变量处方图公开 URL / 预览入口
    - 变量处方叠加后的穗肥方案摘要
- 候选决策动作：
  - `approve`
  - `reject`
  - `adjust`
  - `no_action`
  - `need_more_info`
- 各决策的系统影响：
  - `approve`：生成或更新正式施肥方案 / 正式任务
  - `reject`：关闭当前建议，不生成正式执行对象
  - `adjust`：保存人工调整后的处方或变量处方，再回编排
  - `no_action`：持久化人工结论，不继续生成后续对象
- `need_more_info`：保持待处理，等待补数或复测

`ReviewRequest.decisionPayload` 第一版建议：

| 字段 | 适用审核类型 | 是否必填 | 含义 |
|---|---|---|---|
| `contextRefs.plantingPlanId` | all | 是 | 来源种植计划 |
| `contextRefs.prescriptionTaskId` | 处方审核 / 变量处方审核 | 是 | 施肥处方生成任务 |
| `contextRefs.sourceOperationPlanId` | 处方审核 / 变量处方审核 | 否 | 待审核处方方案 |
| `contextRefs.growthMonitoringTaskId` | 变量处方审核 | 是 | 穗肥前长势监测任务 |
| `contextRefs.remoteSensingTaskIds` | 变量处方审核 | 是 | 影像上传、影像拼接等遥感后续任务 id |
| `soilTestSummary` | 处方审核 | 是 | 审核页展示用土壤检测摘要 |
| `algorithmInputSummary` | 处方审核 | 是 | 算法入参摘要 |
| `algorithmOutputSummary` | 处方审核 | 是 | 算法原始输出摘要 |
| `proposedPlan.fieldPlans[]` | 处方审核 / 变量处方审核 | 是 | 审核通过后写入 `OperationPlan.parameters.fieldPlans[]` 的方案正文 |
| `proposedPlan.prescriptionMap.url` | 变量处方审核 | 是 | 变量处方图公开 URL |
| `adjustmentReason` | adjust | 否 | 人工调整原因 |

补充说明：

- 施肥效果评估异常不走 `ReviewRequest` 复核；当前口径是触发人工处理农事，人工处理结果目前仅记录并结束，不生成补施肥建议，也不回编排生成新事项。

## 12. 页面 / 交互建议

- 这个流程在哪个页面发起或录入：
  - 计划创建页
  - 土样采集 / 检测结果录入页
  - 施肥处方详情页
  - 施肥执行反馈页
  - 穗肥前监测页 / 施肥效果评估页
  - 审核页（如处方和异常处理要进复核）
- 最小展示字段：
  - 任务类型、地块、阶段、推荐窗口、肥料类型、用量、处方摘要、结果状态
- 最小可编辑字段：
  - 算法补充参数
  - 采样 / 检测结果
  - 人工调整施肥量
  - 执行反馈
  - 施肥效果评估结论
- 是否需要详情页：
  - 需要
- 是否需要审核页：
  - 建议需要
- 成功后应刷新哪些接口：
  - 任务列表
  - 任务详情
  - 计划时间线
  - 处方方案详情
  - 相关审核详情

## 13. 失败兜底

- 缺少输入字段时：
  - 阻断当前链路，并明确缺失字段
- 外部接口 4xx 时：
  - 视为参数不合法或输入结构不完整，记录关键参数并提示人工处理
- 外部接口 5xx / timeout 时：
  - 记录失败事件，允许重试，不自动生成不完整方案
- 数据不完整 / 上下文缺失时：
  - 不进入正式施肥执行，停留在待补数或待审核状态
- 是否重试：
  - 采样点规划、插值、处方算法、长势监测算法可后台重试
- 是否创建通知：
  - 是
- 是否创建人工跟进待办：
  - 建议是
- 需要记录哪些事件或日志：
  - 算法入参摘要
  - 返回分支摘要
  - 处方版本变化
  - 人工调整前后差异

## 14. 测试场景

### 场景 1：新采样新检测后生成三阶段施肥处方

- 输入：
  - 计划创建时勾选采土
  - 采样点规划成功
  - 土样检测结果上传成功
  - 处方算法必填参数齐全
- 预期对象变化：
  - 生成土样采集 / 检测相关对象
  - 生成施肥处方结果
  - 生成施基肥、施分蘖肥和分蘖末期遥感长势监测 `CalendarItem`
- 不应发生：
  - 缺少检测结果时仍生成施肥处方

### 场景 2：复用历史检测结果直接生成施肥处方

- 输入：
  - 选择历史检测结果复用
  - 处方算法参数齐全
- 预期对象变化：
  - 不创建新的土样检测任务
  - 直接生成处方建议
  - 按阶段生成下游施肥事项
- 不应发生：
  - 同时又强制创建新检测链路

### 场景 3：穗肥前长势监测生成变量处方图

- 输入：
  - 穗肥前监测任务完成
  - 长势结果可用
- 预期对象变化：
  - 生成或更新变量穗肥处方图
  - 穗肥 `OperationPlan` 使用变量处方
- 不应发生：
  - 长势结果缺失时静默覆盖原穗肥方案

### 场景 4：施肥效果评估正常收口

- 输入：
  - 任一施肥执行完成
  - 7-10 天后施肥效果评估结果正常
- 预期对象变化：
  - 记录评估结果
  - 不创建新的复核或补施肥建议
- 不应发生：
  - 无异常时仍默认进入人工审核

### 场景 5：施肥效果评估异常转人工判断

- 输入：
  - 施肥效果评估结果为 `warning / fail`
- 预期对象变化：
  - 创建人工处理农事
  - 保留上下文和原因信息
- 不应发生：
  - 直接自动生成后续施肥正式任务

## 15. 待决问题

以下事项已经明确，不再继续作为待决问题挂起：

1. 土样采集和土样检测拆成两个任务，并拆成两个独立 `workflowKey`。
2. 快递单号保留为土样采集环节的可选录入字段，不再放在土样检测环节。
3. 人工审核通过后的施肥处方，直接写正式方案并推进下游任务生成。
4. 独立采样点表与独立土壤检测结果表通过采样点 ID 建关联，并按该关联链路做版本追溯。
5. 再生稻发苗肥、促芽肥暂时不纳入本轮 FDE 主文档。
6. `FER-OPEN-05`：穗肥变量处方图 URL 第一版采用直接公开 URL，系统侧只保存并透传 `OperationPlan.prescriptionMap.url`。
7. `FER-OPEN-06`：施肥效果评估异常触发人工处理农事后，人工处理结果目前仅记录并结束。
8. `FER-OPEN-08`：算法只返回样本点的单位面积施肥量，系统侧负责映射 / 补充为地块维度的单位面积施肥量，不要求算法返回地块绝对施肥总量。
9. 土样采集第一版不生成二维码，土样编号仍按采样点一一对应生成和追溯。
10. 长势监测流程按“业务人员到达农场 -> 执行无人机监测任务 -> 完成后录入执行记录及遥感后续任务 id（影像上传、影像拼接）”处理。
11. M3 / healthy 模式必需字段已确认，按 FDE 字段口径组装算法入参。

当前无继续挂起的 `FER-OPEN-05`、`FER-OPEN-06`、`FER-OPEN-08` 问题。

## 16. 推荐阅读顺序

1. [任务 / 流程 FDE 通用输出模板](F:/workspace/CropFlow/docs/fde/task-flow-fde-output-template.md)
2. [施肥方向任务清单](F:/workspace/CropFlow/docs/workflow/checklists/fertilization-task-checklist.md)
3. [施肥方向](F:/workspace/CropFlow/docs/domain/fertilization.md)
4. [任务流程矩阵](F:/workspace/CropFlow/docs/workflow/task-workflow-matrix.md)
5. `docs/model/data-model.md`
6. `docs/model/data-model-validation.md`

## 17. 当前建议

如果你现在是为了进入开发，我建议按下面 5 项作为开发前检查清单：

```text
1. taskSubtype 以本文对象映射为准：soil_sampling、soil_testing、base_fertilizer、tillering_fertilizer、panicle_fertilizer、tillering_growth_monitoring、effect_evaluation、manual_follow_up
2. 施肥算法接口以 docs/references/raw/施肥算法接口.md 为原始依据，开发入口使用 docs/api/fertilization_prescription_algorithm_api.md
3. `POST /run` 返回结果按本文 10.2 映射到 `OperationPlan.parameters`
4. checklist / workflow matrix / domain / data model 需要统一采用本文 taskSubtype 口径
5. 后续如重新纳入再生稻发苗肥、促芽肥，应另起 FDE 补充，不回填到本轮已冻结主链路
```

## 18. 已读取原始材料

当前这版草稿已经参考以下原始资料：

```text
1. docs/references/raw/土壤检测数据样表.xlsx
2. docs/references/raw/施肥算法接口.md
3. docs/workflow/checklists/fertilization-task-checklist.md
4. docs/domain/fertilization.md
5. docs/workflow/task-workflow-matrix.md
```
