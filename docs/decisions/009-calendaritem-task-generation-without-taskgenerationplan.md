# ADR 009：MVP 第一版不引入 TaskGenerationPlan

## 决策

MVP 第一版不把 `TaskGenerationPlan` 作为核心对象或独立表。

正式任务生成逻辑由：

```text
TaskDueCheckJob + TaskGenerationService + CalendarItem
```

完成。

## 背景

在当前阶段，正式任务生成的核心问题主要是：

```text
1. CalendarItem 是否到达生成窗口。
2. 是否满足幂等、阻断和失效条件。
3. 生成后的 FarmingTask 如何回到既有编排边界。
```

如果现在提前引入 `TaskGenerationPlan`，容易把本来可以直接由 `CalendarItem` 和后台任务承接的生成逻辑，再包装成一层语义重复对象。

## 结果

当前采用：

```text
1. SurveyDateRecommendationJob、AgronomyCalendarRefreshJob 等后台任务维护 CalendarItem。
2. TaskDueCheckJob 周期性检查 CalendarItem 是否进入正式任务生成窗口。
3. TaskGenerationService 根据 CalendarItem、幂等键和阻断条件生成 FarmingTask。
4. 如后续出现更复杂的多次计划历史、跳过原因、重试策略，再评估是否重新引入 TaskGenerationPlan。
```

## 非目标

当前 ADR 不要求本阶段完成：

```text
1. 独立的 TaskGenerationPlan 表。
2. 通用任务生成工作流引擎。
3. 生成计划历史的完整审计模型。
```
