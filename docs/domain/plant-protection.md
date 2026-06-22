# 植保方向

> 本文档从团队分工总览中拆出，用于单独说明植保方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交 adapter、mapper、API router 或对象样例代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 植保 | 各接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 植保 | `taskCategory / taskSubtype` 定义表 | 定义表 | 产品 / 架构负责人、核心后端 |
| 植保 | 触发规则表和依赖关系表 | 规则表 / 依赖表 | 产品 / 架构负责人、核心后端 |
| 植保 | 调查录入字段草案 | 字段表 | 核心后端 |
| 植保 | 方案字段草案 | 字段表 | 核心后端、产品 / 架构负责人 |
| 植保 | 执行、评价、反馈、复核字段草案 | 字段表 / 规则说明 | 核心后端 |
| 植保 | 人工复核规则草案 | 规则说明 / 分支表 | 产品 / 架构负责人 |
| 植保 | 端到端测试场景 | 场景表 | 无，必要时核心后端确认 |
| 植保 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

1. 对接土壤封闭处方推荐接口。
2. 对接茎叶除草药前调查时间推荐接口。
3. 对接茎叶除草处方推荐接口。
4. 对接药后调查日期推荐接口。
5. 对接杂草补防诊断接口。
6. 定义植保调查、诊断、防治、药后调查、补防、服务效果评估的任务流转。
7. 定义植保 OperationPlan.parameters / prescriptionMap / acceptanceCriteria。
8. 定义植保执行记录、评价反馈和人工复核规则。

## 当前阶段非代码任务

1. 植保接口摘要：
   对土壤封闭处方推荐接口、茎叶除草药前调查时间推荐接口、茎叶除草处方推荐接口、药后调查日期推荐接口、杂草补防诊断接口按总文档统一模板说明触发时机、输入来源、请求输出结构、异常结构、映射目标、失败处理和人工确认点。
2. task 定义表：
   至少按总文档统一格式给出 workflowKey、taskCategory、taskSubtype、generalFlowKey、goal、upstreamKeys、downstreamKeys、requiresOperationPlan、requiresExecution、requiresReview。
3. 触发规则表和依赖关系表：
   按总文档统一格式说明调查、防治、补防、服务效果评估相关对象的触发来源、阻断条件、依赖关系和 fallbackAction。
4. 调查录入字段草案：
   明确药前调查、病虫调查、药后调查分别需要记录哪些调查项、附件和人工信息。
5. 方案字段草案：
   列出后续植保方案至少需要哪些字段，例如药剂、用量、作业窗口、依据、风险提示；不要求现在给最终 OperationPlan JSON。
6. 执行、评价、反馈、复核字段草案：
   列出植保执行、药后调查、服务效果评估、补防复核分别需要记录哪些结果字段，并说明哪些字段进入 Evaluation / Feedback / ReviewRequest。
7. 人工复核规则草案：
   明确什么情况下需要复核、复核人需要看到什么上下文、可能做哪些决策。
8. 至少 3 个端到端测试场景：
   - 茎叶除草药前调查后生成防治方案。
   - 药后调查识别异常并触发补防人工确认。
   - 药前调查结果不需要防治，只记录 NoAction 或下一次调查日期。
9. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
10. 文档回写要求：
   如涉及新的 workflow、taskSubtype 或后台任务，需同步更新 docs/workflow/task-workflow-matrix.md 和 docs/workflow/background-job-matrix.md。

## 最新接口收口

以下内容基于 [docs/api/weed_diagnosis_api.md](/F:/workspace/CropFlow/docs/api/weed_diagnosis_api.md) 的最新版本整理，用于收口当前杂草主线的接口契约。

### 杂草主线接口总表

| interfaceCode | endpoint | 触发时机 | 关键输入 | 关键输出 | 映射目标 | 是否人工确认 |
|---|---|---|---|---|---|---|
| soilTreatmentDiagnosisAlgorithm | `/api/soil_treatment_diagnosis` | 计划创建 / 更新后，已形成栽培日期 | `province`、`rice_type`、`cultivation_system`、`cultivation_pattern`、`cultivation_date` | `土壤封闭推荐日期`、`封闭操作`、`防治方案`、`杂草萌发起始日期` | `CalendarItem(WF_SOIL_SEAL_WEED)`、`OperationPlan`、`EventRecord` | 否 |
| weedSurveyDateDiagnosisAlgorithm | `/api/weed_survey_date_diagnosis` | 后台推荐药前调查日期时 | `weather_data`、`rice_type`、`cultivation_system`、`cultivation_pattern`、`cultivation_date` | `推荐茎叶除草前调查日期` | `CalendarItem(WF_STEM_LEAF_WEED_SURVEY)`、`EventRecord` | 否 |
| weedTreatmentDiagnosisAlgorithm | `/api/weed_treatment_diagnosis` | 药前调查结果录入完成后 | `province`、`weather_data`、`cultivation_*`、`survey_data_before_treatment`、`last_survey_date` | `msg=已推荐除草日期/5d后重新调查`，以及 `target`、`推荐防治日期` 或 `推荐茎叶除草前调查日期`、`防治方案` | `TaskIntent`、`OperationPlan`、`CalendarItem`、`EventRecord` | 否 |
| afterTreatmentDiagnosisAlgorithm | `/api/after_treatment_diagnosis` | 茎叶除草或补防执行完成后 | `control_date` | `药后调查日期` | `CalendarItem(WF_STEM_LEAF_WEED_POST_SURVEY)`、`EventRecord` | 否 |
| additionalTreatmentDiagnosisAlgorithm | `/api/additional_treatment_diagnosis` | 药后调查结果录入完成后 | `weed_germination_date`、`control_target`、`control_date[]`、`after_treatment_survey_date`、`survey_data_before_treatment`、`survey_data_after_treatment`，以及立即补防所需 `province/cultivation_*` | `msg=无需补防/需缓解药害/需要待药害缓解后进行补防，补充调查后重新录入数据/需要立即补防`，以及 `推荐补防日期`、`补充调查日期`、`服务效果评估日期`、条件性返回的 `防治方案` | `ReviewRequest`、`TaskIntent`、`OperationPlan`、`CalendarItem`、`Feedback`、`EventRecord` | 条件性，仅“需要立即补防”必须人工确认 |

### 关键契约结论

1. 杂草主线当前明确为 5 个接口，不再把药前调查日期错误归到 `soil_treatment_diagnosis`。
2. 杂草主线当前不依赖独立 `/api/get_control_plan`；土壤封闭、茎叶除草、立即补防三个接口都直接返回 `防治方案`。
3. `weather_data` 只在 `weed_survey_date_diagnosis` 和 `weed_treatment_diagnosis` 中必填，且必须按接口文档提供闭区间、连续逐日数据。
   直播模式下，`weed_survey_date_diagnosis` 的起算日按计划播种日期处理。
4. `data.target` 不是独立 Recommendation，它只作为 `TaskIntent`、`OperationPlan.basis`、`EventRecord.payload` 的依据摘要。
5. `additional_treatment_diagnosis` 只有在 `msg=需要立即补防` 时才返回 `防治方案`；此结果不能直接生成正式任务，必须先进入 `ReviewRequest`。
6. `additional_treatment_diagnosis` 四个分支沿用返回示例中的同一批字段，不同分支仅字段取值不同。
7. “需要立即补防”在人工复核通过后，统一新增一个 `WF_STEM_LEAF_WEED` 茎叶除草任务。
8. `weather_data` 由第三方接口获取。
9. CropFlow 不维护原始气象主数据；通过后台任务按需拉取、比对变化并记录用于算法调用的气象片段留痕。
10. 当前杂草主线没有独立 `scheme_info` 概念；如需类似信息，统一并入算法请求 payload 组装责任。
11. `soil_treatment_diagnosis` 和 `weed_survey_date_diagnosis` 在计划创建时即调用，并分别新增土壤封闭、药前调查两个 `CalendarItem`；播种或移栽日期变更时更新这两个 `CalendarItem`。
12. `StageChanged` 当前不影响杂草防治相关任务和 `CalendarItem`。
13. 调查类 `CalendarItem` 在推荐日期前 2 周进入正式任务生成窗口。
14. 推荐日期过期后失效；重算结果如有更新则覆盖旧日期。
15. “待药害缓解后补充调查”分支先新增药前调查 `CalendarItem`；如已进入推荐日期前 2 周窗口，则可直接转为 `FarmingTask`。
16. 连续逐日 `weather_data` 缺失或算法调用失败时，记录失败事件，写入 `SystemNotification`，并在计划详情页暴露“待补气象数据 / 算法调用失败”状态。
17. `CalendarItem -> FarmingTask` 的主路径按时间窗自动生成，由 `TaskDueCheckJob` 统一负责。
18. `ReviewRequest` 的通用触发原则是：当接口结果提示需要新增农事或需要人工判断，且系统不能直接落正式任务时，先创建 `ReviewRequest`，再由编排器决定后续动作。

### 当前冻结口径（2026-05-18）

1. `additional_treatment_diagnosis` 返回 `需缓解药害` 时，人工结论如为“施肥”或“打药”，需要生成后续正式任务；第一版先不要求同步冻结完整 `OperationPlan` 结构，具体方案字段后续补充。
2. 药前调查需要区分“普通药前调查”和“补防回流药前调查”两类语义，不能混用为同一个 `taskSubtype`。
3. 杂草防治第一版不支持 `partial`；执行结果按完成 / 未完成 / 失败理解。
4. 药后调查链路触发依赖已完成执行，且执行记录中需要有明确的完成时间和调查时间；调查结果字段以 `docs/api/weed_diagnosis_api.md` 为准。
5. 杂草防治第一版 `ExecutionRecord` 不要求图片附件、实际面积和实际用量。
6. 只有当接口结果提示需要新增农事，且系统不能直接落正式任务时，才进入 `requiresReview / ReviewRequest`。
7. 农户反馈服务评价默认是一个正式 `FarmingTask`，不是仅记录在 `Feedback` 中的轻量动作。
8. 服务评价结果不满意时，第一版直接创建后续 `FarmingTask`，不先创建建议态对象。
9. 杂草防治第一版执行结果仅考虑人工录入，不接设备回调或第三方执行系统回传。

### 杂草主线 5 个算法摘要

#### 1. `soil_treatment_diagnosis`

- interfaceCode: `soilTreatmentDiagnosisAlgorithm`
- endpoint: `/api/soil_treatment_diagnosis`
- 用途: 在计划创建或播种/移栽日期更新后，推荐土壤封闭日期并返回土壤封闭方案。
- 触发时机: `PlantingPlanCreated` / `PlantingPlanUpdated`，且已形成 `cultivation_date`。
- 关键输入:
  - `province`
  - `rice_type`
  - `cultivation_system`
  - `cultivation_pattern`
  - `cultivation_date`
- 关键输出:
  - `土壤封闭推荐日期`
  - `封闭操作`
  - `防治方案`
  - `杂草萌发起始日期`
- 映射目标:
  - 新增或更新 `CalendarItem(WF_SOIL_SEAL_WEED)`
  - 生成 `OperationPlan`
  - 写入 `EventRecord`
- 失败处理:
  - 参数错误时记录失败事件，不生成下游对象
  - 服务异常时按 job 重试策略处理，失败后写 `SystemNotification`
- 人工确认:
  - 当前无

#### 2. `weed_survey_date_diagnosis`

- interfaceCode: `weedSurveyDateDiagnosisAlgorithm`
- endpoint: `/api/weed_survey_date_diagnosis`
- 用途: 推荐茎叶除草药前调查日期。
- 触发时机: `PlantingPlanCreated` / `PlantingPlanUpdated` 后，由后台维护药前调查日期时调用。
- 关键输入:
  - `weather_data`
  - `rice_type`
  - `cultivation_system`
  - `cultivation_pattern`
  - `cultivation_date`
- 关键输入规则:
  - 直播模式下 `weather_data` 起算日按计划播种日期
  - `weather_data` 需提供闭区间、连续逐日数据
- 关键输出:
  - `推荐茎叶除草前调查日期`
- 映射目标:
  - 新增或更新 `CalendarItem(WF_STEM_LEAF_WEED_SURVEY)`
  - 写入 `EventRecord`
- 失败处理:
  - 连续逐日天气缺失或算法失败时，记录失败事件
  - 写入 `SystemNotification`
  - 在计划详情页暴露“待补气象数据 / 算法调用失败”状态
- 人工确认:
  - 当前无

#### 3. `weed_treatment_diagnosis`

- interfaceCode: `weedTreatmentDiagnosisAlgorithm`
- endpoint: `/api/weed_treatment_diagnosis`
- 用途: 基于药前调查结果判断是否达到防治要求，并在需要时返回茎叶除草方案。
- 触发时机: 药前调查结果录入完成后。
- 关键输入:
  - `province`
  - `weather_data`
  - `cultivation_*`
  - `survey_data_before_treatment`
  - `last_survey_date`
- 关键输出:
  - `msg=已推荐除草日期` 或 `msg=5d后重新调查`
  - `target`
  - `推荐防治日期` 或 `推荐茎叶除草前调查日期`
  - 条件性返回 `防治方案`
- 映射目标:
  - 达到防治要求时生成 `TaskIntent`、`OperationPlan`，并进入 `WF_STEM_LEAF_WEED`
  - 未达到防治要求时新增下一次药前调查 `CalendarItem`
  - 全程写入 `EventRecord`
- 失败处理:
  - 输入字段不完整时不生成下游任务，记录失败事件
  - 算法失败时转人工判定待办
- 人工确认:
  - 当前不需要人工确认

#### 4. `after_treatment_diagnosis`

- interfaceCode: `afterTreatmentDiagnosisAlgorithm`
- endpoint: `/api/after_treatment_diagnosis`
- 用途: 为茎叶除草或补防执行完成后的药后调查推荐调查日期。
- 触发时机: 茎叶除草或补防执行完成后。
- 关键输入:
  - `control_date`
- 关键输出:
  - `药后调查日期`
- 映射目标:
  - 新增 `CalendarItem(WF_STEM_LEAF_WEED_POST_SURVEY)`
  - 写入 `EventRecord`
- 失败处理:
  - 缺少完成时间或调用失败时，记录失败事件并转人工安排调查日期
- 人工确认:
  - 当前无

#### 5. `additional_treatment_diagnosis`

- interfaceCode: `additionalTreatmentDiagnosisAlgorithm`
- endpoint: `/api/additional_treatment_diagnosis`
- 用途: 基于药后调查结果判断是否无需补防、需缓解药害、待药害缓解后补充调查或立即补防。
- 触发时机: 药后调查结果录入完成后。
- 关键输入:
  - `weed_germination_date`
  - `control_target`
  - `control_date[]`
  - `after_treatment_survey_date`
  - `survey_data_before_treatment`
  - `survey_data_after_treatment`
  - 立即补防时还需 `province/cultivation_*`
- 关键输出:
  - `msg=无需补防/需缓解药害/需要待药害缓解后进行补防，补充调查后重新录入数据/需要立即补防`
  - `推荐补防日期`
  - `补充调查日期`
  - `服务效果评估日期`
  - 仅“需要立即补防”条件性返回 `防治方案`
- 映射目标:
  - `无需补防` -> 服务效果评估
  - `需缓解药害` -> `ReviewRequest`
  - `待药害缓解后补充调查` -> 药前调查 `CalendarItem`
  - `需要立即补防` -> `ReviewRequest`，通过后新增 `WF_STEM_LEAF_WEED`
  - 全程写入 `EventRecord`
- 失败处理:
  - 关键防效字段缺失或调用失败时，不自动推进下游，创建人工复核待办
- 人工确认:
  - “需要立即补防”必须人工确认
  - `ReviewRequest` 的通用触发原则适用于系统无法直接落正式任务的分支

### 杂草主线字段草案

#### 药前调查录入字段

| 字段 | 类型 | 是否必填 | 说明 | 建议映射 |
|---|---|---|---|---|
| `调查日期` | string | 是 | `YYYYmmdd` | `ExecutionRecord.resultPayload.surveyDate` |
| `水稻叶龄` | float | 是 | 水稻当前叶龄 | `ExecutionRecord.resultPayload.riceLeafAge` |
| `稗草.leaf_age` / `mass` | float | 是 | 稗草叶龄和每平方米出草量 | `ExecutionRecord.resultPayload.weedSurvey.barnyardgrass.*` |
| `千金子.leaf_age` / `mass` | float | 是 | 千金子叶龄和每平方米出草量 | `ExecutionRecord.resultPayload.weedSurvey.leptochloa.*` |
| `阔叶草.mass` | float | 是 | 阔叶草每平方米出草量 | `ExecutionRecord.resultPayload.weedSurvey.broadleaf.mass` |
| `莎草.mass` | float | 是 | 莎草每平方米出草量 | `ExecutionRecord.resultPayload.weedSurvey.sedge.mass` |

#### 药后调查录入字段

| 字段 | 类型 | 是否必填 | 说明 | 建议映射 |
|---|---|---|---|---|
| `调查日期` | string | 是 | `YYYYmmdd` | `ExecutionRecord.resultPayload.postSurveyDate` |
| `水稻叶龄` | float | 是 | 水稻当前叶龄 | `ExecutionRecord.resultPayload.riceLeafAge` |
| `水稻药害等级` | string | 是 | `无/低/中/高` 等 | `ExecutionRecord.resultPayload.herbicideDamageLevel` |
| `稗草/千金子.防效` | float | 是 | 取值 `0~1` | `Evaluation.metrics.weedControlEffect.*` |
| `稗草/千金子.leaf_age` / `mass` | float | 是 | 药后杂草叶龄和出草量 | `ExecutionRecord.resultPayload.postWeedSurvey.*` |
| `阔叶草/莎草.防效` / `mass` | float | 是 | 药后调查数据 | `ExecutionRecord.resultPayload.postWeedSurvey.*` |

#### 服务效果评估字段

| 字段 | 类型 | 是否必填 | 说明 | 建议映射 |
|---|---|---|---|---|
| `是否满意` | boolean / enum | 是 | 满意或不满意 | `Evaluation.result.isSatisfied` |
| `评价时间` | string | 是 | 评价提交时间 | `Evaluation.createdAt` |
| `评价人` | string | 是 | 评价提交人姓名或身份标识 | `Evaluation.evaluatorName` |
| `联系方式` | string | 是 | 电话或其他可联系信息 | `Evaluation.contactInfo` |

#### 植保 `OperationPlan.parameters` 最小结构

| 字段 | 来源 | 说明 |
|---|---|---|
| `strategy` | workflow 语义 | 例如 `soil_sealing`、`stem_leaf_weed`、`additional_weed_control` |
| `targetSummary` | `data.target` | 保存 `水稻叶龄`、`防治靶标` |
| `controlTarget` | 算法结果 | 保存 `防治对象` 或 `补防对象` |
| `recommendedDates` | 算法结果 | 保存 `土壤封闭推荐日期`、`推荐防治日期` 或 `推荐补防日期` |
| `weedGerminationDate` | 算法结果 | 保存 `杂草萌发起始日期`，供后续药后调查 / 补防诊断复用 |
| `prescription` | `防治方案.处方` | 保存处方数组 |
| `waterVolumePerMu` | `防治方案.兑水量` | 保存 `3 L/亩` 或 `4 L/亩` |
| `operationAction` | 土壤封闭接口结果 | 保存封闭任务类型名称，当前固定为 `苗后封闭` |

### 当前仍待确认接口问题

当前无新的杂草主线接口阻塞问题；如后续算法侧仍保留 `农事操作` 示例字段，系统内部统一按“封闭任务类型名称”处理，当前固定为 `苗后封闭`。


### 直接提交模板

#### 1. 接口摘要

```md
## <接口名>

### 1. 基本信息
- interfaceCode:
- 接口名称:
- 用途:
- 负责人:
- 接口地址:
- 请求方式:
- 鉴权方式:

### 2. 触发时机
- 上游 workflowKey / jobKey:
- 触发事件:
- 触发步骤:
- 同步 / 异步:

### 3. 请求输入
- 字段 1：
  - 名称：
  - 类型：
  - 是否必填：
  - 来源：
  - 示例：
  - 备注：
- 字段 2：
  - 名称：
  - 类型：
  - 是否必填：
  - 来源：
  - 示例：
  - 备注：

### 4. 响应输出
- 字段 1：
  - 名称：
  - 类型：
  - 含义：
  - 示例：
  - 映射目标对象：
  - 映射目标字段：
- 字段 2：
  - 名称：
  - 类型：
  - 含义：
  - 示例：
  - 映射目标对象：
  - 映射目标字段：

### 5. 异常返回
- 异常 1：
  - 异常码：
  - 含义：
  - 是否可重试：
  - fallbackAction：
  - 备注：
- 异常 2：
  - 异常码：
  - 含义：
  - 是否可重试：
  - fallbackAction：
  - 备注：

### 6. 业务语义
- no_action 的判定:
- need_more_info 的判定:
- 是否可直接生成 OperationPlan:
- 是否必须人工确认:
```

建议至少分别提交：

1. 土壤封闭处方推荐接口
2. 茎叶除草药前调查时间推荐接口
3. 茎叶除草处方推荐接口
4. 药后调查日期推荐接口
5. 杂草补防诊断接口

#### 2. 农事定义（按条填写）

```md
## 农事：<农事名称>

- workflowKey：
  后补
- 任务大类：
  植保
- 农事子类：
- 任务名称：
- 通用流程：
- 适用阶段：
- 目标：
- 是否需要方案：
  是 / 否 / 条件性
- 是否进入执行：
  是 / 否 / 条件性
- 是否需要复核：
  是 / 否 / 条件性
- 上游依赖：
  - 
- 下游去向：
  - 
- 调用接口：
  - 
- 人工确认点：
  - 
- no_action 情况：
  - 
- 备注：
  - 
```

建议先覆盖杂草防治主线，病虫方向可按同一模板后补：

## 农事：土壤封闭除草

- workflowKey：
  WF_SOIL_SEAL_WEED
- 任务大类：
  植保
- 农事子类：
  土壤封闭除草
- 任务名称：
  土壤封闭除草
- 通用流程：
  GENERAL_PLANT_PROTECTION_CONTROL
- 适用阶段：
  播种或移栽后、杂草萌发前窗口
- 目标：
  在播种或移栽后及时生成土壤封闭作业时间和防治方案，并完成封闭作业
- 是否需要方案：
  是
- 是否进入执行：
  是
- 是否需要复核：
  否
- 上游依赖：
  - PlantingPlan
  - 播种或移栽日期形成或更新
- 下游去向：
  - OperationPlan
  - FarmingTask
  - ExecutionRecord
- 调用接口：
  - 土壤封闭处方推荐接口
- 人工确认点：
  - 当前无
- no_action 情况：
  - 不适用，当前业务口径下土壤封闭没有“无需处理”分支
- 备注：
  - 触发条件是计划创建或播种 / 移栽日期变更
  - 接口返回土壤封闭作业时间和防治方案
  - 作业流程包含水层排干、打药作业、作业后上水、作业反馈

## 农事：茎叶除草药前调查

- workflowKey：
  WF_STEM_LEAF_WEED_SURVEY
- 任务大类：
  植保
- 农事子类：
  茎叶除草药前调查
- 任务名称：
  茎叶除草药前调查
- 通用流程：
  GENERAL_PLANT_PROTECTION_SURVEY
- 适用阶段：
  分蘖至封行前
- 目标：
  根据推荐调查日期完成药前草害调查，为是否实施茎叶除草提供依据
- 是否需要方案：
  否
- 是否进入执行：
  否
- 是否需要复核：
  否
- 上游依赖：
  - PlantingPlan
  - 播种或移栽日期形成或更新
- 下游去向：
  - CalendarItem
  - 茎叶除草
  - 下一次茎叶除草药前调查
- 调用接口：
  - 茎叶除草药前调查时间推荐接口
- 人工确认点：
  - 当前无
- no_action 情况：
  - 调查日期推荐接口本身无 no_action 分支；如缺少连续气象数据或接口失败，不创建调查任务，转待补数据或人工安排
- 备注：
  - 触发条件是计划创建或播种 / 移栽日期更新后，且已具备接口要求的连续 `weather_data`
  - 调查时间由独立的茎叶除草药前调查时间推荐接口给出，不再由土壤封闭接口返回
  - 计划创建时先维护药前调查 CalendarItem，播种或移栽日期变更时更新对应 CalendarItem
  - 调查类 CalendarItem 在推荐日期前 2 周进入生成窗口，再由 TaskDueCheckJob 生成调查 FarmingTask
  - 调查录入后才进入是否新增茎叶除草任务的判断
  - 第一版需通过 `taskSubtype` 区分“普通药前调查”和“补防回流药前调查”

## 农事：茎叶除草

- workflowKey：
  WF_STEM_LEAF_WEED
- 任务大类：
  植保
- 农事子类：
  茎叶除草
- 任务名称：
  茎叶除草
- 通用流程：
  GENERAL_PLANT_PROTECTION_CONTROL
- 适用阶段：
  药前调查判定达到防治要求后的作业窗口
- 目标：
  在药前调查满足防治要求后生成茎叶除草时间和防治方案，并完成施药作业
- 是否需要方案：
  是
- 是否进入执行：
  是
- 是否需要复核：
  条件性
- 上游依赖：
  - 茎叶除草药前调查结果录入
- 下游去向：
  - OperationPlan
  - FarmingTask
  - 茎叶除草药后调查
- 调用接口：
  - 茎叶除草处方推荐接口
- 人工确认点：
  - 当前不需要人工确认，按算法结果直接生成茎叶除草任务
- no_action 情况：
  - 药前调查未达到防治要求时不进入本农事
- 备注：
  - 接口输入是药前调查结果
  - 接口分支一：未达到防治要求，新增下一次药前调查任务，不新增茎叶除草任务
  - 接口分支二：达到防治要求，新增茎叶除草任务，直接返回防治日期和防治方案
  - 杂草主线不再额外调用独立 `control_plan` 接口生成处方
  - 作业流程包含水层排干、打药作业、作业后上水、作业反馈

## 农事：茎叶除草药后调查

- workflowKey：
  WF_STEM_LEAF_WEED_POST_SURVEY
- 任务大类：
  植保
- 农事子类：
  茎叶除草药后调查
- 任务名称：
  茎叶除草药后调查
- 通用流程：
  GENERAL_PLANT_PROTECTION_SURVEY
- 适用阶段：
  茎叶除草或杂草补防完成后的药后评估窗口
- 目标：
  在施药完成后安排药后调查，采集防效和药害等结果，为补防或服务评价提供依据
- 是否需要方案：
  否
- 是否进入执行：
  是
- 是否需要复核：
  否
- 上游依赖：
  - 茎叶除草
  - 杂草补防
- 下游去向：
  - 杂草补防
  - 杂草防治服务效果评估
- 调用接口：
  - 药后调查日期推荐接口
- 人工确认点：
  - 当前无
- no_action 情况：
  - 不适用，药后调查是施药后的固定后续动作
- 备注：
  - 药后调查时间由药后调查日期推荐接口返回
  - 先维护药后调查 CalendarItem，待到达生成窗口后再由 TaskDueCheckJob 生成调查 FarmingTask
  - 作业流程包含人工调查、调查结果录入

## 农事：杂草补防

- workflowKey：
  WF_STEM_LEAF_WEED_ADDITIONAL_CONTROL
- 任务大类：
  植保
- 农事子类：
  杂草补防
- 任务名称：
  杂草补防
- 通用流程：
  GENERAL_PLANT_PROTECTION_CONTROL
- 适用阶段：
  药后调查判定需补防后的补防窗口
- 目标：
  根据药后调查结果判断是否需要补防，并在需要时形成补防时间和补防方案
- 是否需要方案：
  条件性
- 是否进入执行：
  否
- 是否需要复核：
  是
- 上游依赖：
  - 茎叶除草药后调查结果录入
- 下游去向：
  - 茎叶除草
  - 茎叶除草药后调查
  - 杂草防治服务效果评估
  - ReviewRequest
- 调用接口：
  - 杂草补防诊断接口
- 人工确认点：
  - 杂草补防诊断结果不能直接生成正式任务，必须先进入 ReviewRequest
- no_action 情况：
  - 无需补防时，直接进入服务效果评估
- 备注：
  - 接口分支一：`无需补防`，返回服务效果评估日期，进入服务效果评估
  - 接口分支二：`需缓解药害`，创建人工 `ReviewRequest`，由人工判断不处理、施肥还是打药；如结论为施肥或打药，则生成后续正式任务，具体方案字段后续补充
  - 接口分支三：`需要待药害缓解后进行补防，补充调查后重新录入数据`，返回补充调查日期，先新增一个药前调查 `CalendarItem`；该调查需标记为“补防回流药前调查”，如已进入推荐日期前 2 周窗口则直接转 `FarmingTask`
  - 接口分支四：`需要立即补防`，返回补防时间和补防方案
  - 本阶段约定：仅“需要立即补防”分支统一先进入 ReviewRequest，再由编排器决定后续任务

## 农事：杂草防治服务效果评估

- workflowKey：
  WF_PLANT_PROTECTION_SERVICE_EVALUATION
- 任务大类：
  植保
- 农事子类：
  杂草防治服务效果评估
- 任务名称：
  杂草防治服务效果评估
- 通用流程：
  none
- 适用阶段：
  杂草防治完成后的服务评价窗口
- 目标：
  收集农户对杂草防治服务的满意度和现场反馈，决定是否结束闭环或新增服务效果调查
- 是否需要方案：
  否
- 是否进入执行：
  是
- 是否需要复核：
  条件性
- 上游依赖：
  - 茎叶除草药后调查
  - 杂草补防
- 下游去向：
  - 结束
  - 服务效果调查
- 调用接口：
  - 当前无
- 人工确认点：
  - 农户评价不满意时，需要人工安排服务效果调查
- no_action 情况：
  - 评价满意时直接结束
- 备注：
  - 流程一：农户反馈服务评价
  - 流程二：满意则结束
  - 流程三：不满意则新增服务效果调查任务，并录入实际调查结果
  - 第一版默认作为正式 `FarmingTask` 执行，不单独创建建议态对象
  - 当前不调用接口

## 农事：服务效果调查

- workflowKey：
  WF_PLANT_PROTECTION_SERVICE_EFFECT_SURVEY
- 任务大类：
  植保
- 农事子类：
  服务效果调查
- 任务名称：
  服务效果调查
- 通用流程：
  GENERAL_PLANT_PROTECTION_SURVEY
- 适用阶段：
  服务评价不满意后的跟进窗口
- 目标：
  在农户评价不满意时安排服务人员现场复查，补充记录实际问题、原因和后续处理建议
- 是否需要方案：
  否
- 是否进入执行：
  是
- 是否需要复核：
  条件性
- 上游依赖：
  - 杂草防治服务效果评估结果为不满意
- 下游去向：
  - Feedback
  - ReviewRequest
  - 结束
- 调用接口：
  - 当前无
- 人工确认点：
  - 服务效果调查结果如涉及争议或补偿决策，可转 ReviewRequest
- no_action 情况：
  - 不适用，不满意时固定进入本农事
- 备注：
  - 本任务以人工调查和人工录入为主
  - 第一版在服务评价不满意后直接创建 `FarmingTask`
  - 是否直接结束还是形成后续调整动作，由编排器根据调查结果决定
  - 当前不调用接口

## 其他植保方向待补

- 封行病虫调查 / 防治
- 突发病虫调查 / 防治
- 齐穗病虫调查 / 防治
- 破口病虫调查 / 防治

填写约定：

1. workflowKey 先按当前草案保留，最终由产品 / 架构负责人和核心后端统一收口。
2. 任务大类、农事子类、任务名称、适用阶段、目标优先用中文填写。
3. 如果后续需要补英文编码，可由核心后端在收口阶段补到总表。
4. 当前阶段先把业务语义和依赖链写清楚，比编码命名更重要。


#### 3. 触发规则表

```md
## 触发规则：<规则名称>

- 目标对象：
- 目标对象标识：
- 触发类型：
- 触发来源：
- 前置条件：
  - 
- 阻断条件：
  - 
- 动作：
- 建议幂等键：
- fallbackAction：
- 备注：
  - 
```

建议至少先补杂草防治主线：

## 触发规则：计划创建后生成土壤封闭 CalendarItem

- 目标对象：
  土壤封闭除草
- 目标对象标识：
  WF_SOIL_SEAL_WEED
- 触发类型：
  create_or_recompute
- 触发来源：
  PlantingPlanCreated / PlantingPlanUpdated
- 前置条件：
  - 已形成播种日期或移栽日期
  - 已具备接口要求的连续 `weather_data`
- 阻断条件：
  - 播种日期和移栽日期均为空
- 动作：
  调用土壤封闭处方推荐接口，新增或更新土壤封闭 CalendarItem，并写入作业时间和防治方案
- 建议幂等键：
  plantingPlanId + sowingOrTransplantDate + WF_SOIL_SEAL_WEED
- fallbackAction：
  创建待人工补齐日期的提醒，不生成土壤封闭任务
- 备注：
  - 日期变更后重算，如推荐日期有更新则覆盖旧日期；过期日期失效

## 触发规则：计划创建后生成茎叶除草药前调查

- 目标对象：
  茎叶除草药前调查
- 目标对象标识：
  WF_STEM_LEAF_WEED_SURVEY
- 触发类型：
  create_or_recompute
- 触发来源：
  PlantingPlanCreated / PlantingPlanUpdated
- 前置条件：
  - 已形成播种日期或移栽日期
- 阻断条件：
  - 缺少播种日期和移栽日期
- 动作：
  调用茎叶除草药前调查时间推荐接口，新增或更新药前调查 CalendarItem
- 建议幂等键：
  plantingPlanId + sowingOrTransplantDate + WF_STEM_LEAF_WEED_SURVEY
- fallbackAction：
  记录算法失败事件；如仅缺少连续气象数据则等待下次 job，如算法报错则转人工安排调查日期
- 备注：
  - 日期更新后重算，如推荐日期有更新则覆盖旧调查时间；过期日期失效
  - 最新接口口径为调用 `/api/weed_survey_date_diagnosis`

## 触发规则：药前调查结果驱动是否新增茎叶除草

- 目标对象：
  茎叶除草 / 下一次药前调查
- 目标对象标识：
  WF_STEM_LEAF_WEED
- 触发类型：
  evaluate_and_branch
- 触发来源：
  药前调查结果录入完成
- 前置条件：
  - 已有有效的药前调查结果
  - 已具备从最早 `调查日期` 起连续 45 天的 `weather_data`
- 阻断条件：
  - 调查结果字段不完整
- 动作：
  调用茎叶除草处方推荐接口，根据返回结果新增茎叶除草任务或下一次药前调查任务
- 建议幂等键：
  surveyRecordId + WF_STEM_LEAF_WEED
- fallbackAction：
  创建人工判定待办，不自动生成下游任务
- 备注：
  - 达到防治要求时接口直接返回防治日期和防治方案
  - 未达到防治要求时返回下一次调查日期
  - 杂草主线不再额外依赖 `control_plan`

## 触发规则：施药完成后生成药后调查

- 目标对象：
  茎叶除草药后调查
- 目标对象标识：
  WF_STEM_LEAF_WEED_POST_SURVEY
- 触发类型：
  create
- 触发来源：
  茎叶除草完成 / 杂草补防完成
- 前置条件：
  - 已有完成态的执行反馈
- 阻断条件：
  - 执行反馈缺少完成时间
- 动作：
  调用药后调查日期推荐接口，生成药后调查时间
- 建议幂等键：
  executionId + WF_STEM_LEAF_WEED_POST_SURVEY
- fallbackAction：
  转人工安排药后调查日期
- 备注：
  - 正常除草和补防都走同一药后调查入口

## 触发规则：药后调查结果驱动补防分支

- 目标对象：
  杂草补防 / 服务效果评估 / 下一次药后调查
- 目标对象标识：
  WF_STEM_LEAF_WEED_ADDITIONAL_CONTROL
- 触发类型：
  evaluate_and_branch
- 触发来源：
  药后调查结果录入完成
- 前置条件：
  - 已有有效药后调查结果
- 阻断条件：
  - 药后调查结果缺少关键防效字段
- 动作：
  调用杂草补防诊断接口，根据返回结果进入补防、服务评价或下一次药后调查
- 建议幂等键：
  postSurveyRecordId + WF_STEM_LEAF_WEED_ADDITIONAL_CONTROL
- fallbackAction：
  创建人工复核待办，不自动推进下游
- 备注：
  - `需要立即补防` 时先创建 `ReviewRequest`
  - `无需补防` 时进入服务效果评估
  - `需缓解药害` 时创建人工 `ReviewRequest`，由人工判断不处理、施肥还是打药；如结论为施肥或打药，则生成后续正式任务，具体方案字段后续补充
  - `需要待药害缓解后进行补防，补充调查后重新录入数据` 时先新增一个药前调查 `CalendarItem`，并按“补防回流药前调查”标记；如已进入推荐日期前 2 周窗口则直接转 `FarmingTask`
  - `需要立即补防` 复核通过后新增一个 `WF_STEM_LEAF_WEED` 茎叶除草任务

## 触发规则：服务效果评估后决定是否结束

- 目标对象：
  杂草防治服务效果评估
- 目标对象标识：
  WF_PLANT_PROTECTION_SERVICE_EVALUATION
- 触发类型：
  evaluate_and_branch
- 触发来源：
  农户服务评价录入完成
- 前置条件：
  - 已有评价结果
- 阻断条件：
  - 满意度或结论为空
- 动作：
  满意则结束，不满意则新增服务效果调查任务
- 建议幂等键：
  evaluationId + WF_PLANT_PROTECTION_SERVICE_EVALUATION
- fallbackAction：
  创建人工跟进待办
- 备注：
  - 当前不调用接口

## 触发规则：服务效果评估不满意后生成服务效果调查

- 目标对象：
  服务效果调查
- 目标对象标识：
  WF_PLANT_PROTECTION_SERVICE_EFFECT_SURVEY
- 触发类型：
  create
- 触发来源：
  杂草防治服务效果评估结果录入完成
- 前置条件：
  - 服务评价结论为不满意
- 阻断条件：
  - 评价结论为空
- 动作：
  新增服务效果调查任务，安排服务人员现场调查
- 建议幂等键：
  evaluationId + WF_PLANT_PROTECTION_SERVICE_EFFECT_SURVEY
- fallbackAction：
  创建人工跟进待办
- 备注：
  - 本任务不调用接口


#### 4. 依赖关系表

```md
## 依赖关系：<当前农事或流程名>

- 当前对象：
- 依赖类型：
- 依赖对象：
- 依赖规则：
- 缺失依赖时动作：
- 满足依赖后的输出：
- 备注：
  - 
```

建议至少先补杂草防治主线：

## 依赖关系：土壤封闭除草

- 当前对象：
  土壤封闭除草
- 依赖类型：
  触发依赖
- 依赖对象：
  PlantingPlan / 播种日期 / 移栽日期
- 依赖规则：
  计划创建或播种 / 移栽日期更新后，才允许计算土壤封闭时间和方案
- 缺失依赖时动作：
  不创建任务，转人工补齐计划日期
- 满足依赖后的输出：
  土壤封闭作业时间
  土壤封闭防治方案
- 备注：
  - 土壤封闭后无额外业务后续动作

## 依赖关系：茎叶除草药前调查

- 当前对象：
  茎叶除草药前调查
- 依赖类型：
  触发依赖
- 依赖对象：
  PlantingPlan / 播种日期 / 移栽日期
- 依赖规则：
  计划创建或播种 / 移栽日期更新后，在具备连续 `weather_data` 的前提下调用调查时间推荐接口生成药前调查时间
- 缺失依赖时动作：
  不创建调查任务；缺日期则等待计划补齐，缺气象则等待天气数据补齐
- 满足依赖后的输出：
  药前调查 CalendarItem
  到期后的调查 FarmingTask
- 备注：
  - 当前主路径按 CalendarItem -> TaskDueCheckJob -> FarmingTask，调查类 CalendarItem 在推荐日期前 2 周进入生成窗口

## 依赖关系：茎叶除草

- 当前对象：
  茎叶除草
- 依赖类型：
  结果依赖
- 依赖对象：
  茎叶除草药前调查结果
- 依赖规则：
  只有药前调查完成并录入结果后，才允许调用处方推荐接口决定是否生成茎叶除草任务
- 缺失依赖时动作：
  不创建茎叶除草任务
- 满足依赖后的输出：
  茎叶除草任务
  或下一次药前调查任务
- 备注：
  - 未达到防治要求时不进入施药
  - 处方推荐接口直接返回防治方案，不再依赖独立 control_plan

## 依赖关系：茎叶除草药后调查

- 当前对象：
  茎叶除草药后调查
- 依赖类型：
  完成依赖
- 依赖对象：
  茎叶除草完成反馈 / 杂草补防完成反馈
- 依赖规则：
  施药作业完成后，调用药后调查日期推荐接口生成药后调查时间
- 缺失依赖时动作：
  不创建药后调查
- 满足依赖后的输出：
  药后调查任务
- 备注：
  - 正常除草和补防都共享同一后续调查逻辑

## 依赖关系：杂草补防

- 当前对象：
  杂草补防
- 依赖类型：
  结果依赖
- 依赖对象：
  茎叶除草药后调查结果
- 依赖规则：
  药后调查录入后，调用杂草补防诊断接口决定补防、服务评价或再次药后调查
- 缺失依赖时动作：
  不推进补防分支
- 满足依赖后的输出：
  ReviewRequest
  或服务效果评估
  或下一次药后调查
- 备注：
  - 本阶段约定：补防不能直接生成正式任务

## 依赖关系：杂草防治服务效果评估

- 当前对象：
  杂草防治服务效果评估
- 依赖类型：
  顺序依赖
- 依赖对象：
  茎叶除草药后调查结果 / 杂草补防结果
- 依赖规则：
  只有在药后调查或补防链路走完后，才进入服务效果评价
- 缺失依赖时动作：
  不开放评价入口
- 满足依赖后的输出：
  结束
  或新增服务效果调查任务
- 备注：
  - 满意直接结束，不满意进入服务效果调查

## 依赖关系：服务效果调查

- 当前对象：
  服务效果调查
- 依赖类型：
  结果依赖
- 依赖对象：
  杂草防治服务效果评估结果
- 依赖规则：
  只有当服务效果评估结果为不满意时，才创建服务效果调查任务
- 缺失依赖时动作：
  不创建服务效果调查
- 满足依赖后的输出：
  服务效果调查任务
- 备注：
  - 调查完成后可进入 Feedback、ReviewRequest 或结束
  - 第一版由服务评价不满意结果直接创建 `FarmingTask`


#### 5. 调查录入字段表

```md
## 调查类型：<调查类型>

- 字段 1：
  - 名称：
  - 类型：
  - 是否必填：
  - 含义：
  - 示例：
  - 映射目标对象：
  - 映射目标字段：
  - 备注：
- 字段 2：
  - 名称：
  - 类型：
  - 是否必填：
  - 含义：
  - 示例：
  - 映射目标对象：
  - 映射目标字段：
  - 备注：
```


建议至少覆盖：

1. 药前调查
2. 病虫调查
3. 药后调查
4. 服务效果评估

#### 6. `OperationPlan` 字段草案表

```md
## OperationPlan 字段草案

- 字段：planType
  - 是否必填：是
  - 含义：方案类型
  - 来源：固定值或规则
  - 示例：plant_protection_control
  - 备注：
- 字段：algorithmCode
  - 是否必填：否
  - 含义：方案来源接口标识
  - 来源：土壤封闭处方推荐接口 / 茎叶除草处方推荐接口
  - 示例：stem_leaf_weed_control_api
  - 备注：
- 字段：executionMode
  - 是否必填：是
  - 含义：执行方式
  - 来源：业务约定
  - 示例：manual
  - 备注：
- 字段：operationWindowStart
  - 是否必填：否
  - 含义：建议开始时间
  - 来源：算法或规则
  - 示例：2026-05-10T06:00:00+08:00
  - 备注：
- 字段：operationWindowEnd
  - 是否必填：否
  - 含义：建议结束时间
  - 来源：算法或规则
  - 示例：2026-05-10T18:00:00+08:00
  - 备注：
- 字段：parameters
  - 是否必填：是
  - 含义：处方参数
  - 来源：土壤封闭处方推荐接口 / 茎叶除草处方推荐接口
  - 示例：
  - 备注：药剂、剂型、用量、兑水量等
- 字段：operationArea
  - 是否必填：否
  - 含义：作业区域
  - 来源：计划或算法
  - 示例：
  - 备注：
- 字段：prescriptionMap
  - 是否必填：否
  - 含义：处方数组或图
  - 来源：算法
  - 示例：
  - 备注：
- 字段：basis
  - 是否必填：是
  - 含义：方案依据
  - 来源：诊断结果 / 输入摘要
  - 示例：
  - 备注：
- 字段：acceptanceCriteria
  - 是否必填：否
  - 含义：验收标准
  - 来源：业务约定
  - 示例：
  - 备注：
- 字段：riskNotes
  - 是否必填：否
  - 含义：风险提示
  - 来源：算法或人工
  - 示例：
  - 备注：
```


#### 7. 执行 / 评价 / 反馈 / 复核字段表

```md
## 对象：ExecutionRecord / Evaluation / Feedback / ReviewRequest

- 字段 1：
  - 所属对象：
  - 名称：
  - 类型：
  - 是否必填：
  - 含义：
  - 示例：
  - 备注：
- 字段 2：
  - 所属对象：
  - 名称：
  - 类型：
  - 是否必填：
  - 含义：
  - 示例：
  - 备注：
```

以下为 P1 初稿，其中 `ExecutionRecord / Feedback / ReviewRequest` 字段并非直接来自 `weed_diagnosis_api.md`，而是基于当前对象模型和前端录入需求整理的建议口径。

| 所属对象 | 字段 | 类型 | 是否必填 | 含义 | 示例 | 备注 |
|---|---|---|---|---|---|---|
| `ExecutionRecord` | `executionResult` | enum | 是 | 执行结果 | `completed` / `failed` | 第一版不支持 `partial` |
| `ExecutionRecord` | `actualStartTime` | datetime | 否 | 实际开始时间 | `2026-05-10T06:30:00+08:00` | 人工执行时可选 |
| `ExecutionRecord` | `actualEndTime` | datetime | 否 | 实际结束时间 | `2026-05-10T08:00:00+08:00` | 药后调查触发依赖该时间 |
| `ExecutionRecord` | `operatorName` | string | 否 | 执行人 | `张三` | 建议字段 |
| `ExecutionRecord` | `exceptionNote` | string | 否 | 执行异常说明 | `田块积水，作业延迟` | 建议字段 |
| `ExecutionRecord` | `attachments` | array | 否 | 图片、视频、单据等附件 | `[{type:\"image\",url:\"...\"}]` | 建议字段 |
| `ExecutionRecord` | `trackRef` | string / object | 否 | 作业轨迹引用 | `track_001` | 如无设备轨迹可为空 |
| `Feedback` | `feedbackTime` | datetime | 是 | 反馈提交时间 | `2026-05-10T09:00:00+08:00` | 建议字段 |
| `Feedback` | `needManualFollowUp` | boolean | 否 | 是否需要人工跟进 | `true` | 建议字段 |
| `Feedback` | `followUpSuggestion` | string | 否 | 后续建议 | `建议 5 天后复查` | 建议字段 |
| `Feedback` | `feedbackSource` | enum | 否 | 反馈来源 | `farmer` / `service_staff` / `system` | 建议字段 |
| `ReviewRequest` | `reviewType` | enum | 是 | 复核类型 | `additional_control_immediate` | 见下方复核规则 |
| `ReviewRequest` | `triggerReason` | string | 是 | 触发原因 | `接口返回需要立即补防` | 建议字段 |
| `ReviewRequest` | `candidateActions` | array | 是 | 候选决策动作 | `approve,reject,adjust,no_action,need_more_info` | 基于当前前端模板整理 |
| `ReviewRequest` | `decision` | enum | 否 | 最终复核结论 | `approve` | 复核完成后写入 |
| `ReviewRequest` | `decisionNote` | string | 否 | 复核备注 | `同意立即补防` | 建议字段 |
| `ReviewRequest` | `reviewedAt` | datetime | 否 | 复核完成时间 | `2026-05-11T10:00:00+08:00` | 建议字段 |


#### 8. 人工复核规则表

```md
## 复核规则：<复核名称>

- reviewType：
- 触发原因：
- 人工需要看到的上下文：
  - 
- 可选决策动作：
  - approve
  - reject
  - adjust
  - no_action
  - need_more_info
- 决策结果影响：
  - 
- 备注：
  - 
```

以下为 P1 初稿，其中候选动作和部分决策影响并非直接来自 `weed_diagnosis_api.md`，而是基于当前前端模板和编排口径整理的建议规则。

## 复核规则：立即补防复核

- reviewType：
  `additional_control_immediate`
- 触发原因：
  `additional_treatment_diagnosis` 返回 `需要立即补防`
- 人工需要看到的上下文：
  - 药前调查结果
  - 药后调查结果
  - `control_target`
  - 推荐补防日期
  - 推荐补防方案
  - 历史施药日期
- 可选决策动作：
  - approve
  - reject
  - adjust
  - need_more_info
- 决策结果影响：
  - `approve`：新增一个 `WF_STEM_LEAF_WEED` 任务并挂接补防 `OperationPlan`
  - `reject`：不新增补防任务，转人工跟进记录
  - `adjust`：保留补防方向，但允许人工调整时间或备注后再下发
  - `need_more_info`：维持待复核状态，等待补充信息
- 备注：
  - `adjust` 为建议动作，非接口文档直出

## 复核规则：药害缓解处理复核

- reviewType：
  `herbicide_damage_mitigation`
- 触发原因：
  `additional_treatment_diagnosis` 返回 `需缓解药害`
- 人工需要看到的上下文：
  - 药后调查结果
  - 水稻药害等级
  - 历史施药信息
  - 当前计划与田块信息
- 可选决策动作：
  - no_action
  - adjust
  - need_more_info
- 决策结果影响：
  - `no_action`：仅记录人工处理结论，不新增下游 workflow
  - `adjust`：如人工结论为“施肥”或“打药”，则生成后续正式任务；具体 `OperationPlan` 字段后续补充
  - `need_more_info`：维持待复核状态，等待补充信息
- 备注：
  - 第一版先冻结“是否生成后续任务”，具体任务方案结构后续补充


#### 9. 测试场景表

建议至少先覆盖杂草防治主线：

## 场景：计划创建后生成土壤封闭和药前调查

- scenarioId：
  PP-INT-001
- scope：
  integration
- 输入：
  - 创建 PlantingPlan
  - 填入播种日期或移栽日期
- 预期创建或更新对象：
  - 土壤封闭除草任务
  - 茎叶除草药前调查任务
- 不应发生：
  - 日期为空时不应创建任务
- 是否应触发复核：
  否
- 备注：
  - 两个任务分别由各自推荐接口给出时间

## 场景：药前调查达到防治要求后生成茎叶除草

- scenarioId：
  PP-INT-002
- scope：
  integration
- 输入：
  - 茎叶除草药前调查结果录入
  - 茎叶除草处方推荐接口返回达到防治要求
- 预期创建或更新对象：
  - 茎叶除草任务
  - OperationPlan
- 不应发生：
  - 不创建下一次药前调查任务
- 是否应触发复核：
  否
- 备注：
  - 茎叶除草完成后应继续生成药后调查

## 场景：药前调查未达到防治要求

- scenarioId：
  PP-INT-003
- scope：
  integration
- 输入：
  - 茎叶除草药前调查结果录入
  - 茎叶除草处方推荐接口返回未达到防治要求
- 预期创建或更新对象：
  - 下一次药前调查任务
- 不应发生：
  - 不创建茎叶除草任务
  - 不创建 OperationPlan
- 是否应触发复核：
  否
- 备注：
  - 保留 no_action 或 resurvey 的追溯记录

## 场景：药后调查后进入补防

- scenarioId：
  PP-INT-004
- scope：
  integration
- 输入：
  - 茎叶除草完成
  - 药后调查结果录入
  - 杂草补防诊断接口返回需要新增补防
- 预期创建或更新对象：
  - ReviewRequest
- 不应发生：
  - 不直接创建补防正式任务
  - 不直接跳过补防分支进入服务效果评估
- 是否应触发复核：
  是
- 备注：
  - 本阶段约定：先进入 ReviewRequest，再决定后续任务

## 场景：药后调查后无需补防并进入服务评价

- scenarioId：
  PP-INT-005
- scope：
  integration
- 输入：
  - 药后调查结果录入
  - 杂草补防诊断接口返回无需补防
- 预期创建或更新对象：
  - 杂草防治服务效果评估
- 不应发生：
  - 不创建补防任务
- 是否应触发复核：
  否
- 备注：
  - 接口应返回服务效果评估日期

## 场景：服务评价不满意后生成服务效果调查

- scenarioId：
  PP-INT-006
- scope：
  integration
- 输入：
  - 杂草防治服务效果评估结果录入
  - 评价结论为不满意
- 预期创建或更新对象：
  - 服务效果调查任务
- 不应发生：
  - 不直接结束闭环
- 是否应触发复核：
  否
- 备注：
  - 服务效果调查完成后再决定是否进入 Feedback 或 ReviewRequest


#### 10. 待决问题清单

```md
## 待决问题：<问题标题>

- questionId：
- 问题：
- 影响：
- 可选方案：
  - 
- 责任人：
- 目标决策时间：
- 当前状态：
- 备注：
  - 
```


## 当前阶段完成标准

1. 不要求代码提交。
2. 不要求给最终 OperationPlan / ExecutionRecord / Feedback / ReviewRequest JSON。
3. 需要给出任务定义表、触发规则表、依赖关系表、字段清单和场景表，供核心后端后续落到统一对象。
4. 所有需要人工确认或存在歧义的地方都必须显式列出。
5. 算法摘要、场景表和字段草案需遵循总文档统一模板。
