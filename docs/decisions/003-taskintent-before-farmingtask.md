# ADR 003：运行期事件先生成 TaskIntent，再由人工确认生成 FarmingTask

## 决策

运行期触发类事件在 MVP 阶段优先生成 TaskIntent，而不是直接生成 FarmingTask。

## 背景

人工巡田、传感器异常、设备数据变化等事件具有不确定性。直接生成正式任务可能导致误触发。

## 结果

```text
FieldConditionReported
  ↓
Runtime Rule Engine
  ↓
TaskIntent
  ↓
人工确认
  ↓
FarmingTask
```

TaskIntent 需要支持：

```text
pending_confirm
pending_more_info
confirmed
rejected
converted
no_action
expired
```
