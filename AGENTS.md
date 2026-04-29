# AGENTS.md

本文件用于指导 Codex 或其他 AI 编程助手开发 CropFlow 项目。

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
```

## 模块边界

```text
Plan Module：计划基础操作。
Plan Orchestrator：计划级总编排。
Stage Orchestrator：生育期预测、积温、生育期状态。
Runtime Rule Engine：运行期规则判断。
Task Module：CalendarItem / TaskGenerationPlan / TaskIntent / FarmingTask / OperationPlan。
Execution Module：Execution / ExecutionRecord / DeviceCommand。
Evaluation & Feedback Module：Evaluation / Feedback。
Review Module：ReviewRequest / SystemNotification。
Event Module：事件接入、标准化、记录。
Background Job Center：周期性发现变化，生成 Input Event。
```

## 命名规则

建议沿用以下概念名，不要随意替换：

```text
PlantingPlan
CropStageState
CropThermalTimeState
StagePredictionSnapshot
CalendarItem
TaskGenerationPlan
TaskIntent
FarmingTask
OperationPlan
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
ExecutionModule
```

## 文档优先级

开发前优先阅读：

```text
docs/system-function.md
docs/architecture.md
docs/domain-model.md
docs/modules.md
docs/events.md
```

涉及流程时阅读：

```text
docs/flows/
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

## 当前技术栈

尚未确定。

在用户明确技术栈前，不要擅自生成完整工程框架。可以先补充文档、数据结构草案或伪代码。
