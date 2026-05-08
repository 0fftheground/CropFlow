# CropFlow Orchestration Design

> 本文档用于补充 CropFlow 的编排设计，重点解决一个问题：  
> **Plan Orchestrator / Stage Orchestrator / Task Module 不应变成超级服务类。**

---

## 1. 系统要完成的核心任务

CropFlow 的 Plan-level MVP 不是单纯的“农事日历系统”，而是一个围绕单个种植计划运行的闭环系统。

它要完成 5 类核心任务：

```text
1. 计划初始化
   创建种植计划，预测生育期，生成预备农事项和近期正式任务。

2. 状态感知
   接收气象、传感器、人工录入、设备状态、计划变更等信息。

3. 规则判断
   判断这些信息是否影响生育期、农事项、任务、方案或执行状态。

4. 任务与方案生成
   根据预备农事项、运行期事件、人工复核结论生成 FarmingTask 和 OperationPlan。

5. 执行反馈闭环
   执行任务，接收结果，评价执行质量，必要时触发复核或后续任务调整。
```

因此系统的本质是：

```text
Event → State → Decision → Task → OperationPlan → Execution → Evaluation → Feedback → Review / Next Action
```

---

## 2. 当前架构中的风险

当前架构中有几个核心组件：

```text
Plan Orchestrator
Stage Orchestrator
Runtime Rule Engine
Task Module
Execution Module
Evaluation & Feedback Module
Review Module
```

其中风险最大的是：

```text
Plan Orchestrator
```

如果不控制边界，它很容易变成：

```text
1. 所有事件都在这里判断
2. 所有任务都在这里生成
3. 所有反馈都在这里处理
4. 所有规则都在这里写 if-else
5. 所有模块之间的细节都在这里耦合
```

这会导致后续很难维护、测试和多人协作。

---

## 3. 总体设计原则

### 3.1 Orchestrator 只做编排，不做复杂业务判断

Orchestrator 的职责是：

```text
接收事件
识别流程
调用处理器
协调模块
提交结果
发布后续事件
```

Orchestrator 不应该直接承担：

```text
复杂规则判断
不同农事类型差异处理
算法接口选择细节
执行结果合格性判断
具体任务字段组装
```

### 3.2 Handler 处理单类事件

每一类事件由独立 Handler 处理。

例如：

```text
PlanCreatedHandler
PlanKeyInfoChangedHandler
WeatherUpdatedHandler
ActualStageRecordedHandler
FieldConditionReportedHandler
TaskDueCheckTriggeredHandler
ExecutionStatusUpdatedHandler
FeedbackGeneratedHandler
ReviewRequestResolvedHandler
```

Plan Orchestrator 只负责把事件分发给对应 Handler。

### 3.3 Policy 负责业务判断

Policy 用来回答：

```text
是否应该做某件事？
是否需要更新？
是否需要复核？
是否需要重新生成方案？
是否允许覆盖原任务？
```

典型 Policy：

```text
TaskGenerationPolicy
TaskUpdatePolicy
OperationPlanRefreshPolicy
StageChangeImpactPolicy
FeedbackReviewPolicy
ReviewDecisionPolicy
TaskInvalidationPolicy
```

### 3.4 Strategy 负责农事类型差异

不同农事类型的逻辑不同。

例如：

```text
灌溉
施肥
植保
巡田
采收
无人机作业
人工任务
```

它们在以下方面会有差异：

```text
是否需要 OperationPlan
调用哪个算法接口
是否需要设备执行
是否需要人工复核
执行结果如何评价
反馈后是否可能生成补救任务
```

因此建议引入：

```text
TaskTypeStrategy
```

典型实现：

```text
IrrigationTaskStrategy
FertilizationTaskStrategy
PlantProtectionTaskStrategy
RemoteSensingTaskStrategy
FieldInspectionTaskStrategy
ManualTaskStrategy
DroneTaskStrategy
```

### 3.5 Service 执行具体领域动作

Service 负责具体动作，例如创建任务、更新状态、保存方案、生成复核事项。

例如：

```text
CalendarItemService
TaskIntentService
FarmingTaskService
OperationPlanService
StageStateService
ThermalTimeService
ReviewRequestService
ExecutionService
FeedbackService
```

---

## 4. 推荐的分层结构

建议实现时采用下面的结构：

```text
Input Event
  ↓
Event Module
  ↓
Plan Orchestrator
  ↓
Event Handler
  ↓
Policy / Strategy
  ↓
Domain Service
  ↓
Repository / External Client
```

对应关系：

```text
Orchestrator：流程协调
Handler：单类事件处理
Policy：业务判断
Strategy：农事类型差异
Service：执行领域动作
Repository：数据读写
External Client：外部接口调用
```

---

## 5. Plan Orchestrator 的职责边界

### 5.1 应该负责

Plan Orchestrator 应负责：

```text
1. 接收 Event Module 或 Domain Event 传入的事件。
2. 根据 eventType 找到对应 Event Handler。
3. 为 Handler 准备必要上下文，例如 PlantingPlan。
4. 调用 Handler。
5. 接收 Handler 返回的结果。
6. 统一处理事务提交、事件发布、日志记录。
7. 保证关键流程不绕过计划级编排。
```

### 5.2 不应该负责

Plan Orchestrator 不应该负责：

```text
1. 直接判断事件是否要生成 FarmingTask。
2. 直接判断某个任务是否应该更新。
3. 直接拼装 OperationPlan。
4. 直接判断执行结果是否合格。
5. 直接调用所有算法接口。
6. 直接处理不同农事类型的分支逻辑。
7. 直接写大量 if taskType == irrigation 之类的逻辑。
```

### 5.3 推荐伪代码

```text
PlanOrchestrator.handle(event):
    context = buildPlanContext(event.planId)
    handler = handlerRegistry.get(event.eventType)
    result = handler.handle(event, context)
    persistChanges(result)
    publishEvents(result.domainEvents)
    createNotifications(result.notifications)
```

这里的关键是：

```text
PlanOrchestrator 不关心事件内部细节。
```

---

## 6. Event Handler 设计

### 6.1 Handler 输入

Handler 统一输入：

```text
event
planContext
```

其中 planContext 可以包含：

```text
PlantingPlan
CropStageState
CropThermalTimeState
近期 CalendarItem
未完成 FarmingTask
未完成 TaskIntent
未关闭 ReviewRequest
```

### 6.2 Handler 输出

Handler 不直接操作所有副作用，而是返回处理结果。

```text
HandlerResult
  - changedEntities
  - newEntities
  - domainEvents
  - reviewRequests
  - systemNotifications
  - externalCallsRequired
```

MVP 阶段可以不抽象得太复杂，但建议保留这个思想。

注意：

```text
HandlerResult 是实现层返回结构，不是核心业务对象。
externalCallsRequired 表示需要由对应模块或客户端处理的外部调用意图，不表示 Handler 直接绕过模块边界调用外部系统。
```

### 6.3 MVP 需要的 Handler

#### PlanCreatedHandler

负责计划创建后的初始化流程。

```text
PlanCreated
  ↓
预测生育期
  ↓
生成 CalendarItem
  ↓
生成近期 FarmingTask
```

#### PlanKeyInfoChangedHandler

负责计划关键字段变化后的重算。

```text
PlanKeyInfoChanged
  ↓
判断影响范围
  ↓
必要时重新预测生育期
  ↓
必要时标记旧 CalendarItem / OperationPlan 失效
  ↓
重新生成相关内容
```

#### WeatherUpdatedHandler

负责气象更新后的反应。

```text
WeatherUpdated
  ↓
Stage Orchestrator 更新积温
  ↓
判断是否影响生育期预测
  ↓
如生育期变化，返回 StageChanged
  ↓
Plan Orchestrator 继续处理 StageChanged 影响
```

#### ActualStageRecordedHandler

负责用户录入真实生育期。

```text
ActualStageRecorded
  ↓
Stage Orchestrator 应用真实生育期
  ↓
更新 CropStageState
  ↓
生成 ActualStageApplied
  ↓
Plan Orchestrator 判断对任务和方案的影响
```

#### FieldConditionReportedHandler

负责人工巡田或外部数据上报田间情况。

```text
FieldConditionReported
  ↓
Runtime Rule Engine 判断
  ↓
生成 TaskIntent / NeedMoreInfo / NoAction
  ↓
必要时生成 ReviewRequest
```

注意：

```text
MVP 阶段不建议 FieldConditionReported 直接生成 FarmingTask。
```

#### TaskDueCheckTriggeredHandler

负责定时任务检查。

```text
TaskDueCheckTriggered
  ↓
查找进入生成窗口且满足生成条件的 CalendarItem
  ↓
生成或更新 FarmingTask
  ↓
必要时生成 SystemNotification
```

#### ExecutionStatusUpdatedHandler

负责外部执行状态更新。

```text
ExecutionStatusUpdated
  ↓
委托 Execution Module 更新 Execution / ExecutionRecord
  ↓
必要时触发 Evaluation
  ↓
生成 FeedbackGenerated
```

注意：

```text
Execution / ExecutionRecord / DeviceCommand 的状态维护仍属于 Execution Module。
ExecutionStatusUpdatedHandler 只负责把执行状态更新纳入计划级后续编排。
```

#### FeedbackGeneratedHandler

负责执行反馈后的业务处理。

```text
FeedbackGenerated
  ↓
判断是否需要人工复核
  ↓
判断是否影响后续任务
  ↓
生成 ReviewRequest / TaskIntent / TaskUpdateCommand
```

注意：

```text
Feedback 不直接生成 FarmingTask，必须回到 Plan Orchestrator。
```

#### ReviewRequestResolvedHandler

负责人工复核完成后的处理。

```text
ReviewRequestResolved
  ↓
根据复核结论生成 FarmingTask / 更新 FarmingTask / 关闭 TaskIntent / 标记 NoAction
  ↓
必要时生成 OperationPlan
```

---

## 7. Stage Orchestrator 的减重方案

Stage Orchestrator 也不应该承担太多逻辑。

建议拆成：

```text
ThermalTimeService
StagePredictionService
ActualStageApplyService
StageChangeDetector
StageSnapshotService
```

### 7.1 Stage Orchestrator 负责

```text
1. 协调积温计算。
2. 调用生育期预测接口。
3. 应用真实生育期。
4. 保存生育期状态和预测快照。
5. 生成 StageChanged / ActualStageApplied。
```

### 7.2 不负责

```text
1. 不直接生成 FarmingTask。
2. 不直接更新 OperationPlan。
3. 不直接处理农事规则。
4. 不直接判断后续哪些任务需要失效。
```

这些影响由 Plan Orchestrator 调用对应 Handler / Policy 处理。

---

## 8. Task Module 的内部拆分

Task Module 对外是一个模块，但内部不要做成一个大类。

建议拆成：

```text
CalendarItemService
TaskGenerationService
TaskIntentService
FarmingTaskService
OperationPlanService
TaskLifecycleService
TaskConflictService
```

### 8.1 CalendarItemService

负责：

```text
预备农事项创建
预备农事项失效
预备农事项版本保留
```

### 8.2 TaskGenerationService

负责：

```text
根据 CalendarItem 判断是否需要生成 FarmingTask
判断任务生成窗口
维护自动生成策略
```

### 8.3 TaskIntentService

负责：

```text
创建 TaskIntent
保留 NoAction
处理 NeedMoreInfo
关闭或转换 TaskIntent
```

### 8.4 FarmingTaskService

负责：

```text
创建正式任务
更新正式任务
取消正式任务
标记任务完成 / 失败 / 过期
```

### 8.5 OperationPlanService

负责：

```text
调用算法接口
生成 OperationPlan
刷新 OperationPlan
标记旧方案失效
保留方案版本
```

### 8.6 TaskLifecycleService

负责统一任务状态流转：

```text
draft
pending_review
pending_execute
executing
completed
failed
cancelled
expired
invalidated
```

---

## 9. Runtime Rule Engine 的定位

Runtime Rule Engine 不是万能规则平台，MVP 阶段建议定位为：

```text
运行期事件 → 业务判断结果
```

它主要处理：

```text
FieldConditionReported
SensorDataUpdated
DeviceDataUpdated
WeatherUpdated 的部分业务规则
FeedbackGenerated 的部分业务规则
```

输出不应该直接是 FarmingTask，而应该是：

```text
TaskIntent
NeedMoreInfo
NoAction
ReviewRequired
```

其中：

```text
TaskIntent 需要持久化。
NeedMoreInfo、NoAction、ReviewRequired 应作为 TaskIntent 状态、规则判断结果或处理记录持久化，不作为独立核心对象引入。
```

---

## 10. Task Type Strategy 设计

### 10.1 Strategy 需要回答的问题

每个农事类型 Strategy 需要回答：

```text
1. 是否需要 OperationPlan？
2. 需要调用哪个算法接口？
3. 是否允许自动生成 FarmingTask？
4. 是否需要人工复核？
5. 默认执行方式是什么？
6. 执行反馈如何评价？
7. 失败或不合格后是否需要生成补救意图？
```

### 10.2 示例

#### IrrigationTaskStrategy

```text
需要 OperationPlan：是
算法接口：灌溉算法接口
执行方式：设备 / 人工
是否需要复核：视触发来源和风险等级
反馈评价：水量、时长、区域、设备状态
```

#### FertilizationTaskStrategy

```text
需要 OperationPlan：是
算法接口：施肥算法接口
执行方式：人工 / 设备 / 无人机
是否需要复核：通常需要
反馈评价：施肥量、作业面积、处方匹配度
```

#### PlantProtectionTaskStrategy

```text
需要 OperationPlan：是
算法接口：植保算法接口
执行方式：人工 / 无人机 / 第三方服务
是否需要复核：通常需要
反馈评价：用药、区域、天气窗口、作业覆盖度
```

#### RemoteSensingTaskStrategy

```text
需要 OperationPlan：通常需要
算法接口：缺苗识别 / 长势监测 / NDVI / 异常归因相关算法接口
执行方式：无人机 / 影像上传 / 算法处理
是否需要复核：异常结果通常需要人工判断
反馈评价：影像质量、监测区域、缺苗区域、长势等级、异常点位、处方图质量
```

#### FieldInspectionTaskStrategy

```text
需要 OperationPlan：通常不需要
算法接口：通常不需要
执行方式：人工
是否需要复核：按配置
反馈评价：是否完成巡田和是否产生新的 FieldConditionReported
```

---

## 11. 关键流程如何落到组件

### 11.1 计划创建初始化

```text
PlanCreated
  ↓
PlanOrchestrator
  ↓
PlanCreatedHandler
  ↓
StageOrchestrator
  ↓
TaskModule.CalendarItemService
  ↓
TaskModule.TaskGenerationService
  ↓
TaskModule.FarmingTaskService
  ↓
TaskModule.OperationPlanService
```

### 11.2 气象更新导致生育期变化

```text
WeatherUpdated
  ↓
Event Module
  ↓
PlanOrchestrator
  ↓
WeatherUpdatedHandler
  ↓
StageOrchestrator
  ↓
StageChanged
  ↓
StageChangedHandler / StageChangeImpactPolicy
  ↓
Task Module 更新相关 CalendarItem / FarmingTask / OperationPlan
```

### 11.3 人工巡田上报缺水

```text
FieldConditionReported(conditionType=缺水)
  ↓
Event Module
  ↓
PlanOrchestrator
  ↓
FieldConditionReportedHandler
  ↓
Runtime Rule Engine
  ↓
TaskIntent / NeedMoreInfo / NoAction
  ↓
ReviewRequest
  ↓
人工复核
  ↓
ReviewRequestResolved
  ↓
PlanOrchestrator
  ↓
FarmingTask / OperationPlan
```

### 11.4 执行反馈不合格

```text
ExecutionStatusUpdated
  ↓
Execution Module
  ↓
Evaluation & Feedback Module
  ↓
FeedbackGenerated
  ↓
PlanOrchestrator
  ↓
FeedbackGeneratedHandler
  ↓
FeedbackReviewPolicy
  ↓
ReviewRequest / TaskIntent / NoAction
```

---

## 12. 事务边界建议

MVP 阶段可以先简单处理，但建议保持下面原则：

```text
1. 一个 Handler 处理一个事件。
2. 一个 Handler 内部可以有一个事务边界。
3. 外部算法调用不要和数据库事务强绑定。
4. 外部设备下发不要和业务状态更新放在同一个强事务里。
5. 重要外部调用结果必须保存快照。
6. 事件处理要支持幂等。
```

尤其需要注意：

```text
同一个 WeatherUpdated 不应重复生成相同 FarmingTask。
同一个 ReviewRequestResolved 不应重复生成多个相同任务。
同一个 FeedbackGenerated 不应重复生成多个复核事项。
```

---

## 13. 幂等设计建议

每类事件需要有业务幂等键。

示例：

```text
WeatherUpdated:
  planId + weatherDate + dataVersion

TaskDueCheckTriggered:
  planId + checkDate + generationWindow

FieldConditionReported:
  planId + sourceType + sourceRecordId

ReviewRequestResolved:
  reviewRequestId + resolvedVersion

FeedbackGenerated:
  executionId + feedbackVersion
```

---

## 14. 对多人协作的建议

多人开发时可以按模块拆分：

```text
1. Plan Orchestrator + Handler Registry
2. Stage Orchestrator + Stage Services
3. Task Module 内部服务
4. Runtime Rule Engine
5. Execution Module
6. Evaluation & Feedback Module
7. Review Module
8. Event Module + Background Job Center
```

协作边界建议：

```text
Handler 调 Module
Module 不反向调 Handler
Execution Module 不创建 FarmingTask
Task Module 不直接控制硬件
Stage Orchestrator 不直接生成任务
Feedback Module 不直接创建正式任务
Review Module 不直接绕过 Plan Orchestrator
```

---

## 15. MVP 阶段推荐的最小实现

不建议一开始就实现过度复杂的框架。

MVP 可以先这样落地：

```text
PlanOrchestrator
  - handlerRegistry
  - handle(event)

handlers/
  - PlanCreatedHandler
  - WeatherUpdatedHandler
  - FieldConditionReportedHandler
  - TaskDueCheckTriggeredHandler
  - FeedbackGeneratedHandler
  - ReviewRequestResolvedHandler

policies/
  - TaskGenerationPolicy
  - StageChangeImpactPolicy
  - FeedbackReviewPolicy

strategies/
  - IrrigationTaskStrategy
  - FertilizationTaskStrategy
  - PlantProtectionTaskStrategy
  - RemoteSensingTaskStrategy
  - ManualTaskStrategy

services/
  - StageService
  - CalendarItemService
  - TaskIntentService
  - FarmingTaskService
  - OperationPlanService
  - ReviewRequestService
  - ExecutionService
```

这样既能避免超级 Orchestrator，又不会在 MVP 阶段拆得太碎。

---

## 16. 最终结论

CropFlow 的编排设计建议采用：

```text
Plan Orchestrator：流程入口和协调器
Event Handler：事件处理单元
Policy：业务判断
Strategy：农事类型差异
Domain Service：领域动作
Repository / Client：数据和外部接口
```

核心原则是：

```text
Orchestrator 不承载复杂业务判断。
Task Module 不处理执行闭环。
Execution Module 不生成业务任务。
Feedback 必须回到 Plan Orchestrator。
人工复核结果必须回到 Plan Orchestrator。
不同农事类型差异通过 Strategy 管理。
```

这样可以让系统在 MVP 阶段保持可实现，同时为后续多农场、多计划、多设备、多作业资源调度留下扩展空间。
