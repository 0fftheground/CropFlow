# ADR 002：MVP 阶段移除独立 Recommendation Entity

## 决策

MVP 阶段不单独维护 Recommendation Entity。

## 背景

Recommendation 容易和 TaskIntent、OperationPlan、SystemNotification 混淆。

## 替代方案

```text
TaskIntent：保存触发原因、规则判断和建议生成任务类型。
FarmingTask：保存任务生成原因和任务说明。
OperationPlan：保存处方图、剂量、参数和方案依据。
SystemNotification：提醒用户查看或处理。
```

## 后续扩展

如果后续需要独立管理农艺建议流、建议版本、建议采纳率或多方案排序，可以重新引入 Recommendation。
