# 前端方向

> 本文档从团队分工总览中拆出，用于单独说明前端方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐页面信息架构和字段需求，而不是立即交付正式页面代码。

当前如果要支持当前植保链路联调，请优先阅读：

```text
docs/frontend/plant-protection-handoff.md
```

该文档只保留“当前后端已实现、前端可直接接入”的页面需求和接口契约。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 前端 | 页面清单和信息架构 | 页面表 / 信息架构图 | 产品 / 架构负责人 |
| 前端 | 核心页面低保真原型 | 原型图 / 线框图 | 产品 / 架构负责人 |
| 前端 | 页面字段需求清单 | 字段表 | 核心后端 |
| 前端 | mock 数据需求说明 | 需求说明 | 核心后端 |
| 前端 | 页面与接口依赖关系表 | 对照表 | 核心后端 |
| 前端 | 关键组件说明 | 组件说明 | 产品 / 架构负责人、核心后端 |
| 前端 | 第一条闭环演示流程 | 页面流转说明 | 产品 / 架构负责人 |
| 前端 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 计划创建页面。
2. 计划详情页面。
3. 农事项日历 / CalendarItem 列表。
4. FarmingTask 列表和详情。
5. OperationPlan 查看。
6. ExecutionRecord 执行反馈录入和查看。
7. Evaluation / Feedback 查看。
8. ReviewRequest 人工复核。
9. 植保补防人工确认页面。
10. 遥感监测结果查看页面。
11. 库存入库和库存列表的最小页面。
```

## 需要覆盖的页面能力

| 页面 / 能力 | 说明 |
|---|---|
| 计划创建 | 输入计划基础字段，提交后查看初始化结果 |
| 计划详情 | 展示当前生育期、农事项、任务、反馈和复核 |
| 农事项日历 | 区分 CalendarItem 和 FarmingTask，不把预备农事项当执行入口 |
| 任务详情 | 展示 FarmingTask、OperationPlan、执行状态、历史方案 |
| 作业方案 | 展示不同方向的 parameters、prescriptionMap、operationArea |
| 执行反馈 | 支持人工录入执行结果、附件、异常说明 |
| 评价反馈 | 展示 Evaluation / Feedback，标识是否需要复核 |
| 人工复核 | 处理 approve / reject / adjust / no_action / need_more_info |
| 遥感监测 | 展示缺苗识别、长势监测、异常点位、处方图等结果 |
| 库存 | 药剂 / 肥料入库、库存列表、可用物料查看 |

## 当前阶段非代码任务

```text
1. 页面清单和信息架构。
2. 核心页面低保真原型。
3. 页面字段需求清单。
4. mock 数据需求说明。
5. 页面与接口依赖关系表。
6. 关键组件说明：
   包括方案展示、执行反馈录入、复核处理 3 类组件要展示或录入什么信息。
7. 第一条垂直闭环的前端演示流程。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
9. 字段和对象语义对齐：
   页面字段命名、对象语义和状态口径需遵循总文档中的统一关键词定义。
```

### 直接提交模板

#### 1. 页面清单和信息架构表

```md
| pageKey | pageName | entry | primaryObjects | primaryActions | upstreamPages | downstreamPages | notes |
|---|---|---|---|---|---|---|---|
```

#### 2. 核心页面低保真原型提交清单

```md
| pageKey | pageName | prototypeType | mustShowSections | mustSupportActions | notes |
|---|---|---|---|---|---|
| plan_create | 计划创建 | wireframe | 基础表单 / 提交结果 | 创建计划 |  |
| plan_detail | 计划详情 | wireframe | 生育期 / CalendarItem / 任务 / 反馈 / 复核 | 查看详情 / 跳转列表 |  |
| task_detail | 任务详情 | wireframe | FarmingTask / OperationPlan / 执行状态 / 历史记录 | 查看方案 / 去反馈 |  |
| execution_feedback | 执行反馈 | wireframe | 执行结果 / 附件 / 异常说明 | 提交反馈 |  |
| review_request | 复核处理 | wireframe | 触发原因 / 决策输入 / 候选动作 | approve / reject / adjust / no_action / need_more_info |  |
```

#### 3. 页面字段需求清单

```md
| pageKey | section | field | displayOrInput | required | sourceObject | sourceField | missingBackendDefinition | notes |
|---|---|---|---|---|---|---|---|---|
```

#### 4. mock 数据需求说明表

```md
| mockKey | usedByPage | objectType | requiredFields | sampleState | notes |
|---|---|---|---|---|---|
```

#### 5. 页面与接口依赖关系表

```md
| pageKey | pageName | action | apiOrDataDependency | method | status | fallbackPlan | notes |
|---|---|---|---|---|---|---|---|
```

#### 6. 关键组件说明表

```md
| componentKey | componentName | usedByPages | inputData | outputAction | states | notes |
|---|---|---|---|---|---|---|
| operation_plan_panel | 方案展示组件 | task_detail | OperationPlan / basis / riskNotes | 无或查看详情 | loading / empty / ready |  |
| execution_feedback_form | 执行反馈录入组件 | execution_feedback | FarmingTask / execution form schema | submit feedback | loading / editing / submitted / error |  |
| review_decision_panel | 复核处理组件 | review_request | ReviewRequest / decisionInput / candidateActions | submit resolution | loading / ready / submitted |  |
```

#### 7. 第一条闭环演示流程表

```md
| stepNo | pageKey | trigger | userAction | expectedResult | dependsOn | notes |
|---|---|---|---|---|---|---|
```

#### 8. 待决问题清单

```md
| questionId | question | impact | options | owner | targetDecisionDate | status | notes |
|---|---|---|---|---|---|---|---|
```

## 植保前端建议稿

以下内容不是直接从 `weed_diagnosis_api.md` 逐字提取，而是基于当前对象模型、植保主文档和已确认口径整理的前端建议稿，用于先推动 P1 页面定义。

### 1. 页面清单和信息架构建议稿

| pageKey | pageName | entry | primaryObjects | primaryActions | upstreamPages | downstreamPages | notes |
|---|---|---|---|---|---|---|---|
| `plan_detail` | 计划详情 | 计划列表 / 创建计划后跳转 | `PlantingPlan` / `CropStageState` / `CalendarItem` / `FarmingTask` / `SystemNotification` | 查看状态、跳转农事项、查看提醒 | `plan_create` | `calendar_list` / `task_detail` / `evaluation_entry` | 建议在该页展示气象或算法失败状态 |
| `calendar_list` | 农事项日历 | 计划详情 | `CalendarItem` | 查看推荐时间、区分预备事项和正式任务 | `plan_detail` | `task_detail` | 杂草链路重点展示土壤封闭、药前调查、药后调查 |
| `task_detail` | 任务详情 | 计划详情 / 任务列表 | `FarmingTask` / `OperationPlan` / `EventRecord` | 查看方案、进入反馈、查看历史 | `plan_detail` / `calendar_list` | `execution_feedback` / `review_request` | 补防通过后的茎叶除草也复用此页 |
| `survey_entry` | 调查录入 | 任务详情 | `FarmingTask` / 调查表单 | 提交药前调查、药后调查结果 | `task_detail` | `task_detail` / `review_request` | 药前与药后调查可共用页面骨架 |
| `execution_feedback` | 执行反馈 | 任务详情 | `ExecutionRecord` / `Feedback` | 提交执行结果、附件、异常说明 | `task_detail` | `plan_detail` | 适用于土壤封闭、茎叶除草、补防 |
| `review_request` | 人工复核 | 计划详情 / 任务详情 | `ReviewRequest` / `OperationPlan` / 调查结果 | approve / reject / adjust / no_action / need_more_info | `plan_detail` / `task_detail` | `task_detail` / `plan_detail` | 主要用于立即补防和药害缓解 |
| `evaluation_entry` | 服务评价录入 | 计划详情 / 服务评价入口 | `FarmingTask` / `ExecutionRecord` | 提交满意度、评价人、联系方式 | `plan_detail` | `service_effect_survey` / `plan_detail` | 当前后端复用 `POST /tasks/{id}/survey-results`；满意则结束，不满意进入服务效果调查 |
| `service_effect_survey` | 服务效果调查 | 服务评价不满意后 | `FarmingTask` / `ExecutionRecord` | 录入现场实际情况、原因和备注 | `evaluation_entry` | `plan_detail` | 当前以人工录入为主，录入后链路结束 |

### 2. 页面字段缺口建议稿

| pageKey | section | field | displayOrInput | required | sourceObject | sourceField | missingBackendDefinition | notes |
|---|---|---|---|---|---|---|---|---|
| `plan_detail` | 系统提醒 | 气象 / 算法异常状态 | display | 否 | `SystemNotification` | status / message | 否 | 已有建议口径，待对象字段最终命名 |
| `calendar_list` | 农事项列表 | 推荐日期 | display | 是 | `CalendarItem` | recommendedAt / dueAt | 是 | 字段名为建议口径 |
| `task_detail` | 方案卡片 | 防治对象 | display | 否 | `OperationPlan` | parameters.controlTarget | 否 | 来源已明确 |
| `task_detail` | 方案卡片 | 风险提示 | display | 否 | `OperationPlan` | riskNotes | 是 | 建议字段，非接口直出 |
| `survey_entry` | 药前调查表单 | 稗草 / 千金子 / 阔叶草 / 莎草调查项 | input | 是 | `ExecutionRecord` | resultPayload.* | 否 | 来源已明确 |
| `execution_feedback` | 执行反馈表单 | 执行结果 | input | 是 | `ExecutionRecord` | executionResult | 是 | 建议字段 |
| `execution_feedback` | 执行反馈表单 | 实际开始 / 结束时间 | input | 否 | `ExecutionRecord` | actualStartTime / actualEndTime | 是 | 建议字段 |
| `execution_feedback` | 执行反馈表单 | 异常说明 | input | 否 | `ExecutionRecord` | exceptionNote | 是 | 建议字段 |
| `review_request` | 复核面板 | 候选动作 | display / input | 是 | `ReviewRequest` | candidateActions | 是 | 建议字段 |
| `review_request` | 复核面板 | 复核备注 | input | 否 | `ReviewRequest` | decisionNote | 是 | 建议字段 |
| `evaluation_entry` | 服务评价 | 是否满意 | input | 是 | `Evaluation` | result.isSatisfied | 否 | 已有最小口径 |
| `evaluation_entry` | 服务评价 | 评价人 / 联系方式 | input | 是 | `Evaluation` | evaluatorName / contactInfo | 是 | 建议字段命名 |

### 3. mock 数据需求建议稿

| mockKey | usedByPage | objectType | requiredFields | sampleState | notes |
|---|---|---|---|---|---|
| `mock_plan_detail_weed` | `plan_detail` | `PlantingPlan + CalendarItem + FarmingTask + SystemNotification` | 计划基础字段、当前生育期、土壤封闭/药前调查/药后调查、异常提醒 | `active_with_notifications` | 建议稿 |
| `mock_task_detail_weed_control` | `task_detail` | `FarmingTask + OperationPlan` | 任务状态、推荐日期、方案参数、依据摘要 | `ready_for_execution` | 建议稿 |
| `mock_survey_before_treatment` | `survey_entry` | `ExecutionRecord form schema` | 药前调查字段 | `editable` | 建议稿 |
| `mock_survey_after_treatment` | `survey_entry` | `ExecutionRecord form schema` | 药后调查字段 | `editable` | 建议稿 |
| `mock_review_immediate_control` | `review_request` | `ReviewRequest + OperationPlan + survey summary` | 触发原因、候选动作、补防方案、调查摘要 | `pending_review` | 建议稿 |
| `mock_evaluation_entry` | `evaluation_entry` | `Evaluation` | 是否满意、评价时间、评价人、联系方式 | `editable` | 建议稿 |

### 4. 页面与接口依赖关系建议稿

| pageKey | pageName | action | apiOrDataDependency | method | status | fallbackPlan | notes |
|---|---|---|---|---|---|---|---|
| `plan_detail` | 计划详情 | 查看提醒状态 | `SystemNotification` / `EventRecord` | read | 建议稿 | 无提醒时展示空态 | 非接口文档直出 |
| `calendar_list` | 农事项日历 | 查看推荐日期 | `CalendarItem` | read | 已有对象语义 | 无数据时展示空态 | 建议稿 |
| `survey_entry` | 调查录入 | 提交药前调查 | `weed_treatment_diagnosis` 上游调查结果录入接口 | write | 待后端补接口定义 | 先用 mock 提交流程演示 | 非接口文档直出 |
| `survey_entry` | 调查录入 | 提交药后调查 | `additional_treatment_diagnosis` 上游调查结果录入接口 | write | 待后端补接口定义 | 先用 mock 提交流程演示 | 非接口文档直出 |
| `execution_feedback` | 执行反馈 | 提交执行结果 | `ExecutionRecord` 写接口 | write | 待后端补接口定义 | 先用本地表单 mock | 建议稿 |
| `review_request` | 人工复核 | 提交复核决策 | `ReviewRequestResolved` 对应写接口 | write | 待后端补接口定义 | 先 mock 决策结果 | 非接口文档直出 |
| `evaluation_entry` | 服务评价录入 | 提交评价 | `Evaluation` 写接口 | write | 待后端补接口定义 | 先 mock 提交流程 | 建议稿 |

### 5. 第一条闭环演示流程建议稿

| stepNo | pageKey | trigger | userAction | expectedResult | dependsOn | notes |
|---|---|---|---|---|---|---|
| 1 | `plan_detail` | 创建计划完成 | 查看初始化后的土壤封闭和药前调查 `CalendarItem` | 显示推荐日期和任务状态 | `soil_treatment_diagnosis` / `weed_survey_date_diagnosis` | 建议稿 |
| 2 | `calendar_list` | 药前调查进入时间窗 | 打开药前调查任务 | 可进入调查录入 | `TaskDueCheckJob` | 建议稿 |
| 3 | `survey_entry` | 药前调查执行 | 录入药前调查结果并提交 | 达到防治要求时生成茎叶除草任务 | `weed_treatment_diagnosis` | 建议稿 |
| 4 | `task_detail` | 茎叶除草任务生成 | 查看方案并进入执行反馈 | 显示 `OperationPlan` | `OperationPlan` | 建议稿 |
| 5 | `execution_feedback` | 执行完成 | 提交执行结果 | 生成药后调查 `CalendarItem` | `after_treatment_diagnosis` | 建议稿 |
| 6 | `survey_entry` | 药后调查进入窗口 | 录入药后调查结果 | 返回无需补防 / 需缓解药害 / 待补充调查 / 立即补防 | `additional_treatment_diagnosis` | 建议稿 |
| 7 | `review_request` | 返回需复核分支 | 提交复核结论 | 立即补防通过后新增茎叶除草任务 | `ReviewRequest` | 建议稿 |
| 8 | `evaluation_entry` | 补防结束或无需补防 | 提交服务评价 | 满意结束，不满意进入服务效果调查 | `Evaluation` | 建议稿 |

### 6. 待决事项建议稿

| questionId | question | impact | options | owner | targetDecisionDate | status | notes |
|---|---|---|---|---|---|---|---|
| `FE-WEED-001` | `ExecutionRecord` 字段最终命名是否按当前建议稿落地 | 影响执行反馈表单和接口命名 | 沿用建议稿 / 统一改名 | 核心后端 | 待定 | open | 建议稿 |
| `FE-WEED-002` | 复核动作是否保留 `adjust` | 影响复核组件交互和状态机 | 保留 / 删除 | 产品 / 架构负责人 | 待定 | open | 建议稿 |
| `FE-WEED-003` | 计划详情页是否必须展示 `SystemNotification` | 影响提醒入口设计 | 详情页展示 / 单独消息中心 | 产品 / 架构负责人 | 待定 | open | 建议稿 |

## 当前阶段完成标准

```text
1. 页面清单和信息架构：
   需要明确页面名称、入口、主要对象、依赖接口和页面间跳转关系。
2. 核心页面低保真原型：
   至少覆盖计划创建、计划详情、任务详情、执行反馈、复核处理页面。
3. 页面字段需求清单：
   需要按页面列出需要展示和录入的字段，并标记哪些字段当前还缺后端定义。
4. mock 数据需求说明：
   说明前端后续需要哪些 mock 结构，不要求现在给最终对象 mock。
5. 页面与接口依赖关系表：
   需要明确每个页面依赖哪些接口、哪些接口目前还不存在。
6. 关键组件说明：
   需要说明方案展示、执行反馈录入、复核处理组件各自的输入输出信息。
7. 第一条垂直闭环的前端演示流程：
   需要给出从计划创建到任务查看、反馈录入、复核处理的页面流转。
8. 不要求当前提交正式页面代码或最终 mock 数据。
```
