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

## 按植保接入经验补齐的开发材料清单

植保方向在实际接入开发时，真正被后端、前端和编排反复消费的材料，不只是接口摘要，还包括主链路任务清单、冻结口径、字段草案和端到端场景。灌溉方向如果希望尽快进入开发，建议同事至少补齐下面这套材料。

### A. 主链路任务清单

建议按“像 `docs/workflow/checklists/plant-protection-task-checklist.md` 一样可以直接驱动开发”的颗粒度整理：

```text
1. 常规灌溉
2. 排水
3. 水层保持 / 补水
4. 晒田
5. 人工灌溉执行
6. 设备自动灌溉执行
7. 灌溉后达标评价 / 异常反馈
8. 设备异常、执行失败或水位不达标后的人工复核或再次灌溉
```

每个任务项至少写清：

```text
1. 任务触发条件
2. 接口依赖
3. 接口调用时间
4. 接口主要返回结果和分支
5. 系统动作：新增/更新 CalendarItem、TaskIntent、FarmingTask、OperationPlan、ReviewRequest
6. 作业方案：窗口、水量/水位目标、区域、设备参数、验收标准
7. 作业流程：人工/设备/第三方执行、状态回调、轮询兜底、后续动作
8. 任务后续操作：是否进入评价、复核、再次灌溉、结束
```

### B. 建议优先收集的 API 契约文档

以下是建议落点，重点是把契约沉淀成可引用 markdown，而不是继续停留在口头说明或厂商文档截图：

| 建议文件 | 需要包含的内容 |
|---|---|
| `docs/api/irrigation_recommendation_api.md` | 灌溉/排水/晒田推荐接口；说明输入、输出、执行窗口、异常、字段映射 |
| `docs/api/irrigation_device_callback_api.md` | 设备回调协议；说明开始、完成、失败、取消、实时状态上报字段 |
| `docs/api/irrigation_status_polling_api.md` | 轮询兜底接口；说明查询方式、状态码、重试、幂等关联字段 |
| `docs/api/irrigation_evaluation_api.md` | 达标评价或异常反馈接口；说明评价输入、水位/时长/面积类结果和复核触发条件 |
| `docs/api/irrigation_payload_mapping.md` | 入参组装和返回结果对象构建说明；把算法字段如何落到 `OperationPlan / Execution / ExecutionRecord / Feedback` 写清 |

### C. 进入开发前建议冻结的口径

建议在灌溉方向文档里单独列一段“当前冻结口径”，至少拍板这些问题：

```text
1. 哪些灌溉链路直接生成正式任务，哪些只维护 CalendarItem
2. executionMode 第一版支持到什么程度：manual / device / external 各自哪些场景上线
3. 设备执行状态以回调为主还是轮询为主，失败兜底如何定义
4. 水位不达标或执行中断时，是直接生成后续灌溉任务、先触发 ReviewRequest，还是只记录反馈
5. operationArea 和设备分区第一版要求到什么粒度
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 不要求给最终 OperationPlan / ExecutionRecord / Feedback JSON。
3. 需要给出任务定义表、触发规则表、依赖关系表、字段草案和场景表，供核心后端后续统一实现。
4. 对设备回调和轮询的未知点必须单独列出。
5. 算法摘要和场景表需遵循总文档统一模板。
```
