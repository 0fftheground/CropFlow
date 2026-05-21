# AGENTS.md

本文件用于指导 Codex 或其他 AI 编程助手开发 CropFlow 项目。

## Session 启动方式

新的 session 不应默认从头扫整个仓库。推荐按以下顺序恢复上下文：

```text
1. AGENTS.md
2. project-context/entrypoints.md
3. project-context/development-plan.md
4. project-context/current-memory.md
5. 当前 phase 对应文档
6. 与当前任务直接相关的 docs/ 或代码文件
```

原则：

```text
1. 稳定入口放在 project-context/ 和 docs/ 正式文档中。
2. current-memory 只记录当前 phase 的压缩状态，不重复维护完整 backlog。
3. 已完成且对后续无影响的历史讨论，不继续保留在 current-memory。
4. current-memory 只写结论、现状、阻塞和下一步，不写长推理过程。
```

推荐优先使用以下 skill：

```text
1. 开始新一天或恢复上下文时，优先使用 $cropflow-start-work。
2. 结束当天工作、更新 memory 或准备提交时，优先使用 $cropflow-wrap-up。
3. 如果只是普通代码实现，不必强制调用 skill；但只要涉及 session 恢复或扫尾，优先走 skill。
```

推荐触发方式：

```text
Use $cropflow-start-work to restore current CropFlow progress
Use $cropflow-wrap-up to summarize today, update memory, and prepare commit actions
```

## 项目背景

CropFlow 是一个作物种植计划的 Plan-level MVP 编排系统。系统围绕单个种植计划运行，支持：

```text
计划创建
生育期预测与更新
预备农事项生成
正式任务生成
运行期事件触发
作业方案生成
执行反馈
人工复核
后续任务或方案调整
```

## 当前 MVP 范围

只做：

```text
单个 PlantingPlan 内部的编排与执行闭环
```

暂不做：

```text
多农场多计划全局调度
跨计划设备资源排程
复杂审批流
独立 Recommendation Entity
完整规则后台配置系统
```

## 必须遵守的核心设计

```text
1. 不要引入独立 Recommendation Entity。
2. 农艺建议、推荐原因、方案依据分别放到 TaskIntent / FarmingTask / OperationPlan。
3. CalendarItem 是预备农事项，不是正式任务。
4. FarmingTask 是正式任务，是 Execution Module 的入口。
5. OperationPlan 是具体作业方案 / 处方方案。
6. Execution Module 只消费 FarmingTask + OperationPlan。
7. Feedback 不能直接生成 FarmingTask，必须回到 Plan Orchestrator。
8. ReviewRequestResolved 不能直接绕过编排器，必须回到 Plan Orchestrator。
9. 外部执行系统是独立外部系统，不属于系统输入。
10. HW 主动回调进入 Execution Module；轮询兜底由 ExecutionStatusPollingJob 查询 HW。
11. 药剂和肥料库存使用 InventoryItem / InventoryTransaction，不只放在 EventRecord。
12. MVP 第一版不把 TaskGenerationPlan 作为核心对象或独立表；任务生成由 TaskDueCheckJob / TaskGenerationService 根据 CalendarItem 完成。
```

## 模块边界

```text
Plan Module：计划基础操作。
Plan Orchestrator：计划级总编排。
Stage Orchestrator：生育期预测、积温、生育期状态。
Runtime Rule Engine：运行期规则判断。
Task Module：CalendarItem / TaskIntent / FarmingTask / OperationPlan。
Material & Inventory Module：InventoryItem / InventoryTransaction。
Execution Module：Execution / ExecutionRecord / DeviceCommand。
Evaluation & Feedback Module：Evaluation / Feedback。
Review Module：ReviewRequest / SystemNotification。
Event Module：事件接入、标准化、记录。
Background Job Center：周期性发现变化，生成 Input Event。
```

当前业务分工方向：

```text
农事日历 / 生育期
植保
灌溉
施肥
遥感监测
前端
```

## 命名规则

建议沿用以下概念名，不要随意替换：

```text
PlantingPlan
CropStageState
CropThermalTimeState
StagePredictionSnapshot
CalendarItem
TaskIntent
FarmingTask
OperationPlan
InventoryItem
InventoryTransaction
Execution
ExecutionRecord
DeviceCommand
Evaluation
Feedback
ReviewRequest
SystemNotification
PlanOrchestrator
StageOrchestrator
RuntimeRuleEngine
TaskModule
MaterialInventoryModule
ExecutionModule
```

## 文档优先级

开发前优先阅读：

```text
project-context/entrypoints.md
project-context/development-plan.md
project-context/current-memory.md
docs/README.md
docs/architecture/system-function.md
docs/architecture/architecture.md
docs/model/domain-model.md
docs/model/data-model.md
docs/model/data-model-validation.md
docs/workflow/task-workflow-matrix.md
docs/workflow/background-job-matrix.md
docs/planning/development-roadmap.md
docs/planning/team-work-division.md
docs/planning/agent-development-guidelines.md
docs/architecture/modules.md
docs/architecture/events.md
docs/architecture/orchestration-design.md
```

涉及流程时阅读：

```text
docs/workflow/flows/
```

涉及设计取舍时阅读：

```text
docs/decisions/
```

## 修改代码时的要求

每次修改后应尽量做到：

```text
1. 保持模块边界清楚。
2. 不把编排逻辑散落到 Entity 或 Repository 中。
3. 不让 Task Module 直接处理外部硬件执行。
4. 不让 Execution Module 反向创建业务任务。
5. 不让 Feedback 直接跳过 Plan Orchestrator。
6. 不新增与现有核心对象语义重复的对象。
7. 如新增核心对象或流程，先更新 docs/。
```

## 通用编码行为要求

这些要求用于减少常见 AI 编码错误。对很小的任务可以按实际情况简化，但不应违背项目核心设计。

### 1. 编码前先明确问题

```text
1. 不要隐藏不确定性。
2. 如果存在多种理解，先说明取舍。
3. 如果更简单的方案足够，应优先选择简单方案。
4. 如果需求关键点不清楚，应先指出不清楚的地方。
```

### 2. 优先保持简单

```text
1. 不做用户没有要求的功能。
2. 不为单次使用代码提前抽象。
3. 不引入没有明确需求的灵活性或配置项。
4. 不为不可能出现的场景堆叠错误处理。
5. 如果实现明显过度复杂，应先简化。
```

### 3. 修改保持外科手术式

```text
1. 只修改完成当前目标必须修改的内容。
2. 不顺手重构无关代码。
3. 不顺手调整无关格式、注释或命名。
4. 匹配现有风格，即使存在个人偏好的其他写法。
5. 发现无关死代码时可以说明，但不要擅自删除。
6. 只清理本次修改引入的未使用导入、变量、函数或文件。
```

### 4. 以可验证目标推进

```text
1. 修复 bug 时，优先明确如何复现和验证。
2. 新增校验时，优先明确有效和无效输入的检查方式。
3. 重构时，优先保证重构前后行为一致。
4. 多步骤任务应给出简短计划，并说明每步如何验证。
5. 修改完成后应尽量运行与变更范围匹配的检查。
```

## 当前技术栈

当前已确认的基础口径：

```text
后端：Python + FastAPI
数据库：PostgreSQL
部署：Docker
前端：由前端负责人确定，但需遵循统一 API contract
```

在正式进入 P2 实现前，仍应先确认当前任务依赖的契约是否已经在当前 phase 内冻结。
