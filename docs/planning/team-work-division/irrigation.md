# 灌溉方向

> 本文档从团队分工总览中拆出，用于单独说明灌溉方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交设备回调代码、mapper 或测试代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 灌溉 | 灌溉算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 灌溉 | `taskCategory / taskSubtype` 定义表 | 定义表 | 产品 / 架构负责人、核心后端 |
| 灌溉 | 触发规则表和依赖关系表 | 规则表 / 依赖表 | 产品 / 架构负责人、核心后端 |
| 灌溉 | 方案字段草案 | 字段表 | 核心后端 |
| 灌溉 | 执行、评价、反馈、复核字段草案 | 字段表 / 规则说明 | 核心后端 |
| 灌溉 | 设备回调 / 轮询说明 | 协议字段说明 | 核心后端 |
| 灌溉 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 灌溉 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 补充灌溉算法接口文档。
2. 明确灌溉任务类型、触发条件和执行流程。
3. 明确灌溉 OperationPlan.parameters。
4. 明确是否需要 operationArea / prescriptionMap。
5. 明确执行模式：人工、设备、第三方系统。
6. 明确设备回调、轮询和人工反馈的数据格式。
7. 定义灌溉 Evaluation / Feedback 规则。
```

## 当前阶段非代码任务

```text
1. 灌溉算法接口摘要：
   按总文档统一算法模板说明推荐输入、返回结果、执行窗口、异常结构、映射目标、失败处理和外部依赖。
2. task 定义表：
   至少按总文档统一格式给出灌溉、排水、水层保持、晒田相关 workflowKey、taskCategory、taskSubtype、goal、upstreamKeys、downstreamKeys。
3. 触发规则表和依赖关系表：
   按总文档统一格式说明灌溉相关 CalendarItem、FarmingTask、OperationPlan、ReviewRequest 的触发来源、阻断条件、依赖关系和 fallbackAction。
4. 方案字段草案：
   列出后续灌溉方案至少需要哪些字段，例如水量、水位目标、区域、设备参数、验收标准；不要求现在给最终 OperationPlan JSON。
5. 执行、评价、反馈、复核字段草案：
   列出人工执行、设备执行、第三方执行分别需要记录哪些字段，并说明哪些字段进入 Evaluation / Feedback / ReviewRequest。
6. 设备回调 / 轮询说明：
   明确外部执行状态需要哪些字段，不要求现在定最终 ExecutionRecord 结构。
7. 至少 3 个测试场景：
   - 算法推荐灌溉并生成 OperationPlan。
   - 设备执行成功并生成 Feedback completed。
   - 设备异常或水位不达标并触发 ReviewRequest。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
9. 文档回写要求：
   如涉及新的 workflow、taskSubtype 或后台任务，需同步更新 docs/workflow/task-workflow-matrix.md 和 docs/workflow/background-job-matrix.md。
```

### 直接提交模板

#### 1. 灌溉算法接口摘要

```md
## irrigation_algorithm

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
| planType | yes | 方案类型 | 固定值或规则 | irrigation_control |  |
| algorithmCode | no | 方案来源算法 | 算法 | irrigationRecommendationAlgorithm |  |
| executionMode | yes | 执行方式 | 业务约定 | device | manual / device / external |
| operationWindowStart | no | 建议开始时间 | 算法 |  |  |
| operationWindowEnd | no | 建议结束时间 | 算法 |  |  |
| parameters | yes | 水量、水位目标、设备参数 | 算法 |  |  |
| operationArea | no | 作业区域 | 计划或算法 |  |  |
| acceptanceCriteria | no | 验收标准 | 业务约定 |  |  |
| riskNotes | no | 风险提示 | 算法或人工 |  |  |
```

#### 6. 执行 / 评价 / 反馈 / 复核字段表

```md
| objectType | field | type | required | meaning | example | notes |
|---|---|---|---|---|---|---|
| ExecutionRecord |  |  |  |  |  |  |
| Evaluation |  |  |  |  |  |  |
| Feedback |  |  |  |  |  |  |
| ReviewRequest |  |  |  |  |  |  |
```

#### 7. 设备回调 / 轮询字段表

```md
| field | type | required | source | meaning | example | notes |
|---|---|---|---|---|---|---|
```

#### 8. 测试场景表

```md
| scenarioId | scenarioName | scope | input | expectedCreatedObjects | expectedNoAction | expectedReview | notes |
|---|---|---|---|---|---|---|---|
| IR-INT-001 | 算法推荐灌溉并生成方案 | integration | 推荐算法返回灌溉方案 | OperationPlan / FarmingTask | 不创建 ReviewRequest | no |  |
| IR-INT-002 | 设备执行成功并完成反馈 | integration | 执行回调 success | Execution / ExecutionRecord / Feedback | 不创建异常复核 | no |  |
| IR-INT-003 | 设备异常或水位不达标触发复核 | integration | 执行异常或评价 fail | Evaluation / Feedback / ReviewRequest | 不标记 completed | yes |  |
```

#### 9. 待决问题清单

```md
| questionId | question | impact | options | owner | targetDecisionDate | status | notes |
|---|---|---|---|---|---|---|---|
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / ExecutionRecord / Feedback JSON。
3. 需要给出任务定义表、触发规则表、依赖关系表、字段草案和场景表，供核心后端后续统一实现。
4. 对设备回调和轮询的未知点必须单独列出。
5. 算法摘要和场景表需遵循总文档统一模板。
```
