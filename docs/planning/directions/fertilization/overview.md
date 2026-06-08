# 施肥方向

> 本文档从团队分工总览中拆出，用于单独说明施肥方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交施肥方案代码、库存扣减代码或对象样例代码。

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
2. 区分基肥、分蘖肥、穗肥、发苗肥、促芽肥等参数。
3. 明确穗肥前长势监测到变量处方图的关系。
4. 明确是否需要 prescriptionMap。
5. 明确肥料类型、用量、面积、作业窗口和验收标准。
6. 明确施肥作业执行记录、效果抽查和反馈规则。
7. 明确施肥与库存物料的关系。
```

## 当前阶段非代码任务

```text
1. 施肥算法接口摘要：
   按总文档统一算法模板说明输入字段、推荐输出、异常结构、映射目标和 fallbackAction。
2. task 定义表：
   至少按总文档统一格式给出基肥、分蘖肥、穗肥、发苗肥、促芽肥、效果抽查相关 workflowKey、taskCategory、taskSubtype、goal、upstreamKeys、downstreamKeys。
3. 触发规则表和依赖关系表：
   按总文档统一格式说明施肥相关 CalendarItem、FarmingTask、OperationPlan、ReviewRequest 的触发来源、阻断条件、依赖关系和 fallbackAction。
4. 方案字段草案：
   分别列出基肥、分蘖肥、穗肥至少需要哪些方案字段，不要求现在给最终 OperationPlan JSON。
5. 处方图字段草案：
   说明变量处方图需要表达哪些信息，以及与施肥方案的关系。
6. 执行、评价、反馈、复核字段草案：
   列出施肥执行、效果抽查、异常反馈至少需要哪些字段，并说明哪些字段进入 Evaluation / Feedback / ReviewRequest。
7. 库存关系说明：
   说明肥料库存、出库、实际消耗之间的业务关系和关键字段，不要求现在落到表结构。
8. 至少 3 个测试场景：
   - 常规施肥生成 OperationPlan 并完成执行反馈。
   - 穗肥前长势监测生成变量处方图。
   - 穗肥效果抽查发现异常并触发 ReviewRequest。
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
| FE-INT-003 | 效果抽查异常触发复核 | integration | 抽查结果 warning/fail | Evaluation / Feedback / ReviewRequest | 不标记 fully_passed | yes |  |
```

#### 10. 待决问题清单

```md
| questionId | question | impact | options | owner | targetDecisionDate | status | notes |
|---|---|---|---|---|---|---|---|
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / prescriptionMap / ExecutionRecord / Feedback JSON。
3. 需要给出任务定义表、触发规则表、依赖关系表、字段草案和场景表，供核心后端后续统一实现。
4. 施肥参数差异、处方图和库存关系必须显式写清。
5. 算法摘要和场景表需遵循总文档统一模板。
```
