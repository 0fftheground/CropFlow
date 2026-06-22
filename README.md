# CropFlow

CropFlow 是一个围绕作物种植计划运行的农事编排 MVP。

第一版目标是把一个种植计划内的关键链路跑通：系统根据生育期、农事日历、调查结果、算法结果和人工反馈，维护计划下的农事项、作业方案、执行记录和复核事项。

```text
创建种植计划
→ 生育期预测
→ 生成农事安排
→ 形成可执行任务
→ 生成作业方案
→ 记录执行结果
→ 产生反馈或复核
→ 根据反馈继续调整计划内任务
```

## 当前阶段

当前已进入 `P2` 核心工程骨架与最小实现阶段。后端已具备 FastAPI + SQLAlchemy + Alembic 基础工程、核心 ORM / Repository / Orchestrator、首批 API handler 和测试骨架。

仓库级实时推进状态以以下文件为准：

```text
project-context/development-plan.md
project-context/current-memory.md
project-context/phases/
```

当前阶段重点：

```text
1. 接入真实杂草诊断服务并补集成测试。
2. 接入后台作业调度并打通首条端到端联调链路。
3. 继续补齐执行、复核、任务生成相关测试和运行说明。
```

本地开发启动方式：

```text
API:
  powershell -File scripts/start-dev.ps1 -Mode api -Host 127.0.0.1 -Port 8000

Scheduler:
  powershell -File scripts/start-dev.ps1 -Mode scheduler
```

后台任务默认关闭；如需启动 scheduler，请在 `.env` 中显式设置：

```text
CROPFLOW_BACKGROUND_JOBS_ENABLED=true
```

当前业务分工方向：

```text
农事日历 / 生育期
植保
灌溉
施肥
遥感监测
前端
```

## 核心主线

```text
PlantingPlan
  ↓
CropStageState / CropThermalTimeState / StagePredictionSnapshot
  ↓
CalendarItem
  ↓
TaskIntent / FarmingTask
  ↓
OperationPlan
  ↓
Execution / ExecutionRecord
  ↓
Evaluation / Feedback
  ↓
ReviewRequest
  ↓
后续任务或方案调整
```

关键语义：

```text
1. PlantingPlan 是当前 MVP 的编排边界。
2. CalendarItem 是预备农事项，不是执行入口。
3. FarmingTask 是正式任务，是 Execution Module 的入口。
4. OperationPlan 是作业方案 / 处方方案。
5. Feedback 和 ReviewRequestResolved 必须回到 Plan Orchestrator。
```

## 文档入口

完整文档目录见：

```text
docs/README.md
docs/wiki-index.md
```

建议先读：

```text
docs/overview/team-technical-briefing.md     团队技术说明、系统架构、核心对象和关键流转
docs/domain/README.md                        业务方向长期知识入口
docs/fde/README.md                           FDE 访谈、梳理和文档沉淀方式
docs/frontend/README.md                      前端 handoff 和联调说明入口
```

数据模型和流程：

```text
docs/model/data-model.md                  第一版逻辑数据模型
docs/model/data-model-validation.md       数据模型与业务 / 算法核对记录
docs/workflow/task-workflow-matrix.md        农事项、执行步骤、算法调用和分支关系
docs/workflow/background-job-matrix.md       后台任务、触发时机和输出对象
docs/architecture/orchestration-design.md        Plan Orchestrator 设计
```

架构和模块：

```text
docs/architecture/architecture.md
docs/architecture/system-function.md
docs/model/domain-model.md
docs/architecture/modules.md
docs/architecture/events.md
docs/model/glossary.md
```

补充材料：

```text
docs/api/                           外部算法接口文档
docs/workflow/flows/                         关键流程拆解
docs/decisions/                     设计决策记录
docs/change-notes/                  已完成工作项的可读变更摘要
docs/workflow/raw/total-workflow.pdf         农事项总流程图原始来源
```

## 团队协作规则

```text
1. 新增核心对象前，先更新 docs/model/data-model.md。
2. 新增农事流程前，先更新 docs/workflow/task-workflow-matrix.md。
3. 新增后台任务前，先更新 docs/workflow/background-job-matrix.md。
4. 新增算法接口前，先放 docs/api 或更新 API contract。
5. 不清楚的执行细节先放 JSON 承接字段，不阻塞核心闭环。
6. 每个方向只负责自己的算法适配和策略差异，不改变核心任务模型。
```

## 技术栈状态

当前已进入后端最小实现阶段。

后端建议方向：

```text
Python + FastAPI
PostgreSQL
SQLAlchemy + Alembic
Pydantic
REST API + OpenAPI
```

前端技术栈可以由前端负责人确定，但需要以 OpenAPI / API contract 为准，并可先基于 mock API 并行开发。

## AI 编码助手说明

使用 Codex 或其他 AI 编程助手时，先阅读：

```text
AGENTS.md
docs/fde/README.md
skills/
```

`AGENTS.md` 记录项目核心边界、命名规则、文档优先级和编码约束。  
`docs/fde/README.md` 记录 FDE 工作方式和业务梳理相关文档入口。  
`skills/` 保存仓库内可继承的 session workflow skill 定义。
