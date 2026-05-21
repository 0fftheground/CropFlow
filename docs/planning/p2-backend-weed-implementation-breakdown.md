# P2 杂草防治后端实现拆分

本文档用于把当前已经冻结的杂草防治样板链路，拆成可执行的后端实现任务包。

适用阶段：

```text
P2 - 核心工程骨架与最小实现
```

目标：

```text
1. 基于当前已冻结的 API contract、workflow、data-model 和 migration 范围，启动后端工程实现。
2. 第一条样板链路覆盖杂草防治全环节，而不是只覆盖单个茎叶除草任务。
3. 运行期诊断结果先形成 TaskIntent / ReviewRequest，人工审核通过后再创建正式 FarmingTask / OperationPlan。
4. 让后端 owner、模块 owner 和联调同学可以按统一拆分并行推进。
```

## 1. 当前实现边界

本轮覆盖：

```text
1. 土壤封闭除草建议与审核。
2. 药前调查日期推荐、药前调查执行、weed_treatment_diagnosis。
3. 茎叶除草建议审核、正式任务创建、作业执行。
4. 药后调查日期推荐。
5. 安全性调查、injury_mitigation_diagnosis。
6. 防效兼安全性调查、additional_treatment_diagnosis。
7. 补防、药害缓解、补充调查、服务效果评估日期的后续生成。
```

本轮不覆盖：

```text
1. DeviceCommand。
2. InventoryItem / InventoryTransaction。
3. workflowKey / workflowStepKey / generalFlowKey / chainKey 的正式落库。
4. 完整 stageCode 枚举收敛。
5. 通用工作流引擎。
```

## 2. 样板链路范围

第一条样板链路明确覆盖以下业务环节：

```text
1. 土壤封闭除草。
2. 药前调查。
3. 茎叶除草。
4. 药后调查日期推荐。
5. 安全性调查。
6. 药害缓解。
7. 防效兼安全性调查。
8. 补防判断。
9. 补充调查。
10. 服务效果评估日期生成。
```

核心编排原则：

```text
1. 纯日期推荐结果 -> CalendarItem。
2. 具体农事建议 / 处置建议 -> TaskIntent -> ReviewRequest。
3. ReviewRequest 审核通过后 -> FarmingTask。
4. 正式 FarmingTask 创建后，才创建对应 OperationPlan。
5. 运行期生成的新对象必须保留 parentTaskId / sourceExecutionId / sourceExecutionRecordId。
```

## 3. 关键事件与链路入口

### 3.1 后台入口

需要落地的后台任务：

| 任务 | 作用 | 输出 |
|---|---|---|
| `SurveyDateRecommendationJob` | 周期调用调查日期推荐算法 | 调查类 `CalendarItem` |
| `TaskDueCheckJob` | 检查到期 `CalendarItem` 并生成正式调查任务 | 调查类 `FarmingTask` |
| `ExecutionStatusPollingJob` | 轮询兜底外部执行状态 | `ExecutionStatusUpdated` |

### 3.2 运行期入口

需要落地的领域事件：

| 事件 | 来源 | 主要处理器 |
|---|---|---|
| `SurveyResultRecorded` | 调查类 `ExecutionRecord` 录入完成 | `SurveyResultRecordedHandler` |
| `ReviewRequestResolved` | 人工审核完成 | `ReviewRequestResolvedHandler` |
| `ExecutionStatusUpdated` | HW 回调或轮询结果 | `ExecutionStatusUpdatedHandler` |
| `FeedbackGenerated` | 作业反馈生成 | `FeedbackGeneratedHandler` |

### 3.3 算法调用入口

杂草样板链路需要接入以下接口：

| 接口 | 主要用途 |
|---|---|
| `soil_treatment_diagnosis` | 土壤封闭建议 |
| `weed_survey_date_diagnosis` | 药前调查日期推荐 |
| `weed_treatment_diagnosis` | 药前调查后给出重新调查或防治建议 |
| `after_treatment_survey_date_diagnosis` | 药后调查日期推荐 |
| `injury_mitigation_diagnosis` | 安全性调查后药害缓解建议 |
| `additional_treatment_diagnosis` | 防效兼安全性调查后的补防 / 补充调查 / 服务评估分支 |

## 4. 后端实现任务包

### 4.1 工程骨架与迁移环境

目标：

```text
建立 FastAPI + SQLAlchemy + Alembic 最小工程骨架，并能执行当前 v1 migration。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| B1 | 初始化后端目录结构 | `app/`, `models/`, `repositories/`, `services/`, `orchestrator/`, `jobs/`, `api/`, `tests/` |
| B2 | 初始化数据库配置和 session 管理 | PostgreSQL 连接、事务边界 |
| B3 | 接入 Alembic | 迁移环境、版本目录、执行说明 |
| B4 | 导入现有 `001~006` migration | 可执行 migration 链 |

完成标志：

```text
1. 本地可以创建空库并跑完 001~006。
2. 可以通过脚本或 Makefile 启动后端服务。
```

### 4.2 核心 ORM 模型与 Repository

目标：

```text
把当前已冻结的数据模型落成代码层实体和最小读写仓储。
```

第一批必须实现的对象：

| 对象 | 说明 |
|---|---|
| `PlantingPlan` | 计划上下文 |
| `EventRecord` | 输入事件与编排痕迹 |
| `CalendarItem` | 预备农事项 |
| `TaskIntent` | 待审核建议 |
| `ReviewRequest` | 人工审核事项 |
| `FarmingTask` | 正式任务 |
| `OperationPlan` | 正式作业方案 |
| `Execution` | 执行实体 |
| `ExecutionRecord` | 调查记录 / 执行记录 |

必须体现的字段：

```text
1. parentTaskId
2. sourceExecutionId
3. sourceExecutionRecordId
4. ReviewRequest.decisionPayload
5. TaskIntent.ruleResult
6. CalendarItem.generationCondition
7. ExecutionRecord.resultPayload
```

Repository 最小能力：

```text
1. 按 planId 查询当前未关闭 CalendarItem / TaskIntent / ReviewRequest / FarmingTask。
2. 按 parentTaskId / sourceExecutionRecordId 回查派生对象。
3. 查询调查任务最近一次 ExecutionRecord。
4. 查询某条 ReviewRequest 对应的 source entity。
```

### 4.3 杂草算法 Adapter 与入参组装

目标：

```text
统一封装 6 个杂草接口调用，不让 Handler 直接拼 HTTP 请求。
```

建议模块：

| 模块 | 责任 |
|---|---|
| `WeedDiagnosisClient` | 对外 HTTP 调用 |
| `WeedDiagnosisInputBuilder` | 从领域对象组装接口入参 |
| `WeedDiagnosisResultMapper` | 把接口结果映射为 `CalendarItem` / `TaskIntent` / `ReviewRequest` 候选 |

实现要求：

```text
1. 入参来源必须对齐 docs/api/weed_diagnosis_api入参组装和返回结果对象构建.md。
2. 天气数据由系统侧 provider 或 adapter 注入，不由算法接口层自行取数。
3. 结果映射不能直接跳过 ReviewRequest 生成正式 FarmingTask。
4. 不同接口返回的 no_action、日期推荐、具体措施建议要明确分流。
```

### 4.4 Calendar 与调查任务生成

目标：

```text
让药前调查、药后调查、补充调查、服务效果评估等日期推荐能形成可执行任务。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| C1 | 实现 `SurveyDateRecommendationJob` 最小框架 | 周期任务入口 |
| C2 | 接入 `weed_survey_date_diagnosis` | 药前调查 `CalendarItem` |
| C3 | 接入 `after_treatment_survey_date_diagnosis` | 安全性调查 / 防效兼安全性调查 `CalendarItem` |
| C4 | 处理 `additional_survey_date` / `service_effect_evaluation_date` | 补充调查 / 服务评估 `CalendarItem` |
| C5 | 实现 `TaskDueCheckJob` + `TaskGenerationService` | 调查类 `CalendarItem` 到期后生成调查 `FarmingTask` |

注意：

```text
1. 这部分只负责调查类 CalendarItem -> 调查类 FarmingTask。
2. 不负责把运行期防治建议直接生成为正式防治任务。
```

### 4.5 调查结果事件与运行期诊断

目标：

```text
调查结果录入后，统一回到 Plan Orchestrator，触发杂草运行期诊断。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| D1 | 定义 `SurveyResultRecorded` 事件结构 | 事件 payload |
| D2 | 实现 `SurveyResultRecordedHandler` | 按 `taskSubtype` 分流 |
| D3 | 识别药前调查触发 `weed_treatment_diagnosis` | 重新调查或防治建议 |
| D4 | 识别安全性调查触发 `injury_mitigation_diagnosis` | no_action 或药害缓解建议 |
| D5 | 识别防效兼安全性调查触发 `additional_treatment_diagnosis` | 补防 / 补充调查 / 服务评估 |

事件 payload 最少应包含：

```text
1. planId
2. taskId
3. taskSubtype
4. executionId
5. executionRecordId
6. resultPayload
```

### 4.6 TaskIntent 与 ReviewRequest 生成

目标：

```text
把运行期建议先固化成可审核对象，而不是直接生成正式任务。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| R1 | 实现 `TaskIntentService.createProposal` | 结构化建议创建 |
| R2 | 实现 `ReviewRequestService.createForTaskIntent` | 审核事项创建 |
| R3 | 统一 no_action 分支持久化方式 | `TaskIntent(no_action)` |
| R4 | 补齐 `decisionPayload.contextRefs` 读写 | 审核上下文引用 |

`TaskIntent.ruleResult` 至少要能承载：

```text
1. algorithmCode
2. branchType
3. proposedTask
4. proposedPlan
5. parentTaskId
6. sourceExecutionId
7. sourceExecutionRecordId
8. inputExecutionRecordIds
```

### 4.7 审核通过后的正式任务创建

目标：

```text
人工审核通过后，回到编排器，生成正式 FarmingTask，并为其创建 OperationPlan。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| A1 | 定义 `ReviewRequestResolved` 事件结构 | 审核结果事件 |
| A2 | 实现 `ReviewRequestResolvedHandler` | 审核结论分流 |
| A3 | 支持 approve / reject / adjust / no_action | 不同审核结论处理 |
| A4 | 实现 `FarmingTaskService.createFromTaskIntent` | 正式任务创建 |
| A5 | 实现 `OperationPlanService.createForApprovedTask` | 正式方案创建 |
| A6 | 审核通过后关闭 `TaskIntent`，回填 `convertedTaskId` | 完整追溯链 |

审核后生成的正式任务至少覆盖：

```text
1. 土壤封闭除草
2. 茎叶除草
3. 补防
4. 药害缓解
```

药害缓解任务 subtype：

```text
plant_protection.injury_mitigation
```

### 4.8 执行与执行记录

目标：

```text
让正式任务可以进入 Execution Module，并能沉淀调查结果和执行结果。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| E1 | 实现调查任务执行创建 | `Execution` + `ExecutionRecord` |
| E2 | 实现正式作业任务执行创建 | `Execution` + `ExecutionRecord` |
| E3 | 接入 HW 回调或 mock 回调 | `ExecutionStatusUpdated` |
| E4 | 调查记录与作业记录区分 `recordType` | `survey_result` / `result` |
| E5 | 作业完成后生成 `Feedback` | 闭环后续入口 |

注意：

```text
1. Execution Module 只消费 FarmingTask + OperationPlan。
2. Feedback 不直接生 FarmingTask，仍需回到 Plan Orchestrator。
```

### 4.9 杂草全链路 API

目标：

```text
提供前后端联调所需的最小 API，而不是一次做完全部管理端接口。
```

优先接口：

| 类型 | 建议接口 |
|---|---|
| 计划查询 | `GET /planting-plans/{id}` |
| CalendarItem 查询 | `GET /planting-plans/{id}/calendar-items` |
| Task 查询 | `GET /planting-plans/{id}/tasks` |
| Review 查询 | `GET /planting-plans/{id}/review-requests` |
| 调查结果录入 | `POST /tasks/{id}/survey-results` |
| 审核处理 | `POST /review-requests/{id}/resolve` |
| 执行回调 | `POST /executions/{id}/status-callback` |

联调优先级：

```text
1. 先能查看到期调查任务。
2. 再能录入调查结果并生成 TaskIntent / ReviewRequest。
3. 再能审核通过并生成正式防治任务。
4. 最后补执行与药后链路。
```

### 4.10 测试、样例数据与可视化验证

目标：

```text
让整条样板链路可以被本地重复验证。
```

任务：

| 编号 | 任务 | 输出 |
|---|---|---|
| T1 | 准备最小种植计划 seed 数据 | 单 plan 场景 |
| T2 | 准备药前调查结果样例 | 触发 weed_treatment_diagnosis |
| T3 | 准备安全性调查结果样例 | 触发 injury_mitigation_diagnosis |
| T4 | 准备防效兼安全性调查结果样例 | 触发 additional_treatment_diagnosis |
| T5 | 为关键 Handler 补单测 | 编排主分支验证 |
| T6 | 为全链路补最小集成测试 | 单 plan 走通主闭环 |

## 5. 按业务环节拆分的交付顺序

### M1 工程底座

```text
1. FastAPI + SQLAlchemy + Alembic 骨架。
2. 跑通 001~006 migration。
3. 建好核心 ORM 和 Repository。
```

### M2 调查日期与调查任务

```text
1. SurveyDateRecommendationJob。
2. 药前调查 / 药后调查 / 补充调查 / 服务评估 CalendarItem。
3. TaskDueCheckJob 生成调查 FarmingTask。
```

### M3 调查结果到待审核建议

```text
1. SurveyResultRecorded 事件。
2. weed_treatment_diagnosis / injury_mitigation_diagnosis / additional_treatment_diagnosis 接入。
3. TaskIntent / ReviewRequest / no_action 分支落库。
```

### M4 审核通过到正式任务

```text
1. ReviewRequestResolved 事件。
2. 审核通过后创建 FarmingTask。
3. 为正式任务创建 OperationPlan。
4. 回填 convertedTaskId 和 traceability 字段。
```

### M5 作业执行与药后链路

```text
1. 茎叶除草执行与反馈。
2. 药后调查日期推荐。
3. 安全性调查与药害缓解。
4. 防效兼安全性调查与补防。
5. 补充调查 / 服务效果评估日期生成。
```

## 6. 与 migration 的对应关系

| migration | 后端实现关注点 |
|---|---|
| `001_create_base_reference_tables.sql` | 基础主数据与用户 |
| `002_create_plan_and_stage_tables.sql` | `PlantingPlan`、`EventRecord`、阶段上下文 |
| `003_create_task_and_review_tables.sql` | `CalendarItem`、`TaskIntent`、`ReviewRequest`、`FarmingTask`、`OperationPlan` |
| `004_create_execution_tables.sql` | `Execution`、`ExecutionRecord` |
| `005_create_feedback_and_notification_tables.sql` | `Feedback`、`SystemNotification` |
| `006_add_traceability_fks_and_indexes.sql` | `parentTaskId`、`sourceExecutionId`、`sourceExecutionRecordId`、`convertedTaskId` 等追溯关系 |

## 7. 建议的并行分工

| 方向 | 主要内容 |
|---|---|
| 后端 owner | 工程骨架、ORM、Repository、Alembic、基础 API |
| 植保 owner | 杂草接口 adapter、入参组装、结果映射、业务分支校验 |
| 编排 owner | Handler、Policy、TaskIntent / ReviewRequest / FarmingTask 生成链 |
| 联调 owner | 样例数据、接口联调、主链路验证 |

并行原则：

```text
1. 先冻结模型和 migration，再并行写模型层与 adapter 层。
2. Handler 与 API 可以并行，但都依赖统一 Repository 和 Service 边界。
3. 运行期建议映射规则必须由同一 owner 统一维护，避免在多个 handler 中重复分支。
```

## 8. 最小完成定义

满足以下条件，可认为“P2 杂草后端样板链路”完成：

```text
1. 单个 PlantingPlan 能自动生成药前调查 CalendarItem。
2. CalendarItem 到期后能生成调查 FarmingTask。
3. 调查结果录入后能触发对应杂草诊断接口。
4. 诊断结果能正确落到 CalendarItem 或 TaskIntent / ReviewRequest。
5. 人工审核通过后能生成正式 FarmingTask，并为其创建 OperationPlan。
6. 茎叶除草完成后能继续进入药后调查日期推荐。
7. 安全性调查和防效兼安全性调查都能触发后续分支。
8. 补防、药害缓解、补充调查、服务效果评估日期都能按规则落库。
9. 全链路追溯字段可用，能从派生任务回查 parentTaskId 和 sourceExecutionRecordId。
```

## 9. 当前已知延后项

```text
1. DeviceCommand 与真实硬件下发。
2. InventoryItem / InventoryTransaction。
3. workflowKey / workflowStepKey / generalFlowKey / chainKey 落库。
4. 完整 stageCode 枚举。
5. 非杂草链路的共性抽象进一步沉淀。
```
