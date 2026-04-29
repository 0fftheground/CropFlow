# ADR 004：Feedback 必须回到 Plan Orchestrator

## 决策

Feedback 不直接生成任务，也不直接更新后续方案。FeedbackGenerated 必须回到 Plan Orchestrator。

## 背景

执行反馈是否会影响后续任务，需要结合计划状态、生育期、任务状态和人工复核结论判断。

## 结果

```text
Evaluation & Feedback Module
  ↓
FeedbackGenerated
  ↓
Plan Orchestrator
  ↓
Review Module / Task Module
```
