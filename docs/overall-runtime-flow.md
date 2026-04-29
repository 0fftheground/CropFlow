# Plan-level MVP 总运行流程（v2：移除 Recommendation）

---

# 1. MVP 总目标

在单个 `PlantingPlan` 内部跑通：

```text
计划创建
生育期初始化与更新
预备农事项生成
正式任务生成
作业方案生成
任务执行
执行反馈
人工复核
后续任务或方案调整
计划完成与归档
```

MVP 阶段不做多农场、多计划全局调度。

---

# 2. 总体主线

```text
PlantingPlan
  ↓
Stage 初始化
  ↓
CalendarItem
  ↓
FarmingTask
  ↓
OperationPlan
  ↓
Execution
  ↓
Evaluation / Feedback
  ↓
ReviewRequest
  ↓
FarmingTask / OperationPlan 调整
  ↓
Plan Completed / Archived
```

---

# 3. 三条核心流程

## 3.1 计划创建与初始化

```text
创建 PlantingPlan
  ↓
初始化生育期
  ↓
调用农事日历接口
  ↓
生成 CalendarItem
  ↓
生成近期 FarmingTask
```

## 3.2 运行期事件触发

```text
WeatherUpdated / FieldConditionReported / SensorDataUpdated
  ↓
Event Module
  ↓
Plan Orchestrator
  ↓
Stage Orchestrator / Runtime Rule Engine / Task Module
  ↓
TaskIntent / FarmingTask / OperationPlan
```

## 3.3 任务执行与反馈

```text
FarmingTask + OperationPlan
  ↓
Execution Module
  ↓
ExecutionRecord
  ↓
Evaluation
  ↓
Feedback
  ↓
ReviewRequest
  ↓
人工复核
  ↓
更新任务或方案
```

---

# 4. Plan 生命周期

```text
created
initializing
active
completed
archived
failed
```

---

# 5. 核心对象

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
```

---

# 6. MVP 阶段移除 Recommendation

## 调整结论

```text
MVP 阶段不单独维护 Recommendation Entity。
```

## 原因

```text
1. 容易和 TaskIntent 混淆
2. 容易和 OperationPlan 混淆
3. 当前闭环不依赖独立建议对象
4. 具体处方、剂量、参数应属于 OperationPlan
```

## 替代方式

```text
TaskIntent：保存触发原因、规则判断、建议生成任务类型
FarmingTask：保存任务生成原因和任务说明
OperationPlan：保存方案依据、处方图、剂量、参数
SystemNotification：提醒用户查看或处理
```

---

# 7. 模块职责主线

```text
Plan Module：计划基础操作
Plan Orchestrator：计划级总编排
Stage Orchestrator：生育期状态维护
Runtime Rule Engine：运行期规则判断
Task Module：CalendarItem / TaskIntent / FarmingTask / OperationPlan
Execution Module：Execution / ExecutionRecord / DeviceCommand
Evaluation & Feedback Module：Evaluation / Feedback
Review Module：ReviewRequest / 人工复核结论
Event Module：事件接入和标准化
Background Job Center：周期性发现变化
```

---

# 8. 外部执行系统

外部执行系统单独作为外部系统存在，不放在“系统输入”中。

```text
Execution Module → HW
HW → Execution Module
ExecutionStatusPollingJob → HW
```

---

# 9. 当前结论

```text
1. MVP 先做 Plan-level orchestration。
2. CalendarItem 是预备农事项。
3. FarmingTask 是正式任务。
4. TaskIntent 是运行期触发后的任务意图。
5. OperationPlan 是具体作业方案 / 处方方案。
6. Execution Module 只消费 FarmingTask + OperationPlan。
7. Feedback 回到 Plan Orchestrator。
8. ReviewRequestResolved 回到 Plan Orchestrator。
9. 不再维护独立 Recommendation。
```
