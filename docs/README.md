# CropFlow Docs

本目录按文档用途分层，避免所有设计材料堆在同一层级。

## 仓库级入口说明

新的 Codex session 不建议直接从 `docs/` 开始全量阅读。仓库级稳定入口在：

```text
project-context/entrypoints.md
project-context/development-plan.md
project-context/current-memory.md
```

其中：

```text
1. project-context/entrypoints.md 负责稳定阅读入口和按任务分类的文档索引。
2. project-context/development-plan.md 负责全局 phase 计划。
3. project-context/current-memory.md 只负责当前 phase 的压缩进展快照。
```

如果当前动作属于 session 恢复或当天扫尾，推荐先显式调用：

```text
Use $cropflow-start-work to restore current CropFlow progress
Use $cropflow-wrap-up to summarize today, update memory, and prepare commit actions
```

## 推荐阅读顺序

```text
1. ../project-context/entrypoints.md
2. ../project-context/development-plan.md
3. ../project-context/current-memory.md
4. overview/team-technical-briefing.md
5. overview/meeting.md
6. planning/development-roadmap.md
7. planning/team-work-division.md
8. planning/agent-development-guidelines.md
9. model/data-model.md
10. workflow/task-workflow-matrix.md
11. workflow/background-job-matrix.md
```

## 目录结构

```text
docs/
├── README.md
├── overview/
│   ├── team-technical-briefing.md
│   └── meeting.md
├── planning/
│   ├── development-roadmap.md
│   ├── non-code-integration-package-template.md
│   ├── plant-protection-closed-loop-schedule.md
│   ├── team-work-division.md
│   ├── team-work-division/
│   │   ├── product-architecture-owner.md
│   │   ├── core-backend.md
│   │   ├── calendar-stage.md
│   │   ├── plant-protection.md
│   │   ├── irrigation.md
│   │   ├── fertilization.md
│   │   ├── remote-sensing.md
│   │   └── frontend.md
│   └── agent-development-guidelines.md
├── architecture/
│   ├── architecture.md
│   ├── system-function.md
│   ├── modules.md
│   ├── events.md
│   └── orchestration-design.md
├── model/
│   ├── domain-model.md
│   ├── data-model.md
│   ├── data-model-validation.md
│   └── glossary.md
├── workflow/
│   ├── task-workflow-matrix.md
│   ├── background-job-matrix.md
│   ├── total-workflow.pdf
│   └── flows/
├── api/
└── decisions/
```

## 各目录用途

| 目录 | 用途 |
|---|---|
| `overview/` | 给团队说明项目目标、系统架构、核心对象和关键流转 |
| `planning/` | 推进节奏、团队分工、AI agent 开发规范 |
| `architecture/` | 系统架构、模块边界、事件、编排器设计 |
| `model/` | 领域模型、数据模型、模型核对和术语表 |
| `workflow/` | 农事项流程、后台任务、流程图来源和流程拆解 |
| `api/` | 外部算法接口、后续 OpenAPI / API contract |
| `decisions/` | 设计决策记录 |

## 维护规则

```text
1. 新增核心对象：先更新 model/data-model.md。
2. 新增农事流程：先更新 workflow/task-workflow-matrix.md。
3. 新增后台任务：先更新 workflow/background-job-matrix.md。
4. 新增算法接口：放入 api/。
5. 新增设计取舍：放入 decisions/。
6. 新增面向团队协作或 agent 的执行规则：放入 planning/。
```
