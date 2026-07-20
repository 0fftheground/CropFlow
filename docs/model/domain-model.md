# Plan-level MVP 核心对象说明（v4：移除 Recommendation）

> 本版调整：MVP 阶段不再将 `Recommendation` 作为独立核心对象。  
> 农艺建议、推荐原因、方案依据分别放入 `TaskIntent / FarmingTask / OperationPlan` 中。

---

# 1. 当前核心对象总览

## 1.1 计划与生育期对象

```text
PlantingPlan
CropStageState
CropThermalTimeState
StagePredictionSnapshot
```

## 1.2 农事项与任务对象

```text
CalendarItem
TaskIntent
FarmingTask
```

## 1.3 作业方案与执行对象

```text
OperationPlan
Execution
ExecutionRecord
DeviceCommand
```

## 1.4 评价、反馈与人工复核对象

```text
Evaluation
Feedback
ReviewRequest
SystemNotification
```

## 1.5 物料与库存对象

```text
InventoryItem
InventoryTransaction
```

---

# 2. PlantingPlan：种植计划

## 定位

`PlantingPlan` 是系统运行的核心上下文。  
MVP 阶段以单个 `PlantingPlan` 为编排边界。

## 主要承载

```text
1. 农场归属、作物、品种引用、播期等计划基础信息
2. 当前计划状态
3. 任务生成窗口配置
4. 计划创建、运行、完成、归档状态
```

补充说明：

```text
1. PlantingPlan 保留 farmId。
2. PlantingPlan 不再直接保存 fieldId。
3. 计划与地块关系通过 PlantingPlanFieldRelation 维护。
4. 农场与地块关系通过 FarmFieldRelation 维护。
5. 品种通过独立 RiceVariety 维护，PlantingPlan 通过 varietyId 引用。
6. cultiTypeCode / plantingMethodCode 等基础业务枚举通过 cf_code_dict 维护，其结构和初始化数据沿用 agri_code_dict。
```

---

# 3. CropStageState：生育期状态

## 定位

表示当前计划的生育期运行状态。

## 主要承载

```text
1. 当前生育期
2. 当前生育期来源：预测 / 人工录入 / 系统修正
3. 最近一次更新时间
```

## 与 PlantingPlan 的关系

`PlantingPlan` 不再重复维护 `currentStage`。  
当前生育期统一以 `CropStageState` 为准。

---

# 4. CropThermalTimeState：积温状态

## 定位

记录当前计划的累计积温状态。

## 主要承载

```text
1. 当前累计积温
2. 起算日期
3. 最近计算日期
4. 使用的积温阈值版本或快照引用
```

---

# 5. StagePredictionSnapshot：生育期预测快照

## 定位

记录每次生育期预测或修正的结果快照。

## 价值

```text
1. 保留历史预测结果
2. 支持对比预测变化
3. 支持追溯气象数据或人工反馈对预测的影响
```

---

# 6. CalendarItem：预备农事项

## 定位

`CalendarItem` 是由农事日历接口或规则生成的“预备农事项”。

它表示：

```text
未来可能需要做的农事安排
```

但它不是正式任务，不能直接执行。

## 主要作用

```text
1. 承接农事日历接口返回的全周期农事项
2. 作为后续生成 FarmingTask 的来源
3. 支持在生育期变化、计划关键字段变化后更新或失效
4. 支持记录运行期补充调查、复查、评估类农事项的上游任务来源
```

## 状态建议

```text
active
converted
invalidated
cancelled
```

---

# 7. 任务生成逻辑

## 定位

MVP 第一版不把 `TaskGenerationPlan` 作为核心对象或独立表。

任务生成逻辑由 `TaskDueCheckJob / TaskGenerationService` 根据 `CalendarItem` 完成。

## 主要作用

```text
1. 检查 CalendarItem 是否进入任务生成窗口
2. 检查 CalendarItem.generationCondition 是否满足
3. 避免一次性生成整个种植季的正式任务
4. 生成近期需要进入执行闭环的 FarmingTask
```

---

# 8. TaskIntent：任务意图

## 定位

`TaskIntent` 表示系统认为“可能需要生成一个任务”，但还没有成为正式任务。

常见来源：

```text
1. 人工巡田录入缺水、病害、苗情异常
2. 传感器或设备数据触发规则判断
3. 运行期规则引擎判断需要人工确认
4. 执行反馈后建议产生后续任务
```

## 主要价值

```text
1. 支持 MVP 阶段先人工判断，不直接自动生成 FarmingTask
2. 保存触发原因、规则判断结果和建议处理方向
3. 支持 NeedMoreInfo / NoAction 等非任务结果持久化
4. 支持追溯上游前置任务和具体触发记录
```

说明：

```text
NeedMoreInfo / NoAction 不是独立核心对象。
它们优先作为 TaskIntent.status、规则判断结果或处理记录保存。
```

## 可承载的农艺建议内容

MVP 去掉 `Recommendation` 后，运行期触发类建议优先放在 `TaskIntent` 中，例如：

```text
1. 触发原因
2. 规则判断结果
3. 建议任务类型
4. 建议优先级
5. 是否需要补充信息
6. 是否建议生成正式任务
```

## 状态建议

```text
pending_confirm
pending_more_info
confirmed
rejected
converted
no_action
expired
```

---

# 9. FarmingTask：正式农事任务

## 定位

`FarmingTask` 是正式任务，是执行闭环的入口。

它可以来源于：

```text
1. CalendarItem 到期生成
2. TaskIntent 人工确认后生成
3. ReviewRequest 复核后生成
4. 人工手动创建
```

## 可承载的农艺说明

MVP 去掉 `Recommendation` 后，任务级说明可以放入 `FarmingTask`：

```text
1. 任务生成原因
2. 任务来源
3. 任务目标
4. 任务注意事项
5. 上游前置任务与触发记录追溯
```

但具体处方、剂量、设备参数应放在 `OperationPlan`。

## 状态建议

```text
pending
confirmed
in_progress
completed
cancelled
expired
invalidated
```

---

# 10. OperationPlan：作业方案 / 处方方案

## 定位

`OperationPlan` 是给执行模块消费的作业方案。

它回答：

```text
具体怎么做？
在哪里做？
什么时候做？
用什么参数做？
由谁或什么设备执行？
如何验收？
```

## 主要承载

```text
1. 作业区域
2. 作业时间窗口
3. 施肥量 / 灌溉量 / 药剂量
4. 处方图
5. 设备参数
6. 执行方式：人工 / 设备 / 无人机 / 第三方作业
7. 验收标准
8. 方案依据
```

## 与 FarmingTask 的关系

```text
FarmingTask 是执行入口
OperationPlan 是执行依据
```

一个 `FarmingTask` 可以有 0 个、1 个或多个 `OperationPlan`。  
提醒类任务可以没有复杂 `OperationPlan`。

---

# 11. Execution：执行实例

## 定位

表示一次任务执行过程。

## 主要承载

```text
1. 执行对象
2. 执行方式
3. 执行状态
4. 执行开始和结束时间
5. 关联的 FarmingTask / OperationPlan
```

---

# 12. ExecutionRecord：执行记录

## 定位

记录实际执行结果明细。

## 示例

```text
1. 实际灌溉量
2. 实际施肥量
3. 实际喷药面积
4. 无人机作业轨迹
5. 人工上传图片
6. 作业完成率
```

---

# 13. DeviceCommand：设备指令

## 定位

只在设备执行场景出现。

## 主要承载

```text
1. 指令内容
2. 设备编号
3. 指令状态
4. 下发时间
5. 回调结果
```

---

# 14. Evaluation：执行评价

## 定位

对执行结果进行系统评价。

## 示例

```text
1. 是否按方案完成
2. 实际用量是否合格
3. 作业面积是否达标
4. 执行时间是否符合窗口
5. 是否需要复核或补救
```

---

# 15. Feedback：反馈

## 定位

`Feedback` 是执行评价后的业务反馈结果。

## 主要作用

```text
1. 触发人工复核
2. 提示需要补救任务
3. 提示需要调整后续任务或作业方案
4. 支持闭环追溯
```

`Feedback` 不直接生成任务，应回到 `Plan Orchestrator` 判断后续动作。

---

# 16. ReviewRequest：人工复核事项

## 定位

需要人工判断的事项统一进入 `ReviewRequest`。

## 常见来源

```text
1. TaskIntent 需要确认
2. Feedback 需要复核
3. 执行异常
4. 方案调整需要确认
5. 关键生育期修正需要确认
```

## 复核后可能动作

```text
1. 生成 FarmingTask
2. 更新 FarmingTask
3. 更新 OperationPlan
4. 标记 NoAction
5. 要求补充信息
```

---

# 17. SystemNotification：系统提醒

## 定位

`SystemNotification` 只负责提醒用户查看或处理事项。

## 不承载

```text
1. 不承载核心业务状态
2. 不替代 TaskIntent
3. 不替代 ReviewRequest
4. 不替代 FarmingTask
```

---

# 18. InventoryItem：库存物料

## 定位

`InventoryItem` 是药剂和肥料库存主数据。

## 主要承载

```text
1. 物料类型：药剂 / 肥料
2. 物料名称、规格、批次
3. 当前库存数量
4. 有效期和可用状态
```

## 不承载

```text
1. 不承载施肥或打药作业方案
2. 不承载农艺推荐原因
3. 不替代 OperationPlan
```

---

# 19. InventoryTransaction：库存流水

## 定位

`InventoryTransaction` 记录药剂和肥料库存数量变化。

## 主要承载

```text
1. 入库、出库或调整类型
2. 变动数量和单位
3. 来源 FarmingTask / EventRecord
4. 发生时间和操作人
```

## MVP 边界

```text
1. 药剂入库和肥料入库生成 stock_in 流水。
2. 是否在施肥、打药执行后扣减库存，后续在执行集成阶段确认。
3. MVP 不做完整仓储、库位、盘点、调拨或财务成本。
```

---

# 20. MVP 阶段移除 Recommendation 的说明

## 为什么移除

```text
1. Recommendation 容易和 TaskIntent 混淆
2. Recommendation 容易和 OperationPlan 混淆
3. MVP 阶段不需要独立管理农艺建议流
4. 具体处方、剂量、参数应归入 OperationPlan
5. 触发原因、建议说明可归入 TaskIntent / FarmingTask
```

## 去掉后的替代方式

| 原本 Recommendation 中的内容 | MVP 中放到哪里 |
|---|---|
| 运行期触发原因 | TaskIntent |
| 建议生成某类任务 | TaskIntent |
| 正式任务生成说明 | FarmingTask |
| 具体处方图 / 剂量 / 参数 | OperationPlan |
| 方案依据 | OperationPlan |
| 提醒用户查看 | SystemNotification |

## 后续可扩展

如果后续需要独立管理以下能力，可以重新引入 `Recommendation`：

```text
1. 农艺建议流
2. 建议采纳率
3. 建议版本追踪
4. 建议解释与对比
5. 多方案推荐排序
```

---

# 21. 当前核心对象链路

```text
PlantingPlan
  ↓
CropStageState / CropThermalTimeState / StagePredictionSnapshot
  ↓
CalendarItem
  ↓
FarmingTask
  ↓
OperationPlan
  ↓
Execution
  ↓
ExecutionRecord / DeviceCommand
  ↓
Evaluation
  ↓
Feedback
  ↓
ReviewRequest
```

物料库存链路：

```text
药剂 / 肥料入库 FarmingTask
  ↓
InventoryStockInRecorded
  ↓
InventoryItem / InventoryTransaction
```

运行期触发类链路：

```text
Input Event
  ↓
Runtime Rule Engine
  ↓
TaskIntent
  ↓
人工确认
  ↓
FarmingTask
  ↓
OperationPlan
```
