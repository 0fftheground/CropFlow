# ADR 012：Agent Runtime 不拥有 CropFlow 业务状态

## 决策

CropFlow Agent Runtime 只拥有会话、运行、工具调用、批准、事件和审计状态；`PlantingPlan / FarmingTask / OperationPlan / Execution / ReviewRequest` 的权威状态继续由现有业务表、Service 和 `PlanOrchestrator` 管理。

## 背景

如果 Agent Runtime 另建任务、复核或工作流状态并直接推进，会产生两套事实源：

```text
CropFlow 业务系统状态
Agent 自己维护的业务状态
```

这会使权限、幂等、人工复核、Feedback 回编排和失败恢复失去统一边界。

## 结果

```text
1. Context Builder 每轮从 CropFlow 权威表重新投影 Object View。
2. Available Action Resolver 只暴露当前角色和业务状态允许的动作。
3. 模型只生成 Action Proposal，不能直接更新 ORM 对象或字段。
4. 查询动作通过既有 QueryService 执行。
5. 写动作必须先人工批准，再次 PreAction 后调用既有 Domain Service。
6. complete_farming_task 复用 TaskExecutionService。
7. resolve_review_request 复用 ReviewRequestService，并继续回到 PlanOrchestrator。
8. cf_agent_* 表只保存 Agent 执行事实，不复制业务对象状态。
```

## ID 取舍

业务实体继续使用现有 bigint 主键。Agent Runtime 的 session、message、run、tool call 和 approval 使用带类型前缀的字符串 ID，原因是它们需要跨 API、provider call id 和事件流稳定传递，不改变既有业务实体 ID 约定。

## 非目标

当前 ADR 不表示已经完成：

```text
企业级 IAM
跨计划自治 Agent
完全自动执行高风险动作
独立业务任务系统
durable worker / 多实例事件总线
生产部署与真实 provider eval
```
