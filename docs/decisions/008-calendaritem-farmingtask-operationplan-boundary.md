# ADR 008：CalendarItem、FarmingTask、OperationPlan 保持明确边界

## 决策

MVP 阶段明确保持以下对象边界：

```text
1. CalendarItem 是预备农事项，不是正式执行任务。
2. FarmingTask 是正式任务，是 Execution Module 的业务入口。
3. OperationPlan 是具体作业方案 / 处方方案，不替代 FarmingTask。
4. Execution Module 只消费 FarmingTask + OperationPlan。
```

## 背景

随着杂草、病虫害、灌溉、施肥等方向逐步接入，系统里很容易把“推荐事项”“待执行任务”“具体作业方案”混成一个对象，导致：

```text
1. CalendarItem 被误当成可执行任务。
2. OperationPlan 被误当成任务主对象。
3. Execution Module 反向耦合任务生成和业务判断。
4. 前端、后端和业务讨论时对象语义不断漂移。
```

## 结果

当前按以下方式落地：

```text
PlantingPlan
  ↓
CalendarItem
  ↓
TaskDueCheckJob / Plan Orchestrator
  ↓
FarmingTask
  ↓
OperationPlan
  ↓
Execution / ExecutionRecord
```

补充约束：

```text
1. CalendarItem 可以被更新、失效、跳过，但不直接进入执行。
2. FarmingTask 负责正式任务状态、执行入口和业务追溯。
3. OperationPlan 负责参数、处方图、作业窗口和方案依据。
4. ReviewRequestResolved 后如需落正式任务，仍回到 Plan Orchestrator 生成 FarmingTask / OperationPlan。
```
