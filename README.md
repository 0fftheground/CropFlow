# CropFlow

CropFlow 是一个面向作物种植计划的 Plan-level MVP 系统，用于支持种植计划创建、农事任务生成、运行期事件触发、作业方案生成、执行反馈和人工复核闭环。

## 当前阶段

当前项目处于系统设计进入数据结构设计前的准备阶段。

MVP 范围聚焦在：

```text
单个 PlantingPlan 内部的编排与执行闭环
```

暂不覆盖：

```text
多农场、多计划全局调度
跨计划设备资源排程
复杂多级审批
独立 Recommendation 管理
```

## 核心主线

```text
PlantingPlan
  ↓
CropStageState / CropThermalTimeState
  ↓
CalendarItem / TaskGenerationPlan
  ↓
TaskIntent / FarmingTask
  ↓
OperationPlan
  ↓
Execution
  ↓
Evaluation / Feedback
  ↓
ReviewRequest
  ↓
后续任务或方案调整
```

## 关键设计原则

```text
1. MVP 先做 Plan-level orchestration。
2. CalendarItem 是预备农事项，不是正式任务。
3. TaskIntent 是运行期事件触发后的任务意图。
4. FarmingTask 是正式任务，是执行入口。
5. OperationPlan 是具体作业方案 / 处方方案。
6. Execution Module 只消费 FarmingTask + OperationPlan。
7. Feedback 不直接生成任务，必须回到 Plan Orchestrator。
8. ReviewRequestResolved 必须回到 Plan Orchestrator。
9. MVP 阶段不单独维护 Recommendation Entity。
10. 外部执行系统不放在系统输入里，应单独建模。
```

## 文档目录

```text
docs/
├── architecture.md
├── system-function.md
├── domain-model.md
├── modules.md
├── events.md
├── glossary.md
├── overall-runtime-flow.md
├── review-reading-order.md
├── flows/
│   ├── plan-creation-initialization.md
│   ├── runtime-event-task-update.md
│   └── task-execution-feedback.md
└── decisions/
    ├── 001-plan-level-mvp.md
    ├── 002-remove-recommendation-entity.md
    ├── 003-taskintent-before-farmingtask.md
    ├── 004-feedback-back-to-plan-orchestrator.md
    └── 005-external-execution-system-boundary.md
```

## 建议阅读顺序

先读：

```text
docs/system-function.md
docs/overall-runtime-flow.md
docs/architecture.md
docs/modules.md
docs/domain-model.md
```

然后再读：

```text
docs/events.md
docs/flows/
docs/decisions/
```

## 后续开发建议

下一步建议进入数据结构设计阶段，优先设计：

```text
PlantingPlan
CropStageState
CalendarItem
TaskGenerationPlan
TaskIntent
FarmingTask
OperationPlan
Execution
Feedback
ReviewRequest
```
