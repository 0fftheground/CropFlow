# 农事日历 / 生育期方向

> 本文档从团队分工总览中拆出，用于单独说明农事日历 / 生育期方向的职责和交付要求。

## 当前阶段说明

当前处于核心对象、ER 图、API contract 仍在收敛的阶段。

因此本方向当前任务以非代码交付为主，用于补齐后续接入契约，而不是立即提交 adapter、mapper 或测试代码。

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 农事日历 / 生育期 | 生育期预测接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 农事日历 / 生育期 | 农事日历接口摘要 | Markdown 摘要 | 核心后端、产品 / 架构负责人 |
| 农事日历 / 生育期 | `stageCode` 清单 | 表格 | 产品 / 架构负责人 |
| 农事日历 / 生育期 | 日历相关 `taskCategory / taskSubtype` 定义和映射 | 定义表 / 映射表 | 产品 / 架构负责人、核心后端 |
| 农事日历 / 生育期 | 触发规则表和依赖关系表 | 规则表 / 依赖表 | 产品 / 架构负责人、核心后端 |
| 农事日历 / 生育期 | 生育期变化影响范围 | 规则说明 | 产品 / 架构负责人、核心后端 |
| 农事日历 / 生育期 | 到期生成条件草案 | 条件表 / 规则草案 | 核心后端 |
| 农事日历 / 生育期 | 测试场景表 | 场景表 | 无，必要时核心后端确认 |
| 农事日历 / 生育期 | 待决问题清单 | 问题列表 | 产品 / 架构负责人、核心后端 |

## 主要职责

```text
1. 对接生育期预测接口。
2. 对接农事日历接口。
3. 明确 stageCode 和 taskSubtype 映射。
4. 定义 CalendarItem 的生成、更新、失效和重算规则。
5. 定义生育期变化后哪些 CalendarItem / FarmingTask / OperationPlan 会受影响。
6. 定义 TaskDueCheckJob 如何把到期 CalendarItem 转为 FarmingTask。
```

## 当前阶段非代码任务

```text
1. 生育期预测接口摘要：
   按总文档统一算法模板说明用途、触发时机、输入来源、输入输出字段、异常结构、映射目标和未决问题。
2. 农事日历接口摘要：
   按总文档统一算法模板说明输入依赖、输出字段、版本信息、异常结构和失效重算触发条件。
3. stageCode 清单：
   至少给出阶段名称、内部编码、适用作物、是否允许人工录入。
4. 日历相关 task 定义和映射表：
   至少按总文档统一格式给出 workflowKey、taskCategory、taskSubtype、goal、upstreamKeys、downstreamKeys。
5. 触发规则表和依赖关系表：
   按总文档统一格式说明 CalendarItem、TaskIntent、FarmingTask 的触发来源、阻断条件、依赖关系和 fallbackAction。
6. 生育期变化影响说明：
   明确阶段变化后哪些日历项需要更新、失效或仅提示人工关注。
7. 到期生成条件草案：
   说明什么情况下日历项应进入正式任务生成窗口，阻断条件有哪些。
8. 测试场景表：
   至少包含计划初始化、天气变化、人工录入真实生育期 3 类场景。
9. 待决问题清单：
   统一列出需要核心后端或产品 / 架构负责人拍板的点。
10. 文档回写要求：
   如涉及新的 workflow、taskSubtype 或后台任务，需同步更新 docs/workflow/task-workflow-matrix.md 和 docs/workflow/background-job-matrix.md。
```

### 直接提交模板

#### 1. 生育期预测接口摘要

```md
## stage_prediction_algorithm

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

#### 2. 农事日历接口摘要

```md
## agronomy_calendar_algorithm

### 1. 基本信息
- algorithmCode:
- algorithmName:
- purpose:
- owner:
- endpoint:
- method:
- auth:

### 2. 输入依赖
| field | type | required | source | example | notes |
|---|---|---|---|---|---|

### 3. 输出结果
| field | type | meaning | example | targetObject | targetField |
|---|---|---|---|---|---|

### 4. 失效 / 重算触发条件
| triggerSource | condition | affectedObjects | action | notes |
|---|---|---|---|---|
```

#### 3. `stageCode` 清单

```md
| stageCode | stageName | cropType | sequence | allowsManualInput | notes |
|---|---|---|---|---|---|
```

#### 4. 日历相关 task 定义和映射表

```md
| workflowKey | taskCategory | taskSubtype | taskName | generalFlowKey | stageScope | goal | requiresOperationPlan | requiresExecution | requiresReview | upstreamKeys | downstreamKeys | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
```

#### 5. 触发规则表

```md
| targetType | targetKey | triggerType | triggerSource | preconditions | blockingConditions | action | idempotencyKeySuggestion | fallbackAction |
|---|---|---|---|---|---|---|---|---|
```

#### 6. 依赖关系表

```md
| currentKey | dependencyType | dependsOn | dependencyRule | missingDependencyAction | satisfiedOutput |
|---|---|---|---|---|---|
```

#### 7. 生育期变化影响表

```md
| changeType | affectedObjectType | affectedKey | effect | followUpAction | notes |
|---|---|---|---|---|---|
```

#### 8. 到期生成条件表

```md
| workflowKey | sourceCalendarType | dueWindowRule | preconditions | blockingConditions | outputObject | notes |
|---|---|---|---|---|---|---|
```

#### 9. 测试场景表

```md
| scenarioId | scenarioName | scope | input | expectedCreatedObjects | expectedNoAction | expectedReview | notes |
|---|---|---|---|---|---|---|---|
| CS-INT-001 | 计划初始化生成日历项 | integration | PlanCreated + stage_prediction_algorithm + agronomy_calendar_algorithm | CropStageState / CalendarItem | 不创建 FarmingTask | no |  |
| CS-INT-002 | 天气变化触发阶段更新和日历重算 | integration | WeatherUpdated | StagePredictionSnapshot / CalendarItem updated | 不重复创建无变化项 | no |  |
| CS-INT-003 | 人工录入真实生育期后重算影响项 | integration | ActualStageRecorded | CropStageState / invalidated CalendarItem | 不直接生成执行任务 | conditional |  |
```

#### 10. 待决问题清单

```md
| questionId | question | impact | options | owner | targetDecisionDate | status | notes |
|---|---|---|---|---|---|---|---|
```

## 当前阶段完成标准

```text
1. 不要求代码提交。
2. 所有交付物都应能被核心后端用来定义模型字段、API contract 和后续规则实现。
3. 所有未定事项必须显式列出，不能省略。
4. 不要求给 CalendarItem / FarmingTask 的最终 JSON，只需给字段和语义草案。
5. 任务定义表、触发规则表、依赖关系表和场景表需遵循总文档统一模板。
```
