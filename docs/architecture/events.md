# Plan-level MVP 事件系统设计（v4：移除 Recommendation）

---

# 1. 事件系统定位

事件系统负责把外部变化、用户操作、后台检查结果转化为系统可以处理的标准事件。

事件系统不直接做复杂业务决策。

---

# 2. 事件分类

## 2.1 Input Event

外部输入事件或后台任务发现的变化。

示例：

```text
WeatherUpdated
SensorDataUpdated
DeviceDataUpdated
FieldConditionReported
ActualStageRecorded
ExecutionStatusUpdated
TaskDueCheckTriggered
CalendarItemUpdated
InventoryStockInRecorded
```

## 2.2 Domain Event

系统内部业务状态变化事件。

示例：

```text
PlanCreated
PlanKeyInfoChanged
StageChanged
ActualStageApplied
TaskIntentCreated
FarmingTaskCreated
OperationPlanUpdated
FeedbackGenerated
ReviewRequestCreated
ReviewRequestResolved
InventoryTransactionCreated
```

---

# 3. Event Module 职责

```text
1. 接收 Input Event
2. 标准化事件格式
3. 记录事件日志
4. 转发给 Plan Orchestrator
```

不负责：

```text
1. 不直接生成 FarmingTask
2. 不直接生成 OperationPlan
3. 不直接控制设备
4. 不直接执行农艺规则
```

---

# 4. Background Job Center 职责

```text
1. 定期检查气象数据
2. 定期同步传感器/设备数据
3. 定期检查任务到期情况
4. 定期轮询外部执行系统状态
5. 定期调用调查日期推荐算法，新建或修改调查类 CalendarItem
```

典型关系：

```text
DailyWeatherCheckJob → WeatherUpdated
StagePredictionRefreshJob → StageChanged
AgronomyCalendarRefreshJob → CalendarItemUpdated
DeviceDataSyncJob → SensorDataUpdated / DeviceDataUpdated
TaskDueCheckJob → TaskDueCheckTriggered
ExecutionStatusPollingJob → ExecutionStatusUpdated
SurveyDateRecommendationJob → CalendarItemUpdated
```

注意：

```text
不使用 HW → Background Job Center
```

应表达为：

```text
ExecutionStatusPollingJob → HW
```

---

# 5. 关键事件说明

## 5.1 WeatherUpdated

来源：

```text
DailyWeatherCheckJob
```

处理：

```text
Event Module
  ↓
Plan Orchestrator
  ↓
Stage Orchestrator
```

可能结果：

```text
1. 更新 CropThermalTimeState
2. 更新 StagePredictionSnapshot
3. 产生 StageChanged
4. 触发后续 CalendarItem / FarmingTask 更新
```

---

## 5.2 ActualStageRecorded

来源：

```text
用户录入真实生育期
```

处理：

```text
Event Module
  ↓
Plan Orchestrator
  ↓
Stage Orchestrator
```

可能结果：

```text
1. 修正 CropStageState
2. 保存 StagePredictionSnapshot
3. 产生 ActualStageApplied
4. 影响后续任务生成或更新
```

---

## 5.3 FieldConditionReported

来源：

```text
人工巡田
设备上报
传感器数据解释结果
第三方平台
```

示例：

```text
缺水
病害风险
苗情异常
积水
倒伏
虫害
```

处理：

```text
Event Module
  ↓
Plan Orchestrator
  ↓
Runtime Rule Engine
  ↓
TaskIntent / NeedMoreInfo / NoAction
```

MVP 原则：

```text
不直接生成 FarmingTask。
优先生成 TaskIntent 或 ReviewRequest，让人工判断。
NeedMoreInfo / NoAction 作为规则结果或 TaskIntent 状态保存，不作为独立核心对象。
```

---

## 5.4 ExecutionStatusUpdated

来源有两种：

```text
1. HW 主动回调给 Execution Module
2. ExecutionStatusPollingJob 主动轮询 HW 后生成事件
```

处理：

```text
Execution Module / Event Module
  ↓
Evaluation & Feedback Module
  ↓
FeedbackGenerated
```

边界说明：

```text
Execution / ExecutionRecord / DeviceCommand 的状态维护属于 Execution Module。
如果 ExecutionStatusUpdated 经过 Plan Orchestrator 或对应 Handler，Handler 只负责流程编排和委托 Execution Module，不直接维护执行对象。
```

---

## 5.5 FeedbackGenerated

来源：

```text
Evaluation & Feedback Module
```

处理：

```text
FeedbackGenerated
  ↓
Plan Orchestrator
  ↓
Review Module
  ↓
ReviewRequest
```

原则：

```text
Feedback 不直接新增任务。
是否生成补救任务、调整任务或更新 OperationPlan，应由 Plan Orchestrator 编排。
```

---

## 5.6 ReviewRequestResolved

来源：

```text
人工复核完成
```

处理：

```text
ReviewRequestResolved
  ↓
Plan Orchestrator
  ↓
Task Module / Stage Orchestrator / Execution Module
```

可能结果：

```text
1. 生成 FarmingTask
2. 更新 FarmingTask
3. 更新 OperationPlan
4. 标记 NoAction
5. 要求补充信息
```

---

## 5.7 InventoryStockInRecorded / InventoryTransactionCreated

来源：

```text
药剂入库 FarmingTask
肥料入库 FarmingTask
人工物料信息录入
```

处理：

```text
Event Module
  ↓
Plan Orchestrator
  ↓
Material & Inventory Module
  ↓
InventoryItem / InventoryTransaction
```

原则：

```text
1. 入库需要维护独立库存表。
2. InventoryStockInRecorded 是输入事件，表示入库信息已录入。
3. InventoryTransactionCreated 是库存流水创建后的领域事件。
4. 库存事件不直接生成施肥或打药任务。
5. 施肥、打药是否扣减库存后续在执行集成阶段确认。
```

---

# 6. 已移除的 Recommendation 相关事件

MVP 阶段不再使用独立：

```text
RecommendationUpdated
RecommendationRefreshTriggered
```

替代方式：

| 原事件含义 | 当前替代 |
|---|---|
| 推荐内容更新 | OperationPlanUpdated / TaskIntentUpdated |
| 推荐刷新检查 | TaskDueCheckTriggered / FieldConditionReported / PlanKeyInfoChanged |
| 推荐结果展示 | TaskIntent / FarmingTask / OperationPlan + SystemNotification |

---

# 7. 当前事件流转原则

```text
1. Event Module 只做接入和标准化。
2. Plan Orchestrator 负责事件后的业务编排。
3. Stage Orchestrator 负责生育期相关事件。
4. Runtime Rule Engine 负责田间条件类规则判断。
5. Task Module 负责 TaskIntent / FarmingTask / OperationPlan。
6. Execution Module 负责执行状态。
7. Material & Inventory Module 负责库存主数据和库存流水。
8. FeedbackGenerated 回到 Plan Orchestrator。
9. ReviewRequestResolved 回到 Plan Orchestrator。
10. MVP 阶段不再产生独立 Recommendation 事件。
```
