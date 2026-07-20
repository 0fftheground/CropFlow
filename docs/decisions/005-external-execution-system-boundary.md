# ADR 005：外部执行系统不放入系统输入

## 决策

硬件、无人机、第三方作业平台作为 External Execution System 单独建模，不放在系统输入框中。

## 背景

外部执行系统既是系统下发任务的目标，也是执行状态和作业结果的来源。单纯放在系统输入中会造成边界混乱。

## 关系

```text
Execution Module → HW
HW → Execution Module
ExecutionStatusPollingJob → HW
```

其中：

```text
Execution Module → HW：下发任务或指令。
HW → Execution Module：主动回调。
ExecutionStatusPollingJob → HW：后台轮询兜底。
```
