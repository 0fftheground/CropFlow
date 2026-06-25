# 施肥方向 FDE 输出初稿

> 用途：作为“如何把施肥方向需求梳理到可开发”的参考初稿。  
> 当前定位：不是最终冻结事实，而是基于现有 checklist、workflow 矩阵和方向说明生成的第一版 FDE 输出。  
> 使用方式：
> 1. 先按本文补齐缺失口径、分支和字段
> 2. 再把已冻结的系统事实回写到 `docs/domain/`、`docs/workflow/`、`docs/api/`
> 3. 未冻结项继续保留在“待决问题”里，不要提前伪装成正式系统规则

## 1. 基本信息

- 业务名称：施肥方向农事项闭环
- 建议流程标识：`fertilization_task_flow`
- 所属业务线 / 模块：Fertilization / Task Module / Plan Orchestrator / Review Module / Material & Inventory Module
- 当前阶段：
  - P0 调研到 P1 可开发之间
- 适用范围：
  - 水稻种植计划下的测土、施肥处方、基肥 / 分蘖肥 / 穗肥、穗肥前长势监测与变量处方、穗肥后效果抽查
  - 再生稻场景下的发苗肥、促芽肥
- 不适用范围：
  - 复杂库存结转和完整仓储管理
  - 自动设备闭环执行
  - 所有作物通用施肥口径
- 关联角色：
  - 发起方：系统编排器、后台 Job、人工操作人员
  - 执行方：农服人员、实验室、无人机服务人员、种植户
  - 审核方：农艺师、处方审核人员
  - 结果使用方：任务中心、处方查看页、执行反馈页、后续编排链路

## 2. 业务目标

- 这条流程解决什么问题：
  - 把“采土测土 -> 施肥处方 -> 分阶段施肥 -> 穗肥前监测 -> 变量穗肥 -> 穗肥后效果抽查”整理成可以开发和联调的系统闭环
- 系统为什么需要感知它：
  - 施肥不是单次作业，而是依赖采样、检测、算法处方、阶段窗口、长势监测和执行反馈的连续链路
- 最终希望输出什么结果：
  - 可追溯的施肥处方
  - 分阶段施肥 `CalendarItem / FarmingTask / OperationPlan`
  - 可选的人工审核、变量处方图、效果抽查和异常后续处理入口

## 3. 闭环结束条件

- 什么情况下视为完成：
  - 常规场景下，施基肥 / 施分蘖肥 / 施穗肥及必要的效果抽查完成，且无异常后续动作
- 什么情况下转入下一流程：
  - 土样采集完成后转土样检测
  - 土样检测完成或复用历史检测结果后转施肥处方生成
  - 施肥处方保存后转分阶段施肥 `CalendarItem`
  - 穗肥前长势监测完成后转变量穗肥处方
  - 穗肥执行完成后转效果抽查
- 什么情况下仅记录，不继续推进：
  - 效果抽查结果正常，当前不触发后续复核或补施肥
- 什么情况下转人工：
  - 施肥处方需要人工审核或人工调整
  - 穗肥前监测发现异常但算法无法直接给出变量处方
  - 效果抽查异常，需要人工判断是否复核、补施肥或仅记录

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
  - `soil_test`：计划创建时人工选择新增采土任务
  - `prescription_generation`：历史检测数据复用或新检测结果上传完成
  - `base / tillering / panicle`：施肥处方就绪后，由规则或阶段窗口生成对应 `CalendarItem`
  - `panicle_variable_prescription`：施肥处方完成后，穗肥前到达监测窗口
  - `panicle_fertilizer_effect_check`：施穗肥完成后 7-10 天
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
  - 土样检测结果更新
  - 算法参数补录
  - 人工调整施肥处方
  - 长势监测重新生成变量处方
- 重算后旧对象如何处理：
  - 施肥处方建议：
    - 当前优先理解为“旧处方失效 / 新处方替代”，但是否需要保留版本仍待确认
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
| sampling_points | 土样采集必填 | 采样点规划算法 | 算法返回 | `[{pointId: ...}]` | 阻断采样任务 | 采样点结构待冻结 |
| soil_sample_ids | 土样检测必填 | 土样采集任务 | 采样结果 | `["S-001"]` | 阻断检测任务 | 是否系统内生成二维码待确认 |
| soil_test_result | 处方生成必填 | 实验室检测 / 历史复用 | 结果上传 | `{国标PH: 6.83, 有机质: 1.38, 有效磷-M3: 4.007, ...}` | 阻断处方生成 | 已从 `docs/references/raw/土壤检测数据样表.xlsx` 提取样表字段 |
| target_yield | 是 | 人工补录 / 规则 | 页面录入 | `400` | 等待补录 | 施肥算法接口要求单位为 `kg/亩` |
| fertilization_algorithm_params | 常用 | 人工补录 / 系统聚合 | 页面录入 / 聚合结果 | `{waysType: "M3", varietyType: "0", riceType: "4"}` | 等待补录 | 已从 `docs/references/raw/施肥算法接口.md` 提取核心参数 |
| growth_monitoring_result | 变量穗肥必填 | 长势监测算法 | 监测结果 | `{zones: [...]}` | 阻断变量穗肥 | 输出口径待补 |
| execution_feedback | 效果抽查常用 | 执行完成页 | 反馈录入 | `{operationDate: ...}` | 不生成下游抽查 | 至少需要施穗肥完成记录 |

补充说明：

- 当前最缺的是“哪些检测字段第一版必须入库”和“算法返回结果如何落到 `OperationPlan.parameters / prescriptionMap`”。
- 施肥方向和植保不同，前置数据更偏离散化结构化字段，而不是单次调查结果。
- 变量穗肥场景需要明确处方图 / 分区 / 插值区的表达方式。

## 6. 外部接口 / 规则调用

| interfaceCode / ruleCode | 接口 / 规则名 | 调用时机 | 关键输入 | 关键输出 | 成功后系统动作 | 失败兜底 |
|---|---|---|---|---|---|---|
| `samplingPointPlanningAlgorithm` | 采样点规划算法 | 采土任务创建后 | 地块范围、采样规则 | 采样点清单 | 创建采样点和土样标识 | 转人工生成采样点 |
| `soilInterpolationAlgorithm` | 土壤插值算法 | 检测结果回传后 | 采样点检测结果、地块范围 | 插值后田块指标 | 供处方生成使用 | 保留点位结果，转人工 |
| `fertilizerPrescriptionAlgorithm` | 施肥处方算法 `POST /run` | 土样检测结果就绪或历史数据复用后 | `waysType`、`targetYield`、`varietyType`、`riceType`、`fertilizerA/B/C`、`excelData` | 基肥 / 分蘖肥 / 穗肥处方、N/P/K 分配比例、采样点级推荐总量 | 生成处方建议 / OperationPlan 参数正文 | 记录失败并等待补数 |
| `growthMonitoringAlgorithm` | 长势监测算法 | 穗肥前 / 穗肥后监测 | 影像、区域范围 | 长势结果 / 异常区域 | 提供变量处方或效果抽查依据 | 转人工判断 |
| `panicleVariablePrescriptionAlgorithm` | 变量穗肥处方算法 | 穗肥前长势结果可用后 | 长势结果、地块范围、穗肥规则 | 变量处方图 / 分区施肥量 | 更新穗肥作业方案 | 仅保留长势结果，不自动生成变量处方 |
| `farmingRuleLibrary` | 农事规则库 | 施基肥 / 施分蘖肥 / 施穗肥窗口生成时 | 生育期、种植制度、阶段规则 | 推荐日期 / 时间窗 | 创建施肥 `CalendarItem` | 保留待定，人工处理 |

补充说明：

- 施肥处方接口当前正式文档在 `docs/references/raw/施肥算法接口.md`，主入口是 `POST /run`。
- 当前接口返回的是“采样点级”处方结果，不是直接的田块级正式执行方案；系统侧还需要补“采样点到田块插值 / 聚合”的转换口径。
- 是否所有处方都必须先人工审核，目前没有冻结，建议保留为待决问题。

## 7. 结果分支

| 分支编号 | 触发条件 / 返回特征 | 系统判断 | 下游动作 | 是否人工确认 | 备注 |
|---|---|---|---|---|---|
| `F-01` | 采样点规划成功 | 可推进 | 创建土样采集任务和采样点清单 | 否 | 任务级 |
| `F-02` | 采样点规划失败 | 不可自动推进 | 转人工补点位 | 是 |  |
| `F-03` | 土样检测结果齐全 | 可生成处方 | 进入处方生成 | 否 |  |
| `F-04` | 复用历史检测数据 | 可生成处方 | 跳过新检测，直接进入处方生成 | 视口径 | 是否要求人工确认复用待定 |
| `F-05` | 处方算法成功返回三阶段处方 | 可推进 | 保存处方并生成基肥 / 分蘖肥 / 穗肥 `CalendarItem` | 视口径 | 审核是否必需待定 |
| `F-06` | 处方算法成功但参数不全 / 风险高 | 不可自动下发 | 创建 `ReviewRequest` 或待补录待办 | 是 | 当前建议保守处理 |
| `F-07` | 穗肥前长势监测正常且变量处方生成成功 | 可推进 | 更新穗肥方案为变量处方 | 视口径 | 可能直接更新现有穗肥 `OperationPlan` |
| `F-08` | 长势监测异常但无法直接给出处方 | 需人工判断 | 创建 `ReviewRequest` | 是 |  |
| `F-09` | 穗肥后效果抽查正常 | 闭环收口 | 记录结果，无后续动作 | 否 |  |
| `F-10` | 穗肥后效果抽查异常 | 需后续处理 | 创建 `ReviewRequest` / Feedback / 后续施肥建议 | 是 | 当前未冻结 |

## 8. 对象映射

| 结果 / 动作 | 生成或更新对象 | 关键字段 | 说明 |
|---|---|---|---|
| 采样点规划结果 | `OperationPlan` / 辅助结果对象 / EventRecord | `samplingPoints` | 当前系统里是否要落独立采样点表仍待定 |
| 土样采集任务 | `CalendarItem` / `FarmingTask` | `taskSubtype=fertilization.soil_test` | checklist 当前把采土和测土放在一条大链路里 |
| 土样检测结果 | `ExecutionRecord` / `EventRecord` / 外部数据快照 | `resultPayload` | 处方生成的直接输入 |
| 施肥处方生成结果 | `TaskIntent` / `OperationPlan` | `taskSubtype=prescription_generation`, `parameters`, `prescriptionMap` | 是否先进入审核待定 |
| 施基肥 / 施蘖肥 / 施穗肥预备事项 | `CalendarItem` | `taskSubtype=base/tillering/panicle` | 仍是预备事项，不是正式任务 |
| 施肥正式执行 | `FarmingTask` | `plannedTime`, `taskSubtype` | 到期后由 `TaskDueCheckJob` 生成 |
| 施肥作业方案 | `OperationPlan` | `operationWindow`, `parameters`, `prescriptionMap`, `riskNotes` | 正式执行依据 |
| 穗肥前监测结果 | `ExecutionRecord` / `FieldConditionReported` | `monitorPurpose=panicle_variable_prescription` | 变量穗肥输入 |
| 效果抽查结果 | `Feedback` / `Evaluation` / `FieldConditionReported` | `resultPayload` | 是否总是触发复核待定 |
| 异常后人工判断 | `ReviewRequest` | `type`, `payload`, `contextRefs` | 变量处方异常或效果异常时使用 |

补充说明：

- `WF_SOIL_TEST` 在矩阵里当前是单个 workflowKey，但 checklist 里分成“土样采集 + 土样检测”两个子步骤；系统实现时可能仍需要拆两个任务节点。
- 处方生成最可能落在 `TaskIntent / ReviewRequest / OperationPlan` 这一层，而不是直接生成正式执行任务。

## 9. 人工录入字段

### 9.1 调查 / 采集 / 填报字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| sample_date | date | 采样时必填 | 实际采样日期 | `2026-06-25` | `resultPayload.sampleDate` |  |
| sample_operator | string | 否 | 采样人员 | `张三` | `resultPayload.operatorName` |  |
| sample_point_results | array | 采样时常用 | 采样点结果 / 土样编号 | `[{pointId:..., sampleId:...}]` | `resultPayload.points` | 结构待定 |
| logistics_no | string | 土样检测可能必填 | 快递单号 | `SF123...` | `resultPayload.logisticsNo` | checklist 里是待确认触发条件 |
| soil_test_result | json | 检测后必填 | 检测结果正文 | `{国标PH: 6.83, Buffer PH: 7.04, 有机质: 1.38, 有效磷-M3: 4.007, 有效钾-M3: 103.551}` | `resultPayload.soilTestResult` | 样表还包含有效钙 / 镁 / 铁 / 锌 / 铜 / 硼 / 锰 / 硫 / 铝 / 钠 / 硅等字段 |
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
| abnormal_area | string / json | 否 | 异常区域 | `zone-3` | `evaluation.result.abnormalArea` |  |
| suspected_reason | string / enum | 否 | 异常原因猜测 | `缺肥 / 积水 / 非施肥原因` | `evaluation.result.reason` | 可人工判断 |
| follow_up_suggestion | string | 否 | 后续建议 | `补施穗肥` | `feedback.result.followUpSuggestion` |  |

## 10. 方案或执行对象最小结构

| 字段 | 是否必填 | 含义 | 来源 | 示例 | 备注 |
|---|---|---|---|---|---|
| taskSubtype | 是 | 施肥类型 | 规则 / 固定值 | `fertilization.base` | 区分阶段 |
| operationWindowStart | 否 | 建议开始时间 | 农事规则 / 算法 | `2026-07-01T06:00:00+08:00` |  |
| operationWindowEnd | 否 | 建议结束时间 | 农事规则 / 算法 | `2026-07-03T18:00:00+08:00` |  |
| parameters | 是 | 施肥方案正文 | 处方算法 | `{sectionId: "...", project: [...], avgData: {...}, nRatio: {...}, pRatio: {...}, kRatio: {...}}` | 现已可按接口返回结构起草 |
| prescriptionMap | 否 | 变量处方图 | 变量穗肥算法 | `{zones:[...]}` | 当前待冻结 |
| operationArea | 否 | 作用面积 | 计划 / 算法 | `12.5ha` |  |
| basis | 否 | 方案依据 | 检测 / 监测 / 规则 | `soil_test + target_yield` |  |
| riskNotes | 否 | 风险提示 | 算法 / 人工 | `雨前不建议施肥` |  |
| acceptanceCriteria | 否 | 验收标准 | 业务约定 | `撒施均匀，无明显漏施` | 当前缺明确口径 |

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
| 国标PH | number | 高 | 土壤 pH | `6.83` | 第一版建议必填 |
| Buffer PH | number | 中 | Buffer pH | `7.04` | `waysType=M3/healthy` 可能使用 |
| 有机质 | number | 高 | 有机质含量 | `1.38 %` | 第一版建议必填 |
| 有效钾-M3 | number | 高 | 有效钾 | `103.551 mg/kg` | 第一版建议必填 |
| 有效钙-M3 | number | 中 | 有效钙 | `2163.829 mg/kg` | |
| 有效钠-M3 | number | 低 | 有效钠 | `134.153 mg/kg` | 原接口文档未提及 |
| 有效镁-M3 | number | 中 | 有效镁 | `677.466 mg/kg` | |
| 有效铝-M3 | number | 低 | 有效铝 | `796.975 mg/kg` | |
| 有效铁-M3 | number | 低 | 有效铁 | `158.197 mg/kg` | |
| 有效磷-M3 | number/string | 高 | 有效磷 | `4.007 mg/kg` | 第一版建议必填 |
| 有效锌-M3 | number | 低 | 有效锌 | `1.217 mg/kg` | |
| 有效硼-M3 | number | 低 | 有效硼 | `0.136 mg/kg` | |
| 有效锰-M3 | number | 低 | 有效锰 | `148.796 mg/kg` | |
| 有效硫-M3 | number | 低 | 有效硫 | `20.910 mg/kg` | |
| 有效铜-M3 | number | 低 | 有效铜 | `2.418 mg/kg` | |
| 有效硅-M3 | number | 低 | 有效硅 | `0.370 mg/kg` | |

当前建议：

```text
1. 第一版先明确哪些字段是算法强依赖，不要一次把全表都做成强校验。
2. 建议至少把样品编号、地块编号、国标PH、有机质、有效磷-M3、有效钾-M3 作为优先核对字段。
3. Buffer PH、有效钙-M3、有效镁-M3 是否属于 M3/healthy 模式必填，需要再和算法方确认。
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
| excelData | 是 | 土壤检测结果数组 | `[{采样点ID: ..., 国标PH: ...}]` | 采样点级输入 |

### 响应字段

| 接口字段 | 建议系统落点 | 示例 | 备注 |
|---|---|---|---|
| sectionId | `OperationPlan.parameters.samplePointPlans[].sectionId` | `344ecf...` | 采样点 id |
| sectionCropsId | `OperationPlan.parameters.samplePointPlans[].sectionCropsId` | `0` | 当前看是固定值 |
| nRatio / pRatio / kRatio | `OperationPlan.parameters.samplePointPlans[].nutrientRatio` | `{base:5,tiller:3,ear:2}` | 表达三阶段 N/P/K 分配比例 |
| avgData | `OperationPlan.parameters.samplePointPlans[].avgData` | `{avgOfN:"12.0_kg/亩"}` | 建议保留原始单位字符串 |
| project | `OperationPlan.parameters.samplePointPlans[].project` | `[{fertilizerTypeName:"基肥", ...}]` | 当前最核心输出 |
| NPK | `OperationPlan.parameters.samplePointPlans[].npkMapping` | `[{N:"尿素"}]` | 供处方图或页面解释使用 |

补充说明：

```text
1. 当前接口返回的是采样点级结果，系统还没有最终确定如何聚合成田块级正式施肥方案。
2. 如果第一版不做 prescriptionMap，也建议先把采样点级 project 原样保存在 parameters 里。
3. `project[].fertilizerList[]` 已经足够支撑前端展示“阶段 -> 肥料名称 -> 用量 -> 比例 -> 单位”。
```

## 11. 人工判断规则

- 是否需要人工判断：
  - 建议需要，但范围未完全冻结
- 判断类型建议：
  - `review_fertilization_prescription`
  - `review_panicle_variable_prescription`
  - `review_fertilization_effect_exception`
- 触发原因：
  - 处方算法输出需要人工确认
  - 人工调整施肥量
  - 变量穗肥图异常或原因不清
  - 效果抽查异常
- 人工需要看到的上下文：
  - 计划、地块、品种、生育期
  - 土样 / 检测结果
  - 处方参数与算法依据
  - 历史施肥执行记录
  - 穗肥前 / 穗肥后长势监测结果
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

## 12. 页面 / 交互建议

- 这个流程在哪个页面发起或录入：
  - 计划创建页
  - 土样采集 / 检测结果录入页
  - 施肥处方详情页
  - 施肥执行反馈页
  - 穗肥前监测 / 穗肥后抽查页
  - 审核页（如处方和异常处理要进复核）
- 最小展示字段：
  - 任务类型、地块、阶段、推荐窗口、肥料类型、用量、处方摘要、结果状态
- 最小可编辑字段：
  - 算法补充参数
  - 采样 / 检测结果
  - 人工调整施肥量
  - 执行反馈
  - 效果抽查结论
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
  - 生成施基肥、施分蘖肥、施穗肥 `CalendarItem`
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

### 场景 4：穗肥后效果抽查正常收口

- 输入：
  - 施穗肥执行完成
  - 7-10 天后效果抽查结果正常
- 预期对象变化：
  - 记录抽查结果
  - 不创建新的复核或补施肥建议
- 不应发生：
  - 无异常时仍默认进入人工审核

### 场景 5：效果抽查异常转人工判断

- 输入：
  - 效果抽查结果为 `warning / fail`
- 预期对象变化：
  - 创建 `ReviewRequest` 或异常待办
  - 保留上下文和原因信息
- 不应发生：
  - 直接自动生成后续施肥正式任务

## 15. 待决问题

| questionId | 问题 | 影响范围 | 可选方案 | 需要谁拍板 | 计划何时决定 |
|---|---|---|---|---|---|
| `FER-OPEN-01` | 土样采集和土样检测是一个 workflowKey 下的两个步骤，还是两类独立任务 | Task 定义、页面、编排 | 一个 workflow / 两个 workflow | 产品 + 架构 + 后端 | FDE 收口阶段 |
| `FER-OPEN-02` | 土样检测的触发条件是否真的是“快递单号上传” | 页面录入、任务推进 | 物流驱动 / 结果上传驱动 | 业务 + 产品 | FDE 收口阶段 |
| `FER-OPEN-03` | 施肥处方生成是否必须进入人工审核 | Review、任务生成 | 强审 / 风险时审核 / 不审核 | 产品 + 架构 + 后端 | 开发前 |
| `FER-OPEN-04` | 采样点、土样、检测结果是否需要独立表结构 | 数据模型、接口 | 独立表 / 先放 payload | 核心后端 | 开发前 |
| `FER-OPEN-05` | `prescriptionMap` 第一版是否必做 | API、前端、方案结构 | 必做 / 仅穗肥做 / 后置 | 产品 + 架构 + 后端 | 开发前 |
| `FER-OPEN-06` | 效果抽查异常后是生成复核、补施肥建议，还是只记录反馈 | Workflow、Review、Task | 复核 / 新建议 / 仅反馈 | 产品 + 架构 + 后端 | 联调前 |
| `FER-OPEN-07` | 再生稻发苗肥、促芽肥是否要纳入本轮 FDE 主文档 | 范围控制 | 纳入 / 单独补充 | 业务 + 产品 | FDE 收口阶段 |
| `FER-OPEN-08` | 施肥处方接口返回的是采样点级结果，系统如何形成田块级正式方案 | API 映射、OperationPlan、插值逻辑 | 直接按采样点保存 / 插值后生成田块级处方 / 同时保留两层 | 产品 + 架构 + 后端 + 算法 | 开发前 |

## 16. 推荐阅读顺序

1. [任务 / 流程 FDE 通用输出模板](F:/workspace/CropFlow/docs/fde/task-flow-fde-output-template.md)
2. [施肥方向任务清单](F:/workspace/CropFlow/docs/workflow/checklists/fertilization-task-checklist.md)
3. [施肥方向](F:/workspace/CropFlow/docs/domain/fertilization.md)
4. [任务流程矩阵](F:/workspace/CropFlow/docs/workflow/task-workflow-matrix.md)
5. `docs/model/data-model.md`
6. `docs/model/data-model-validation.md`

## 17. 当前建议

如果你现在是为了尽快推进施肥 FDE，我建议下一轮优先补这 5 块：

```text
1. 先把土壤检测样表字段分成“第一版必填 / 可选保留”
2. 先冻结 waysType / varietyType / riceType 的前后端枚举口径
3. 明确 `POST /run` 的返回结果怎样映射到 `OperationPlan.parameters`
4. 明确采样点级处方如何转田块级处方 / 变量处方图
5. 明确处方审核和效果抽查异常的人工决策口径
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
