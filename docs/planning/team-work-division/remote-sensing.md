# 遥感监测方向

> 本文档从团队分工总览中拆出，用于单独说明遥感监测方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交影像处理代码、mapper 或对象样例代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 遥感监测 | 遥感算法接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 遥感监测 | `taskCategory / taskSubtype` 定义表 | 定义表 | 产品 / 架构负责人、核心后端 |
| 遥感监测 | 触发规则表和依赖关系表 | 规则表 / 依赖表 | 产品 / 架构负责人、核心后端 |
| 遥感监测 | 方案字段草案 | 字段表 | 核心后端 |
| 遥感监测 | 过程记录、评价、反馈、复核字段草案 | 字段表 / 规则说明 | 核心后端 |
| 遥感监测 | 下游关系说明 | 关系说明 | 产品 / 架构负责人、核心后端 |
| 遥感监测 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 遥感监测 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 明确遥感监测任务类型、触发条件和执行流程。
2. 对接缺苗识别、长势监测、NDVI 长势监测、异常点位识别等算法。
3. 定义遥感监测 OperationPlan.parameters / operationArea / prescriptionMap / acceptanceCriteria。
4. 定义影像上传、影像拼接、算法处理、结果回写的执行记录字段。
5. 明确缺苗识别结果、长势监测结果与后续任务或方案的关系。
6. 定义遥感 Evaluation / Feedback 规则。
7. 明确长势监测与穗肥变量处方图的关系。
```

## 当前阶段非代码任务

```text
1. 遥感监测算法接口摘要：
   按总文档统一算法模板说明影像输入、拼接依赖、输出结构、异常结构、映射目标、异常处理和人工确认点。
2. task 定义表：
   至少按总文档统一格式给出缺苗识别、长势监测、穗肥前监测、效果抽查、异常点位调查相关 workflowKey、taskCategory、taskSubtype、goal、upstreamKeys、downstreamKeys。
3. 触发规则表和依赖关系表：
   按总文档统一格式说明遥感相关 CalendarItem、FarmingTask、OperationPlan、ReviewRequest 的触发来源、阻断条件、依赖关系和 fallbackAction。
4. 方案字段草案：
   列出监测任务后续至少需要哪些方案字段，不要求现在给最终 OperationPlan JSON。
5. 过程记录、评价、反馈、复核字段草案：
   列出影像上传、拼接、算法处理、结果确认分别需要记录哪些字段，并说明哪些字段进入 Evaluation / Feedback / ReviewRequest。
6. 下游关系说明：
   说明缺苗识别、长势监测与补苗、复核、施肥处方图之间的关系。
7. 至少 3 个测试场景：
   - 缺苗识别生成缺苗区域重大事件或复核事项。
   - 常规长势监测生成长势状态更新和异常点位。
   - 穗肥前长势监测生成变量处方图并供施穗肥方案使用。
8. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
9. 文档回写要求：
   如涉及新的 workflow、taskSubtype 或后台任务，需同步更新 docs/workflow/task-workflow-matrix.md 和 docs/workflow/background-job-matrix.md。
```

### 直接提交模板

#### 1. 遥感监测算法接口摘要

```md
## remote_sensing_algorithm

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

#### 5. `OperationPlan` / 监测方案字段表

```md
| field | required | meaning | source | example | notes |
|---|---|---|---|---|---|
| planType | yes | 方案类型 | 固定值或规则 | remote_sensing_monitoring |  |
| algorithmCode | no | 方案来源算法 | 算法 | growthMonitoringAlgorithm |  |
| executionMode | yes | 执行方式 | 业务约定 | external |  |
| operationWindowStart | no | 建议开始时间 | 规则或调度 |  |  |
| operationWindowEnd | no | 建议结束时间 | 规则或调度 |  |  |
| parameters | yes | 监测目的、影像类型、算法参数等 | 业务约定 |  |  |
| operationArea | no | 监测区域 | 计划或算法 |  |  |
| prescriptionMap | no | 变量处方图 | 算法 |  |  |
| acceptanceCriteria | no | 验收标准 | 业务约定 |  |  |
| riskNotes | no | 风险提示 | 算法或人工 |  |  |
```

#### 6. 过程记录 / 评价 / 反馈 / 复核字段表

```md
| objectType | field | type | required | meaning | example | notes |
|---|---|---|---|---|---|---|
| ExecutionRecord |  |  |  |  |  |  |
| Evaluation |  |  |  |  |  |  |
| Feedback |  |  |  |  |  |  |
| ReviewRequest |  |  |  |  |  |  |
```

#### 7. 下游关系表

```md
| sourceResult | downstreamType | downstreamKey | triggerCondition | output | notes |
|---|---|---|---|---|---|
```

#### 8. 测试场景表

```md
| scenarioId | scenarioName | scope | input | expectedCreatedObjects | expectedNoAction | expectedReview | notes |
|---|---|---|---|---|---|---|---|
| RS-INT-001 | 缺苗识别生成复核事项 | integration | 缺苗识别结果 high_risk | Evaluation / Feedback / ReviewRequest | 不直接创建补苗任务 | yes |  |
| RS-INT-002 | 常规长势监测生成状态更新和异常点位 | integration | 长势监测结果 | Evaluation / Feedback | 不创建无关方案 | conditional |  |
| RS-INT-003 | 穗肥前长势监测生成变量处方图 | integration | 长势结果 + 施肥衔接 | prescriptionMap / OperationPlan | 不重复创建监测任务 | no |  |
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
3. 需要给出任务定义表、触发规则表、依赖关系表、字段草案和下游关系说明，供核心后端后续统一实现。
4. 遥感过程记录必须拆分成多个步骤描述，不能只描述最终结果。
5. 算法摘要和场景表需遵循总文档统一模板。
```
