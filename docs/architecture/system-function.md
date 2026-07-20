# Plan-level MVP 系统与功能说明（v2：移除 Recommendation）

---

# 1. 系统定位

本系统是一个围绕单个种植计划运行的农事任务编排与执行闭环系统。

它支持：

```text
创建种植计划
生成预备农事项
生成正式农事任务
响应运行期事件
生成作业方案
执行任务
记录执行结果
评价执行效果
触发人工复核
调整后续任务或方案
```

MVP 阶段重点不是多农场、多计划全局调度，而是先跑通单个 `PlantingPlan` 内部闭环。

---

# 2. 系统要解决的问题

```text
1. 种植计划创建后，需要自动生成整个种植季的预备农事项。
2. 正式任务不应一次性全部生成，而应根据生育期和时间窗口逐步生成。
3. 生育期会随气象、积温、人工录入真实生育期而更新。
4. 运行期的田间信息、设备信息、人工反馈会触发新的任务意图。
5. 不同农事有不同执行方式：人工、设备、无人机、第三方平台。
6. 执行后需要记录结果、评价效果，并通过人工复核决定后续动作。
```

---

# 3. MVP 功能范围

```text
1. 种植计划管理
2. 生育期预测与更新
3. 预备农事项生成
4. 正式农事任务生成
5. 运行期事件接入
6. 任务意图生成与人工确认
7. 作业方案生成
8. 作业执行与状态同步
9. 执行评价与反馈
10. 人工复核
11. 系统提醒
12. 计划完成与归档
13. 药剂和肥料库存最小管理
```

---

# 4. MVP 不包含

```text
1. 多农场、多计划全局调度
2. 跨计划设备资源排程
3. 复杂多级审批
4. 完全自动化闭环决策
5. 独立 Recommendation 管理
6. 完整农艺规则后台维护系统
7. 完整仓储、库位、盘点、调拨或财务成本系统
```

---

# 5. 功能说明

## 5.1 创建种植计划

用户录入品种、播期、种植区域、地块等基础信息后，系统创建 `PlantingPlan`。

创建后产生：

```text
PlanCreated
```

并进入初始化流程。

---

## 5.2 生育期预测与初始化

系统通过 `Stage Orchestrator` 调用生育期预测接口，得到生育期预测结果和积温阈值相关信息。

系统维护：

```text
CropStageState
CropThermalTimeState
StagePredictionSnapshot
```

---

## 5.3 生成预备农事项

系统通过 `Task Module` 调用农事日历接口，生成全周期 `CalendarItem`。

`CalendarItem` 是预备农事项，不是正式任务。

---

## 5.4 生成正式农事任务

系统根据：

```text
1. 当前生育期
2. 当前日期
3. 任务生成窗口
4. CalendarItem 状态
5. CalendarItem.generationCondition
```

生成近期正式任务 `FarmingTask`。

正式任务才是执行入口。

---

## 5.5 运行期事件接入

系统可以接收：

```text
1. 气象变化
2. 传感器数据变化
3. 设备数据变化
4. 人工巡田录入
5. 真实生育期录入
6. 执行结果回传
7. 后台任务检查结果
```

这些先进入 `Event Module`，标准化为事件后交给 `Plan Orchestrator`。

---

## 5.6 任务意图生成

当运行期事件表示可能需要新增任务时，系统不直接生成正式任务，而是先生成 `TaskIntent`。

例如：

```text
人工巡田录入缺水
  ↓
Runtime Rule Engine 判断
  ↓
TaskIntent：建议生成灌溉任务，等待人工确认
```

MVP 阶段建议优先人工判断。

---

## 5.7 作业方案生成

部分正式任务需要生成 `OperationPlan`。

例如：

```text
灌溉任务 → 生成灌溉量、执行区域、设备参数
施肥任务 → 生成施肥量、肥料类型、处方图
植保任务 → 生成药剂、剂量、喷施区域
```

`OperationPlan` 是执行模块的依据。

---

## 5.8 物料入库与库存

药剂和肥料入库需要维护独立库存表。

系统维护：

```text
InventoryItem
InventoryTransaction
```

MVP 只处理最小入库和库存流水，不做完整仓储管理。库存数据可以支撑后续植保方案和施肥方案查询可用物料。

---

## 5.9 作业执行

`Execution Module` 根据：

```text
FarmingTask + OperationPlan
```

创建执行实例。

执行方式可以是：

```text
1. 人工执行
2. 设备执行
3. 无人机执行
4. 第三方作业平台执行
```

---

## 5.10 外部执行系统对接

外部执行系统包括：

```text
1. 灌溉设备
2. 无人机平台
3. 第三方作业平台
```

两种状态获取方式：

```text
1. 主动回调：HW → Execution Module
2. 后台轮询：ExecutionStatusPollingJob → HW
```

---

## 5.11 执行评价与反馈

执行完成后，系统生成：

```text
ExecutionRecord
Evaluation
Feedback
```

`Feedback` 不直接生成任务，而是回到 `Plan Orchestrator` 判断是否需要复核或调整后续内容。

---

## 5.12 人工复核

需要人工判断的事项进入 `ReviewRequest`。

例如：

```text
1. 任务意图确认
2. 异常执行结果复核
3. 是否生成补救任务
4. 是否调整后续作业方案
```

复核完成后产生：

```text
ReviewRequestResolved
```

再由 `Plan Orchestrator` 协调后续动作。

---

# 6. MVP 阶段不单独维护 Recommendation

## 6.1 调整原因

系统中原本讨论过 `Recommendation`，但在当前 MVP 中容易和以下对象混淆：

```text
TaskIntent
OperationPlan
SystemNotification
```

因此 MVP 阶段不再将 `Recommendation` 作为独立对象。

## 6.2 替代方案

| 内容 | 放置位置 |
|---|---|
| 系统为什么建议生成任务 | TaskIntent |
| 任务生成原因 | FarmingTask |
| 具体处方图、剂量、参数 | OperationPlan |
| 方案依据 | OperationPlan |
| 提醒用户查看 | SystemNotification |

## 6.3 后续扩展

如果后续需要独立管理农艺建议、建议采纳率、建议版本和建议解释，可以再引入 `Recommendation`。

---

# 7. 核心业务主线

```text
创建 PlantingPlan
  ↓
初始化生育期
  ↓
生成 CalendarItem
  ↓
生成近期 FarmingTask
  ↓
生成 OperationPlan
  ↓
执行任务
  ↓
记录 ExecutionRecord
  ↓
生成 Evaluation / Feedback
  ↓
ReviewRequest 人工复核
  ↓
调整后续 FarmingTask / OperationPlan
  ↓
计划完成 / 归档
```

运行期触发主线：

```text
FieldConditionReported / SensorDataUpdated / WeatherUpdated
  ↓
Event Module
  ↓
Plan Orchestrator
  ↓
Stage Orchestrator / Runtime Rule Engine / Task Module
  ↓
TaskIntent / FarmingTask / OperationPlan
```
