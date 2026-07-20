# Phase P4 - Business Agent Runtime 接入

## 目标

```text
1. 让 Business Agent 基于真实 CropFlow 业务状态运行。
2. 接入 Session / AgentRun / Context Builder / Action Resolver / PreAction。
3. 让查询与写 Action 复用既有 Service 和 PlanOrchestrator。
4. 为写操作建立明确批准、幂等、事件和审计边界。
```

## 当前已完成

```text
Runtime 持久化表和 migration
PlantingPlan Object View
observer / operator / reviewer Action Resolver
任务与复核查询 Action
任务完成与复核处理 Action
批准后重新 PreAction
OpenAI-compatible provider adapter
DeepSeek V4-Pro 真实 tool-calling、只读 loop 与 approval gate 基础联调
DeepSeek V4-Flash / V4-Pro 真实模型 + Mock Business State Eval Dataset、Runner 和报告
Development / Regression / Holdout Dataset split；7 个 P0 场景各 10 次采样
Adapter prompt / cache / completion / reasoning Token usage、估算成本和 p50 / p95 延迟
显式 Thinking / Reasoning Effort / max output tokens 配置和输出截断失败处理
自然语言澄清与 Runtime Approval 协议分层；多 Tool Calls 回归统计
复杂农艺解释、失败恢复、Tool Result 冲突和多轮澄清 Development 场景
Provider 瞬态错误分类、有限重试、backoff / jitter / Retry-After
Run 180 秒活跃执行段、16k Token budget 和可选成本预算
独立只读 Query Tool bounded parallel execution；混合和副作用 Action 串行 replan
Tool rejected / failed / unknown 结构化回注；副作用结果不确定时禁止自动重试
Run / SSE / approval / ontology API
自动化测试
```

## 仍需完成

```text
目标数据库 migration 验证
目标数据库真实业务数据 provider eval；当前只完成真实模型 + Mock Business State Eval
冻结模型配置后的 Holdout 运行，以及新 resilience 策略下的 Development 复测
正式 IAM / 数据范围
Agent 前端与批准交互
durable worker、恢复和多实例事件交付
生产部署验证
```

## 状态

`backend_mvp_implemented`
