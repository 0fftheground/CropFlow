# 施肥方向

> 本文档从团队分工总览中拆出，用于单独说明施肥方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交施肥方案代码、库存扣减代码或对象样例代码。

推荐产出顺序：

```text
1. 先整理 docs/workflow/checklists/fertilization-task-checklist.md
2. 再生成并人工核查 docs/fde/fertilization-fde-draft.md
3. 已冻结的方向知识和交付要求再回写到本文件
4. 其中流程事实、接口契约、字段口径仍需同步回 docs/workflow/、docs/api/、docs/model/
```

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 施肥 | 施肥算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 施肥 | `taskCategory / taskSubtype` 定义表 | 定义表 | 产品 / 架构负责人、核心后端 |
| 施肥 | 触发规则表和依赖关系表 | 规则表 / 依赖表 | 产品 / 架构负责人、核心后端 |
| 施肥 | 方案字段草案 | 字段表 | 核心后端 |
| 施肥 | 处方图字段草案 | 字段表 / 结构说明 | 核心后端 |
| 施肥 | 执行、评价、反馈、复核字段草案 | 字段表 / 规则说明 | 核心后端 |
| 施肥 | 库存关系说明 | 关系说明 / 字段草案 | 核心后端、产品 / 架构负责人 |
| 施肥 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 施肥 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 补充施肥算法接口文档。
2. 区分基肥、分蘖肥、穗肥等本轮施肥主链路参数；再生稻发苗肥、促芽肥暂不纳入本轮 FDE。
3. 明确穗肥前长势监测到变量处方图的关系。
4. 明确是否需要 prescriptionMap。
5. 明确肥料类型、用量、面积、作业窗口和验收标准。
6. 明确施肥作业执行记录、效果评估和反馈规则。
7. 明确施肥与库存物料的关系。
```

## 当前阶段非代码任务

```text
1. 施肥算法接口摘要：
   按总文档统一算法模板说明输入字段、推荐输出、异常结构、映射目标和 fallbackAction。
2. task 定义表：
   至少按总文档统一格式给出基肥、分蘖肥、穗肥、施肥效果评估相关 workflowKey、taskCategory、taskSubtype、goal、upstreamKeys、downstreamKeys；再生稻发苗肥、促芽肥后续单独补充。
3. 触发规则表和依赖关系表：
   按总文档统一格式说明施肥相关 CalendarItem、FarmingTask、OperationPlan、ReviewRequest 的触发来源、阻断条件、依赖关系和 fallbackAction。
4. 方案字段草案：
   分别列出基肥、分蘖肥、穗肥至少需要哪些方案字段，不要求现在给最终 OperationPlan JSON。
5. 处方图字段草案：
   说明变量处方图需要表达哪些信息，以及与施肥方案的关系。
6. 执行、评价、反馈、复核字段草案：
   列出施肥执行、效果评估、异常反馈至少需要哪些字段，并说明哪些字段进入 Evaluation / Feedback / ReviewRequest。
7. 库存关系说明：
   说明肥料库存、出库、实际消耗之间的业务关系和关键字段，不要求现在落到表结构。
8. 至少 3 个测试场景：
   - 常规施肥生成 OperationPlan 并完成执行反馈。
   - 穗肥前长势监测生成变量处方图。
   - 施肥效果评估发现异常后触发人工处理农事，人工处理结果目前仅记录并结束。
9. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
10. 文档回写要求：
   如涉及新的 workflow、taskSubtype 或后台任务，需同步更新 docs/workflow/task-workflow-matrix.md 和 docs/workflow/background-job-matrix.md。
```

### 直接提交模板

#### 1. 施肥算法接口摘要

```md
## fertilization_algorithm

### 1. 基本信息
- algorithmCode:
- algorithmName:
- purpose:
- owner:
- endpoint:
- method:
- auth:

### 2. 触发时机
- upstream workflowKey / jobKey:
- trigger event:
- trigger step:
- whether sync or async:

### 3. 请求输入
| field | type | required | source | example | notes |
|---|---|---|---|---|---|

### 4. 响应输出
| field | type | meaning | example | targetObject | targetField |
|---|---|---|---|---|---|

### 5. 异常返回
| code | meaning | retryable | fallbackAction | notes |
|---|---|---|---|---|
```

#### 2. task 定义表

```md
| workflowKey | taskCategory | taskSubtype | taskName | generalFlowKey | stageScope | goal | requiresOperationPlan | requiresExecution | requiresReview | upstreamKeys | downstreamKeys | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
```

#### 3. 触发规则表

```md
| targetType | targetKey | triggerType | triggerSource | preconditions | blockingConditions | action | idempotencyKeySuggestion | fallbackAction |
|---|---|---|---|---|---|---|---|---|
```

#### 4. 依赖关系表

```md
| currentKey | dependencyType | dependsOn | dependencyRule | missingDependencyAction | satisfiedOutput |
|---|---|---|---|---|---|
```

#### 5. `OperationPlan` 字段草案表

```md
| field | required | meaning | source | example | notes |
|---|---|---|---|---|---|
| planType | yes | 方案类型 | 固定值或规则 | fertilization_prescription |  |
| algorithmCode | no | 方案来源算法 | 算法 | fertilizationRecommendationAlgorithm |  |
| executionMode | yes | 执行方式 | 业务约定 | manual |  |
| operationWindowStart | no | 建议开始时间 | 算法或规则 |  |  |
| operationWindowEnd | no | 建议结束时间 | 算法或规则 |  |  |
| parameters | yes | 肥料品类、用量、单位等 | 算法 |  |  |
| operationArea | no | 作业区域 | 计划或算法 |  |  |
| prescriptionMap | no | 变量处方图 | 算法 |  |  |
| acceptanceCriteria | no | 验收标准 | 业务约定 |  |  |
| riskNotes | no | 风险提示 | 算法或人工 |  |  |
```

#### 6. 处方图字段表

```md
| field | type | required | meaning | source | example | notes |
|---|---|---|---|---|---|---|
```

#### 7. 执行 / 评价 / 反馈 / 复核字段表

```md
| objectType | field | type | required | meaning | example | notes |
|---|---|---|---|---|---|---|
| ExecutionRecord |  |  |  |  |  |  |
| Evaluation |  |  |  |  |  |  |
| Feedback |  |  |  |  |  |  |
| ReviewRequest |  |  |  |  |  |  |
```

#### 8. 库存关系表

```md
| businessAction | inventoryObject | changeType | requiredFields | notes |
|---|---|---|---|---|
```

#### 9. 测试场景表

```md
| scenarioId | scenarioName | scope | input | expectedCreatedObjects | expectedNoAction | expectedReview | notes |
|---|---|---|---|---|---|---|---|
| FE-INT-001 | 常规施肥生成方案并完成反馈 | integration | 推荐算法返回施肥方案 + 执行完成 | OperationPlan / ExecutionRecord / Feedback | 不创建复核 | no |  |
| FE-INT-002 | 穗肥前长势监测生成变量处方图 | integration | 长势结果 + 施肥算法输入 | prescriptionMap / OperationPlan | 不直接关闭施肥任务 | no |  |
| FE-INT-003 | 施肥效果评估异常触发人工处理 | integration | 评估结果 warning/fail | Evaluation / Feedback / 人工处理 FarmingTask | 不标记 fully_passed | yes | 人工处理结果目前仅记录并结束 |
```

#### 10. 待决问题清单

```md
| questionId | question | impact | options | owner | targetDecisionDate | status | notes |
|---|---|---|---|---|---|---|---|
```

## 按植保接入经验补齐的开发材料清单

植保方向在实际接入开发时，真正推动后端、前端和编排并行工作的材料，不只是接口摘要，还包括主链路任务清单、冻结口径、字段草案和端到端场景。施肥方向如果希望尽快进入开发，建议同事至少补齐下面这套材料。

### A. 主链路任务清单

建议按“像 `docs/workflow/checklists/plant-protection-task-checklist.md` 一样可以直接驱动开发”的颗粒度整理：

```text
1. 基肥
2. 分蘖肥
3. 穗肥
4. 穗肥前长势监测触发变量处方图
5. 施肥效果评估 / 服务评价
6. 施肥效果评估异常后的人工处理记录

注：再生稻发苗肥、促芽肥暂不纳入本轮施肥 FDE，后续如恢复范围，应另起材料补齐 task 定义、触发和上下游关系。
```

每个任务项至少写清：

```text
1. 任务触发条件
2. 接口依赖
3. 接口调用时间
4. 接口主要返回结果和分支
5. 系统动作：新增/更新 CalendarItem、TaskIntent、FarmingTask、OperationPlan；仅在 FDE 明确需要人工审核或人工判断时创建 ReviewRequest
6. 作业方案：窗口、肥料类型、用量、处方图、验收标准
7. 作业流程：人工/设备/第三方执行、结果回传、后续动作
8. 任务后续操作：是否进入效果评估、复核、再次施肥、结束
```

### B. 建议优先收集的 API 契约文档

以下是建议落点，重点是把契约沉淀成可引用 markdown，而不是继续停留在口头说明或截图：

| 建议文件 | 需要包含的内容 |
|---|---|
| `docs/api/fertilization_prescription_algorithm_api.md` | 当前施肥处方算法 `POST /run` 开发 contract；覆盖入参组装、响应解析、错误处理和 `OperationPlan.parameters` 映射 |
| `docs/api/fertilization_prescription_map_api.md` | 变量处方图或分区处方接口；说明 `prescriptionMap` 的结构、区域粒度、单位、分区标识 |
| `docs/api/fertilization_effect_evaluation_api.md` | 施肥效果评估接口；说明评估输入、评价结果、异常分支和人工处理记录口径 |
| `docs/api/fertilization_inventory_mapping.md` | 不是算法接口也建议补；说明肥料品类、库存扣减、实际消耗、批次或单位换算关系 |
| `docs/api/fertilization_payload_mapping.md` | 后续如施肥方向 API 增多，可独立补入参组装和返回结果对象构建说明；当前处方算法映射先以 `fertilization_prescription_algorithm_api.md` 为准 |

### C. 当前冻结口径

当前已明确的施肥方向口径：

```text
1. 施肥处方和变量穗肥处方都先人工审核。
2. 人工审核通过后的施肥处方，直接写正式 OperationPlan 并推进下游任务生成。
3. prescriptionMap 第一版仅在穗肥前长势联动生成变量处方图时使用。
4. 穗肥变量处方图系统内只保存远程公开 URL，不保存完整图内容，不做签名 URL 或平台代理转发。
5. 施肥效果评估异常触发人工处理农事后，人工处理结果目前仅记录并结束。
6. 施肥算法只返回样本点的单位面积施肥量，系统侧映射 / 补充为地块维度的单位面积施肥量，不要求算法返回地块绝对施肥总量。
7. 再生稻发苗肥、促芽肥暂不纳入本轮 FDE。
8. 土样采集第一版不生成二维码。
9. 长势监测流程以无人机监测执行记录和遥感后续任务 id 串接影像上传、影像拼接。
10. M3 / healthy 模式必需字段已确认，按 FDE 字段口径组装算法入参。
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / prescriptionMap / ExecutionRecord / Feedback JSON。
3. 需要给出任务定义表、触发规则表、依赖关系表、字段草案和场景表，供核心后端后续统一实现。
4. 施肥参数差异、处方图和库存关系必须显式写清。
5. 算法摘要和场景表需遵循总文档统一模板。
```
