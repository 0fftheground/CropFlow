# Plan-level MVP 模块职责说明（v2：移除 Recommendation）

> 本版调整：MVP 阶段不再单独维护 `Recommendation`。  
> Task Module 负责 `TaskIntent / FarmingTask / OperationPlan`，农艺建议和推荐依据作为这些对象的说明信息存在。

---

# 1. 模块总览

```text
[Module] Plan Module
[Orchestrator] Plan Orchestrator
[Orchestrator] Stage Orchestrator
[Module] Runtime Rule Engine
[Module] Task Module
[Module] Execution Module
[Module] Evaluation & Feedback Module
[Module] Review Module
[Module] Event Module
[Job Center] Background Job Center
```

---

# 2. Plan Module

## 职责

```text
1. 创建 PlantingPlan
2. 更新 PlantingPlan 基础信息
3. 完成计划
4. 归档计划
5. 产生 PlanCreated / PlanKeyInfoChanged / PlanCompleted / PlanArchived 等事件
```

## 不负责

```text
1. 不直接生成农事项
2. 不直接生成正式任务
3. 不直接调用生育期预测接口
4. 不直接调用农事日历接口
5. 不直接控制设备
```

---

# 3. Plan Orchestrator

## 职责

计划级总编排中心。

```text
1. 接收计划级事件和运行期事件
2. 决定调用 Stage Orchestrator / Runtime Rule Engine / Task Module / Review Module
3. 维护一个 PlantingPlan 内部的运行主线
4. 处理 FeedbackGenerated 后的后续动作
5. 处理 ReviewRequestResolved 后的任务或方案调整
```

## 不负责

```text
1. 不保存具体业务对象
2. 不直接调用农事日历接口
3. 不直接调用灌溉/施肥/植保算法接口
4. 不直接执行设备指令
```

## 内部实现建议

`Plan Orchestrator` 可以内部拆成：

```text
Handler Registry
Event Handler
Policy
Task Type Strategy
Domain Service
```

这些是实现层分工，不是新的顶层业务模块，也不改变现有模块边界。

建议保持：

```text
1. Orchestrator 负责接收事件、识别流程、协调模块。
2. Handler 负责单类事件的处理过程。
3. Policy 负责是否需要生成、更新、失效、复核等业务判断。
4. Strategy 负责灌溉、施肥、植保、巡田等农事类型差异。
5. Service 负责具体领域动作和状态维护。
```

不建议把复杂规则、任务字段组装、算法接口选择和农事类型分支全部写在 `Plan Orchestrator` 中。

---

# 4. Stage Orchestrator

## 职责

```text
1. 调用生育期预测接口
2. 维护 CropStageState
3. 维护 CropThermalTimeState
4. 保存 StagePredictionSnapshot
5. 处理真实生育期录入
6. 判断生育期变化并产生 StageChanged
```

## 输入

```text
1. PlanCreated
2. WeatherUpdated
3. ActualStageRecorded
4. PlanKeyInfoChanged
```

## 输出

```text
1. CropStageState
2. CropThermalTimeState
3. StagePredictionSnapshot
4. StageChanged
5. ActualStageApplied
```

---

# 5. Runtime Rule Engine

## 职责

运行期规则判断模块。

```text
1. 接收 Plan Orchestrator 转来的运行期事件
2. 根据规则判断是否需要生成 TaskIntent
3. 判断是否 NeedMoreInfo
4. 判断是否 NoAction
5. 返回规则判断结果
```

## 不负责

```text
1. 不直接创建 FarmingTask
2. 不直接创建 OperationPlan
3. 不直接控制设备
4. 不直接维护任务状态
```

`NeedMoreInfo` 和 `NoAction` 是规则判断结果，应由 `Task Module` 以 `TaskIntent` 状态或规则判断记录持久化，不作为独立核心对象引入。

## 典型输入

```text
FieldConditionReported
SensorDataUpdated
DeviceDataUpdated
FeedbackGenerated 后的派生判断
```

---

# 6. Task Module

## 定位

农事项、任务意图、正式任务、作业方案的管理模块。

## 职责

```text
1. 调用农事日历接口生成 CalendarItem
2. 维护 CalendarItem
3. 维护 TaskGenerationPlan
4. 根据任务生成窗口生成 FarmingTask
5. 保存 TaskIntent
6. 将确认后的 TaskIntent 转为 FarmingTask
7. 调用灌溉/施肥/植保等算法接口生成 OperationPlan
8. 维护 OperationPlan
9. 维护任务状态
10. 生成必要的 SystemNotification
```

## 不再负责

```text
1. 不再维护独立 Recommendation Entity
2. 不把农艺建议作为独立对象流转
```

## 内部实现建议

`Task Module` 对外仍是一个模块，内部可以按对象和生命周期拆成服务：

```text
CalendarItemService
TaskGenerationPlanService
TaskIntentService
FarmingTaskService
OperationPlanService
TaskLifecycleService
TaskConflictService
```

这些服务只处理任务与方案领域动作，不反向调用 `Handler`，也不直接控制外部硬件执行。

## 农艺建议信息放置规则

| 内容 | 放置位置 |
|---|---|
| 运行期触发原因 | TaskIntent |
| 规则判断结果 | TaskIntent |
| 建议生成任务类型 | TaskIntent |
| 正式任务说明 | FarmingTask |
| 具体处方、剂量、参数 | OperationPlan |
| 方案依据 | OperationPlan |
| 用户提醒 | SystemNotification |

---

# 7. Execution Module

## 职责

```text
1. 接收 FarmingTask
2. 读取 OperationPlan
3. 创建 Execution
4. 创建 ExecutionRecord
5. 在设备执行场景下创建 DeviceCommand
6. 向外部执行系统下发任务或指令
7. 接收外部执行系统主动回调
8. 同步执行状态
```

## 只消费

```text
FarmingTask + OperationPlan
```

## 不消费

```text
Recommendation
```

因为 MVP 阶段已经移除该独立对象。

---

# 8. Evaluation & Feedback Module

## 职责

```text
1. 根据 ExecutionRecord 和 OperationPlan 评价执行结果
2. 生成 Evaluation
3. 生成 Feedback
4. 产生 FeedbackGenerated 事件
```

## 不负责

```text
1. 不直接生成 FarmingTask
2. 不直接更新后续任务
3. 不直接创建 TaskIntent
```

这些动作应交回 `Plan Orchestrator` 统一判断。

---

# 9. Review Module

## 职责

```text
1. 创建 ReviewRequest
2. 维护 ReviewRequest 状态
3. 记录人工复核结论
4. 生成 SystemNotification
5. 产生 ReviewRequestResolved 事件
```

## 不负责

```text
1. 不直接执行任务
2. 不直接调用算法接口
3. 不直接修改生育期状态
```

复核结论回到 `Plan Orchestrator` 后，再协调其他模块执行后续动作。

---

# 10. Event Module

## 职责

```text
1. 接收 Input Event
2. 标准化事件格式
3. 记录事件
4. 转发给 Plan Orchestrator
```

## 不负责

```text
1. 不做复杂业务判断
2. 不直接生成任务
3. 不直接调用算法接口
4. 不直接控制设备
```

---

# 11. Background Job Center

## 职责

后台任务调度中心。

```text
1. 定期检查气象变化
2. 定期同步设备/传感器数据
3. 定期检查任务到期/逾期
4. 定期轮询外部执行系统状态
5. 产生 Input Event
```

## 典型 Job

```text
DailyWeatherCheckJob
DeviceDataSyncJob
TaskDueCheckJob
ExecutionStatusPollingJob
```

## 注意

不保留：

```text
HW → Background Job Center
```

应改为：

```text
ExecutionStatusPollingJob → HW
```

表示后台任务主动查询外部执行系统。

---

# 12. 外部执行系统关系

```text
Execution Module → HW
HW → Execution Module
ExecutionStatusPollingJob → HW
```

含义：

```text
1. Execution Module 负责下发任务或指令
2. HW 主动回调进入 Execution Module
3. 如果 HW 不主动回调，由 ExecutionStatusPollingJob 轮询兜底
```

---

# 13. 当前模块边界结论

```text
1. Plan Module 负责计划基础操作。
2. Plan Orchestrator 负责计划级总编排。
3. Stage Orchestrator 负责生育期状态。
4. Runtime Rule Engine 负责运行期规则判断。
5. Task Module 负责 CalendarItem / TaskGenerationPlan / TaskIntent / FarmingTask / OperationPlan。
6. MVP 阶段不单独维护 Recommendation。
7. Execution Module 只消费 FarmingTask + OperationPlan。
8. Evaluation & Feedback Module 负责评价和反馈，不直接生成任务。
9. Review Module 负责人工复核事项维护。
10. Event Module 只做事件接入、标准化和记录。
11. Background Job Center 负责周期性发现变化并产生 Input Event。
```
