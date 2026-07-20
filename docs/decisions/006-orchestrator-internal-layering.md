# ADR 006：Orchestrator 内部采用 Handler / Policy / Strategy 分层

## 决策

`Plan Orchestrator` 和相关编排组件内部可以采用：

```text
Handler Registry
Event Handler
Policy
Task Type Strategy
Domain Service
```

来组织实现。

这些结构是实现层分工，不是新的顶层业务模块，也不改变当前模块边界。

## 背景

CropFlow MVP 聚焦单个 `PlantingPlan` 内部闭环。随着事件类型、任务类型和反馈处理增加，如果所有判断都写入 `Plan Orchestrator`，它容易变成超级服务类：

```text
1. 所有事件判断集中在一个类
2. 所有任务生成逻辑集中在一个类
3. 所有反馈处理集中在一个类
4. 所有农事类型差异通过大量 if-else 表达
```

这会削弱模块边界，也会让测试和多人协作变困难。

## 结果

建议实现时保持：

```text
1. Orchestrator 负责接收事件、识别流程、协调模块、提交结果、发布后续事件。
2. Handler 负责单类事件的处理流程。
3. Policy 负责是否需要生成、更新、失效、复核等业务判断。
4. Strategy 负责不同农事类型的差异。
5. Domain Service 负责具体领域动作。
```

同时保持既有边界：

```text
1. Task Module 不直接处理外部硬件执行。
2. Execution Module 不创建 FarmingTask。
3. Feedback 必须回到 Plan Orchestrator。
4. ReviewRequestResolved 必须回到 Plan Orchestrator。
5. Stage Orchestrator 不直接生成 FarmingTask 或 OperationPlan。
```

## 非目标

MVP 阶段不要求实现完整框架化插件系统，也不要求把所有 Policy / Strategy 都提前抽象完。

可以先按关键事件和高风险任务类型做最小拆分，再随着流程扩展补充。
