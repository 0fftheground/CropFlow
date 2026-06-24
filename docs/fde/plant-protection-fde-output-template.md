# 植保方向 FDE 输出参考

> 用途：作为“如何把一个植保方向需求梳理到可开发”的参考成品。  
> 范围：覆盖当前已落地的两条主线
> 1. 杂草防治
> 2. 病虫害调查 / 防治 / 人工复核
>
> 使用方式：
> 1. 先用 [任务 / 流程 FDE 通用输出模板](F:/workspace/CropFlow/docs/fde/task-flow-fde-output-template.md) 采访和整理
> 2. 再参考本文档，看植保方向通常需要补齐哪些对象映射、接口分支、调查录入和审核规则
> 3. 最终把稳定事实回写到 `docs/domain/`、`docs/workflow/flows/`、`docs/workflow/task-workflow-matrix.md`、`docs/api/`

## 1. 基本信息

- 业务名称：植保方向农事项闭环
- 建议流程标识：`plant_protection_task_flow`
- 所属业务线 / 模块：Plant Protection / Task Module / Plan Orchestrator / Review Module
- 当前阶段：
  - P1 可开发到 P2 联调
- 适用范围：
  - 水稻种植计划下的杂草防治主线
  - 水稻种植计划下的病虫害调查、防治建议、人工复核主线
- 不适用范围：
  - 执行设备自动回调驱动的闭环
  - 非水稻作物的专属口径
  - 病虫害药后自动继续调查闭环
- 关联角色：
  - 发起方：系统编排器、后台 Job、人工录入人员
  - 执行方：种植户、农服人员、线下调查人员
  - 审核方：农艺师、方案复核人员
  - 结果使用方：任务中心、审核页、执行页、后续编排链路

## 2. 业务目标

- 这条流程解决什么问题：
  - 把植保相关的“调查日期推荐、调查结果录入、防治建议生成、人工复核、正式任务下发、执行后续跟进”整理成可实现的系统闭环
- 系统为什么需要感知它：
  - 植保任务不是单一步骤动作，而是依赖天气、生育期、调查结果、人工判断和外部诊断接口的连续编排过程
- 最终希望输出什么结果：
  - 杂草方向：可追溯的调查、防治、药后调查、补防 / 缓解、服务评价链路
  - 病虫害方向：可追溯的常规 / 突发调查、防治建议合并、theoryPlan 审核、正式防治任务链路

## 3. 闭环结束条件

- 什么情况下视为完成：
  - 杂草方向：服务效果评估满意，或当前分支返回 `no_action` 且无下游事项
  - 病虫害方向：`disease_pest_control` 正式任务和 `OperationPlan` 已生成，当前主链路收口
- 什么情况下转入下一流程：
  - 杂草方向：药前调查进入茎叶除草，执行完成进入药后安全性 / 防效调查，必要时进入补防或药害缓解
  - 病虫害方向：调查结果进入防治建议，审核通过后转入正式执行
- 什么情况下仅记录，不继续推进：
  - 诊断结果为 `no_action`
  - 当前调查被新的建议合并或覆盖，仅保留追溯信息
- 什么情况下转人工：
  - 需要审核正式防治建议
  - 需要调整病虫害 `theoryPlan`
  - 缺少关键上下文、接口返回不可自动推进或业务方需要人工确认

## 4. 触发规则

- 触发来源：
  - 计划创建
  - 关键字段更新
  - 天气刷新
  - 生育期变化
  - 任务到期
  - 调查结果录入
  - 执行完成录入
  - 审核结果回调
- 具体触发事件：
  - 杂草主线
    - `PlantingPlan` 创建 / 播种日期或移栽日期变化触发 `soil_treatment_diagnosis`
    - 天气刷新触发 `weed_survey_date_diagnosis`
    - 药前调查结果录入触发 `weed_treatment_diagnosis`
    - 茎叶除草执行完成触发 `after_treatment_diagnosis`
    - 安全性调查结果录入触发 `injury_mitigation_diagnosis`
    - 防效调查结果录入触发 `additional_treatment_diagnosis`
  - 病虫害主线
    - 计划初始化 / 天气刷新 / 生育期变化触发 `pestDisease.init_regular_survey`
    - 同轮刷新触发 `pest_disease.daily_update`
    - 常规 / 突发调查结果录入触发病虫害防治建议生成
    - 审核通过触发 `pest_disease.adjust_control_window`
- 前置条件：
  - `PlantingPlan` 已存在且作物、阶段、时间上下文可用
  - 对应任务 / 调查对象处于允许录入结果的状态
  - 外部诊断所需字段已具备或可通过系统聚合补齐
- 阻断条件：
  - 缺少关键基础信息
  - 上游对象已失效
  - 同一时点存在更高优先级的待审核建议且不允许并行推进
- 是否允许重算：
  - 是
- 重算触发条件：
  - 计划关键字段变化
  - 天气 / 生育期变化
  - 新调查结果进入
  - 审核调整了建议窗口或轮次
- 重算后旧对象如何处理：
  - `CalendarItem` 可更新、复用或失效
  - 建议态对象可被新的建议替代或合并
  - 已审核后的正式任务不应被同类新建议静默覆盖
- 幂等建议：
  - 以 `plan_id + taskSubtype + recommendation_window/source_event` 作为调查 / 建议去重主键候选
  - 审核回写时以 `review_request_id` 保证一次性派生正式任务

## 5. 输入字段来源

| 字段 | 是否必填 | 来源对象 / 来源系统 | 来源字段 / 录入位置 | 示例 | 缺失时动作 | 备注 |
|---|---|---|---|---|---|---|
| planting_plan_id | 是 | PlantingPlan | id | `pp_1001` | 阻断并报错 | 全链路追溯主键 |
| crop_type | 是 | PlantingPlan | cropType | `rice` | 阻断并报错 | 当前植保口径默认水稻 |
| cultivation_system | 视接口而定 | PlantingPlan / 归一化映射 | cultivationSystem | `早稻` | 阻断或映射后重试 | 杂草 / 病虫害外部接口可能需要标准枚举 |
| farm_id / field_id | 是 | Farm / Field | id | `farm_01` / `field_01` | 阻断并报错 | 用于空间、归属和展示 |
| sowing_date / transplanting_date | 杂草必填 | PlantingPlan | sowingDate / transplantingDate | `2026-03-10` | 阻断当前推荐 | 土壤封闭和药前调查依赖 |
| growth_stage | 常用 | CropStageState | currentStage | `tillering` | 阻断当前推荐或降级 | 多个诊断入口会依赖 |
| weather_window | 常用 | 天气聚合服务 | 聚合结果 | `{daily: [...]}` | 重试 / 转人工 | 日期窗口必须满足算法要求 |
| survey_result_payload | 结果录入时必填 | 人工表单 | 调查结果页 | `{weed_density: ...}` | 等待补录 | 结构因任务类型不同而不同 |
| execution_completion_payload | 执行完成时必填 | 人工表单 | 执行完成页 | `{operation_date: ...}` | 等待补录 | 药后调查推荐依赖 |
| existing_task_intent / review_context | 病虫害合并时常用 | TaskIntent / ReviewRequest | rule_result / payload | `{proposedPlan: ...}` | 不合并，走新建议 | 用于 theoryPlan 合并 |
| source_execution_id | 药后调查常用 | Execution / ExecutionRecord | executionId | `exec_001` | 记录风险并阻断下游生成 | 下游调查需要追溯 |

补充说明：

- 植保方向特别容易遗漏“外部接口需要的标准枚举”和“执行后继续生成下游调查所依赖的执行追溯 id”。
- 杂草与病虫害都不是只靠页面录入完成，很多关键上下文来自计划、天气、生育期和已有建议对象。
- 对外部接口需要的作物制度、阶段、天气窗口，应在系统内统一做归一化，不把映射逻辑散落到页面侧。

## 6. 外部接口 / 规则调用

| interfaceCode / ruleCode | 接口 / 规则名 | 调用时机 | 关键输入 | 关键输出 | 成功后系统动作 | 失败兜底 |
|---|---|---|---|---|---|---|
| `soil_treatment_diagnosis` | 土壤封闭诊断 | 计划创建 / 关键字段变化后 | 计划信息、时间、天气、栽培制度 | 推荐日期、方案建议 | 生成杂草土壤封闭建议态对象 | 记录事件、通知排查 |
| `weed_survey_date_diagnosis` | 杂草药前调查日期推荐 | 天气刷新 / 后台 Job | 计划、生育期、天气 | 调查窗口 / 日期 | 生成或更新 `stem_leaf_weed_pre_survey` `CalendarItem` | 保留旧对象并重试 |
| `weed_treatment_diagnosis` | 杂草防治诊断 | 药前调查结果录入后 | 调查结果、计划、天气 | 5 天后重查 / 防治建议 | 生成下一调查或建议态对象 | 记录失败并等待补录或重试 |
| `after_treatment_diagnosis` | 杂草药后诊断 | 茎叶除草执行完成后 | 执行完成结果、计划 | 安全性调查 / 防效调查日期 | 创建两个药后调查 `CalendarItem` | 记录失败，不自动继续 |
| `injury_mitigation_diagnosis` | 药害缓解诊断 | 安全性调查结果录入后 | 安全性调查结果 | `no_action` / 缓解建议 | 记录无动作或创建建议态对象 | 转人工 |
| `additional_treatment_diagnosis` | 杂草补防诊断 | 防效调查结果录入后 | 防效调查结果 | 无需补防 / 立即补防 / 待缓解后补查 | 创建评价或补防 / 补查对象 | 转人工 |
| `pestDisease.init_regular_survey` | 病虫害常规调查初始化 | 计划初始化 / 天气刷新 / 生育期变化 | 计划、生育期、天气 | `regular_plans` | 生成或更新 `regular_disease_pest_survey` `CalendarItem` | 记录失败并重试 |
| `pest_disease.daily_update` | 病虫害日更检查 | 天气刷新 / 定时任务 | 计划、预警、天气 | 突发调查建议 | 生成 / 合并 / 失效 `sudden_disease_pest_survey` | 记录事件并保持现状 |
| `pest_disease.merge_control_plan` | 病虫害建议合并 | 新调查结果进入且已有待处理建议 | 新旧建议、调查结果 | 合并后的 `theoryPlan` | 替代旧建议并创建新审核对象 | 不合并，保留新旧并转人工 |
| `pest_disease.adjust_control_window` | 审核后窗口重算 | 病虫害审核通过后 | 审核后的 `theoryPlan` | `adjustedPlan`、正式窗口 | 派生 `FarmingTask` 和 `OperationPlan` | 审核留痕并提示人工处理 |

补充说明：

- 病虫害审核的核心不是前端直接改正式 `controlPlan`，而是编辑并提交 `proposedPlan.theoryPlan`。
- 杂草链路既有“推荐调查日期”类接口，也有“诊断后给出后续动作分支”类接口，采访时必须分清接口输出的语义层次。

## 7. 结果分支

| 分支编号 | 触发条件 / 返回特征 | 系统判断 | 下游动作 | 是否人工确认 | 备注 |
|---|---|---|---|---|---|
| `W-01` | 土壤封闭返回建议方案 | 可推进但需确认 | 创建 `TaskIntent` / `ReviewRequest` | 是 | 不直接下发正式任务 |
| `W-02` | 药前调查返回 5 天后重查 | 暂不防治 | 创建下一次调查 `CalendarItem` | 否 | 可能是普通调查或补防前调查 |
| `W-03` | 药前调查返回需茎叶除草 | 进入防治建议 | 创建 `TaskIntent` / `ReviewRequest` | 是 | 审核后生成正式任务 |
| `W-04` | 药后诊断返回安全性 / 防效调查日期 | 继续闭环 | 创建两个下游 `CalendarItem` | 否 | 依赖执行完成结果 |
| `W-05` | 药害缓解返回 `no_action` | 无需继续 | 记录结论 | 否 | 不生成新任务 |
| `W-06` | 药害缓解返回缓解建议 | 需进一步处理 | 创建建议态对象 | 视情况 | 可进入审核 |
| `W-07` | 防效诊断返回立即补防 | 可推进 | 创建补防建议态对象 | 视情况 | 审核后可生成正式补防任务 |
| `W-08` | 防效诊断返回待缓解后补查 | 先回调查 | 创建 `stem_leaf_weed_recontrol_pre_survey` | 否 | 不直接生成补防正式任务 |
| `W-09` | 服务效果评估满意 | 闭环结束 | 记录评价 | 否 | 当前链路收口 |
| `W-10` | 服务效果评估不满意 | 需追补调查 | 创建 `service_effect_survey` 正式任务 | 否 | 当前实现到此结束 |
| `DP-01` | 常规调查窗口初始化成功 | 进入待执行调查 | 创建 / 更新 `regular_disease_pest_survey` | 否 | 来源于后台 Job |
| `DP-02` | 日更检查发现突发风险 | 进入应急调查 | 创建 `sudden_disease_pest_survey` | 否 | 可被合并或失效 |
| `DP-03` | 突发风险已被常规调查覆盖 | 不单独推进 | 合并进现有常规调查 | 否 | 避免重复任务 |
| `DP-04` | 调查结果形成防治建议 | 进入建议态 | 创建 `disease_pest_control` `TaskIntent` | 是 | 当前统一走审核 |
| `DP-05` | 存在已有未关闭建议 | 需合并 | 调用 `merge_control_plan` 后重新审核 | 是 | 以合并后的 theoryPlan 为准 |
| `DP-06` | 结果为 `no_action` | 不正式执行 | 持久化建议结论 | 否 / 视口径 | 保留追溯信息 |
| `DP-07` | 审核通过并调整 theoryPlan | 进入正式执行 | 调用 `adjust_control_window` 生成正式任务和方案 | 是，已完成 | 正式对象来自审核后的 theoryPlan |

补充说明：

- 对植保方向来说，最重要的不是“有没有建议”，而是“建议属于哪一层对象”。
- 当前实现里，很多建议先停留在 `TaskIntent` / `ReviewRequest`，只有审核或规则确认后才进入正式执行对象。

## 8. 对象映射

| 结果 / 动作 | 生成或更新对象 | 关键字段 | 说明 |
|---|---|---|---|
| 杂草药前调查日期推荐 | `CalendarItem` | `taskSubtype`, `scheduledDate`, `sourceRule` | 预备调查事项，不是正式任务 |
| 病虫害常规 / 突发调查建议 | `CalendarItem` | `taskSubtype`, `windowStart`, `windowEnd`, `sourceEventId` | 由后台 Job 维护 |
| 调查结果后的防治建议 | `TaskIntent` | `taskSubtype`, `rule_result`, `source_task_id` | 建议态主对象 |
| 需要人工确认的建议 | `ReviewRequest` | `type`, `payload`, `source_task_intent_id` | 人工决策入口 |
| 杂草正式防治 | `FarmingTask` | `taskSubtype`, `plannedTime`, `title` | 审核后生成 |
| 病虫害正式防治 | `FarmingTask` | `taskSubtype`, `plannedTime`, `targets` | 审核后的 theoryPlan 派生 |
| 作业方案 | `OperationPlan` | `window`, `parameters`, `basis`, `riskNotes` | 正式执行依据 |
| 调查或执行结果留痕 | `EventRecord` / 结果 payload | `payload`, `result`, `sourceObjectId` | 便于审计和重放 |
| 旧建议失效 | 建议态对象状态更新 | `status=invalidated/replaced` | 避免并行脏状态 |

补充说明：

- `CalendarItem` 只表示“预备农事项 / 预备调查”，不能直接充当正式执行入口。
- `FarmingTask` 才是 Execution Module 的入口。
- 病虫害审核页面看到的是 `TaskIntent.rule_result.proposedPlan.theoryPlan`，而不是一个孤立的前端草稿对象。

## 9. 人工录入字段

### 9.1 调查 / 采集 / 填报字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| `survey_date` | date | 是 | 实际调查日期 | `2026-06-24` | `resultPayload.surveyDate` | 杂草 / 病虫害通用 |
| `investigator` | string | 否 | 调查人员 | `张三` | `resultPayload.investigator` | 便于追溯 |
| `weed_density` | number / enum | 杂草常用 | 杂草发生程度 | `3` | `resultPayload.weedDensity` | 药前调查 |
| `weed_stage` | string / enum | 杂草常用 | 草相 / 草龄 | `2-3叶期` | `resultPayload.weedStage` | 药前调查 |
| `injury_level` | number / enum | 安全性调查常用 | 药害程度 | `2` | `resultPayload.injuryLevel` | 进入缓解诊断 |
| `control_effect_level` | number / enum | 防效调查常用 | 防治效果 | `一般` | `resultPayload.controlEffectLevel` | 进入补防诊断 |
| `pest_type` | string / enum | 病虫害常用 | 病虫对象 | `稻飞虱` | `resultPayload.targets[].type` | 可多值 |
| `severity_level` | number / enum | 病虫害常用 | 发生程度 | `中度` | `resultPayload.targets[].severity` | 常规 / 突发调查 |
| `observed_area_ratio` | number | 否 | 受害比例 | `0.35` | `resultPayload.targets[].observedAreaRatio` | 便于阈值判断 |
| `remark` | string | 否 | 现场备注 | `田边更重` | `resultPayload.remark` | 纯补充信息 |

### 9.2 正式执行反馈字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| `operation_date` | datetime | 是 | 实际执行日期 | `2026-06-24T09:00:00+08:00` | `completionPayload.operationDate` | 杂草药后链路依赖 |
| `actual_end_at` | datetime | 否 | 实际完成时间 | `2026-06-24T10:00:00+08:00` | `completionPayload.actualEndAt` | 便于执行留痕 |
| `operator_name` | string | 否 | 执行人 | `李四` | `completionPayload.operatorName` |  |
| `materials_used` | array | 否 | 实际药剂 / 用量 | `[{name: ..., dosage: ...}]` | `completionPayload.materialsUsed` | 可与库存串联 |
| `execution_remark` | string | 否 | 执行备注 | `局部补喷` | `completionPayload.remark` |  |

### 9.3 评价 / 反馈字段

| 字段 | 类型 | 是否必填 | 含义 | 示例 | 建议落点 | 备注 |
|---|---|---|---|---|---|---|
| `is_satisfied` | boolean / enum | 服务评价必填 | 服务效果是否满意 | `true` | `evaluation.result.isSatisfied` | 杂草方向当前已实现 |
| `feedback_reason` | string | 否 | 不满意原因 | `效果不均匀` | `evaluation.result.reason` | 用于决定后续调查 |

## 10. 方案或执行对象最小结构

| 字段 | 是否必填 | 含义 | 来源 | 示例 | 备注 |
|---|---|---|---|---|---|
| `taskSubtype` | 是 | 任务 / 方案子类型 | 固定值 / 规则输出 | `plant_protection.disease_pest_control` | 区分主线 |
| `windowStart` | 否 | 建议开始时间 | 规则 / 审核后重算 | `2026-06-25T06:00:00+08:00` | 可为空 |
| `windowEnd` | 否 | 建议结束时间 | 规则 / 审核后重算 | `2026-06-26T18:00:00+08:00` | 可为空 |
| `parameters` | 是 | 作业参数正文 | 外部接口 / 人工调整 | `{rounds: [...]}` | 病虫害常见为多轮次 |
| `basis` | 否 | 决策依据 | 规则结果 / 调查结果 | `达到防治阈值` | 便于解释 |
| `riskNotes` | 否 | 风险提示 | 外部接口 / 人工 | `降雨前不建议施药` | 展示和审核用 |
| `targets` | 病虫害常用 | 防治对象 | 调查结果 / theoryPlan | `["稻飞虱"]` | 支持多对象 |
| `theoryPlan` | 病虫害审核关键字段 | 审核理论方案 | `TaskIntent.rule_result.proposedPlan` | `{rounds: [...]}` | 先审这个，再派生正式计划 |
| `adjustedPlan` | 病虫害正式对象常用 | 审核后窗口修正结果 | `adjust_control_window` | `{rounds: [...]}` | 后端派生结果 |

补充说明：

- 病虫害方向最关键的是把“理论方案”和“正式执行方案”拆开。
- 杂草方向则更强调“执行完成后是否继续创建下游调查对象”。

## 11. 人工判断规则

- 是否需要人工判断：
  - 需要
- 判断类型建议：
  - `review_weed_control_plan`
  - `review_injury_mitigation_plan`
  - `review_disease_pest_theory_plan`
- 触发原因：
  - 正式防治建议需要确认
  - 药害缓解 / 补防建议有风险或成本
  - 病虫害需要编辑 `theoryPlan.rounds`
- 人工需要看到的上下文：
  - 计划基础信息
  - 地块 / 农场信息
  - 生育期、天气窗口
  - 本次调查结果和来源任务
  - 当前建议的 `rule_result`
  - 如为病虫害，必须展示 `proposedPlan.theoryPlan`
- 候选决策动作：
  - `approve`
  - `reject`
  - `adjust`
  - `no_action`
  - `need_more_info`
- 各决策的系统影响：
  - `approve`：
    - 依据当前建议生成正式 `FarmingTask` 和 `OperationPlan`
  - `reject`：
    - 关闭当前建议，不生成正式执行对象
  - `adjust`：
    - 杂草方向可调整建议参数
    - 病虫害方向应修改 `theoryPlan`，再由后端重算 `adjustedPlan`
  - `no_action`：
    - 持久化人工结论，不继续生成新任务
  - `need_more_info`：
    - 保持待处理状态，提示补充调查或补充上下文

## 12. 页面 / 交互建议

- 这个流程在哪个页面发起或录入：
  - 任务中心
  - 调查结果录入页
  - 执行完成页
  - 病虫害审核页
- 最小展示字段：
  - 任务类型、所属计划、所属地块、推荐日期 / 窗口、建议摘要、来源任务、状态
- 最小可编辑字段：
  - 调查结果字段
  - 执行完成字段
  - 杂草审核建议参数
  - 病虫害 `theoryPlan.rounds`
- 是否需要详情页：
  - 需要
- 是否需要审核页：
  - 需要
- 成功后应刷新哪些接口：
  - 任务列表
  - 任务详情
  - 审核详情
  - 相关计划时间线
- 哪些错误应直接展示给用户：
  - 输入字段缺失
  - 外部接口返回参数错误
  - 对象已失效或已被替代
  - 审核提交结构不合法

## 13. 失败兜底

- 缺少输入字段时：
  - 阻断当前诊断或提交流程，并返回明确缺失字段
- 外部接口 4xx 时：
  - 视为参数或业务上下文不合法，记录请求体和关键映射字段，提示人工排查
- 外部接口 5xx / timeout 时：
  - 记录失败事件，允许后台重试或人工重触发
- 数据不完整 / 上下文缺失时：
  - 不静默生成半成品任务，应停留在待补数或人工处理状态
- 是否重试：
  - 后台推荐类接口可重试
  - 已由人工提交的审核 / 录入动作不应自动重复提交
- 是否创建通知：
  - 是
- 是否创建人工跟进待办：
  - 对关键链路失败建议创建
- 需要记录哪些事件或日志：
  - 外部接口入参与关键映射值
  - 返回分支摘要
  - 对象创建 / 更新 / 失效结果
  - 审核前后 `theoryPlan` 差异

## 14. 测试场景

### 场景 1：杂草药前调查进入正式茎叶除草

- 输入：
  - 已存在 `stem_leaf_weed_pre_survey` 正式调查任务
  - 录入的调查结果满足防治阈值
- 预期对象变化：
  - 生成 `TaskIntent`
  - 生成 `ReviewRequest`
  - 审核通过后生成 `plant_protection.stem_leaf_weed_control` `FarmingTask` 和 `OperationPlan`
- 不应发生：
  - 调查结果录入后直接生成正式执行任务

### 场景 2：杂草茎叶除草执行后进入药后调查

- 输入：
  - `stem_leaf_weed_control` 执行完成
  - 执行完成字段齐全
- 预期对象变化：
  - 调用 `after_treatment_diagnosis`
  - 生成 `rice_safety_survey` 和 `control_effect_survey` 两个 `CalendarItem`
- 不应发生：
  - 缺少执行追溯信息时仍继续生成下游调查

### 场景 3：病虫害常规调查结果与已有建议合并

- 输入：
  - 已存在未关闭的 `disease_pest_control` 建议
  - 新的常规调查结果再次命中防治建议
- 预期对象变化：
  - 调用 `merge_control_plan`
  - 旧建议被替代或失效
  - 新的 `ReviewRequest` 基于合并后的 `theoryPlan`
- 不应发生：
  - 直接平行生成两套未关联的正式防治任务

### 场景 4：病虫害审核调整 theoryPlan 后生成正式任务

- 输入：
  - 审核页对 `theoryPlan.rounds` 做增删改
  - 提交 `adjust`
- 预期对象变化：
  - 后端调用 `adjust_control_window`
  - 生成基于调整后窗口的正式 `FarmingTask` 和 `OperationPlan`
- 不应发生：
  - 前端直接覆盖正式 `controlPlan`

### 场景 5：外部诊断参数不合法

- 输入：
  - 栽培制度枚举不符合接口要求
- 预期对象变化：
  - 当前调用失败
  - 记录失败日志和关键映射值
  - 不生成脏建议对象
- 不应发生：
  - 静默吞错或生成不完整的后续对象

## 15. 待决问题

| questionId | 问题 | 影响范围 | 可选方案 | 需要谁拍板 | 计划何时决定 |
|---|---|---|---|---|---|
| `PP-OPEN-01` | 病虫害正式防治执行完成后，是否要像杂草一样继续自动生成药后调查主线 | 任务编排、页面、测试 | 先不做 / 增加病种专属药后调查 | 业务 + 产品 + 后端 | 后续 phase |
| `PP-OPEN-02` | 杂草缓解和补防建议是否统一强制进入审核 | 审核页、编排逻辑 | 全部强审 / 按风险级别审核 | 业务 + 产品 | 联调期 |
| `PP-OPEN-03` | 不同外部接口对栽培制度、阶段枚举的映射是否应沉淀为统一字典层 | 接口适配、排错 | 分接口映射 / 统一适配层 | 后端 | 尽快 |

## 16. 采访完成标准

当下面这些问题都能回答时，植保方向某条农事项链路基本已达到可开发状态：

```text
1. 该事项属于 CalendarItem、TaskIntent、ReviewRequest 还是正式 FarmingTask 的入口已明确。
2. 外部接口返回的是日期、建议、分支还是正式方案已明确。
3. 调查录入字段、执行完成字段、审核编辑字段已明确。
4. 是否需要人工复核，以及人工能改什么已明确。
5. 重算后旧对象是更新、失效还是替代已明确。
6. 是否继续派生下游调查、补防、评价等后续事项已明确。
7. 失败兜底、关键日志和至少 3 个测试场景已明确。
```

## 17. 推荐阅读顺序

1. [任务 / 流程 FDE 通用输出模板](F:/workspace/CropFlow/docs/fde/task-flow-fde-output-template.md)
2. [植保杂草主线流程](F:/workspace/CropFlow/docs/workflow/flows/plant-protection-weed-loop.md)
3. [植保病虫害调查、防治与复核流程](F:/workspace/CropFlow/docs/workflow/flows/plant-protection-disease-pest-loop.md)
4. `docs/domain/plant-protection.md`
5. `docs/workflow/task-workflow-matrix.md`
6. `docs/api/frontend-plant-protection-api-contract.md`
