# ADR 011：病虫害防治复核阶段只审核 theoryPlan

## 决策

对 `plant_protection.disease_pest_control`，人工复核阶段只审核：

```text
proposedPlan.theoryPlan
```

而不是直接审核或覆盖最终 `controlPlan`。

## 背景

病虫害防治建议需要同时处理：

```text
1. 理论防治轮次与目标对象。
2. 天气修正后的实际作业窗口。
3. 合并常规调查和突发调查后的建议收口。
4. 前端人工增删轮次、改单轮 targets / theory_window / prescription。
```

如果前端直接改最终 `controlPlan`，容易把理论方案、天气修正结果和正式任务派生结果混在一起，导致复核口径难以稳定。

## 结果

当前行为统一为：

```text
1. /api/review-requests/{reviewRequestId}/resolve 对病虫害防治只接收 decision_payload.proposedPlan.theoryPlan。
2. theoryPlan.rounds 按完整列表提交；数量变化表示新增 / 删除轮次。
3. 后端在 ReviewRequestResolved 后根据 theoryPlan 重算 adjustedPlan、operationWindow 和正式 controlPlan。
4. disease_pest_control 的正式 FarmingTask 和 OperationPlan 由 Plan Orchestrator 根据审核后的 theoryPlan 派生。
```

## 非目标

当前 ADR 不允许：

```text
1. 前端直接提交 proposedPlan.controlPlan 覆盖正式方案。
2. ReviewRequestResolved 绕过编排器直接落正式任务。
3. 把天气修正后的最终窗口当成前端人工维护的事实源。
```
