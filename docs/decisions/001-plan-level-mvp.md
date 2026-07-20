# ADR 001：MVP 先做 Plan-level Orchestration

## 决策

CropFlow MVP 阶段只做单个 PlantingPlan 内部的编排与执行闭环。

## 背景

完整系统未来可能需要支持多农场、多计划、多设备、多作业资源的全局调度。但当前阶段如果同时设计全局调度，会显著增加复杂度。

## 结果

当前 MVP 聚焦：

```text
PlantingPlan → CalendarItem → FarmingTask → OperationPlan → Execution → Feedback → ReviewRequest
```

暂不处理：

```text
跨计划任务冲突
跨农场资源调度
多计划设备排程
```
