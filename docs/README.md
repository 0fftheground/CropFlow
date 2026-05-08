# CropFlow Docs

本目录按文档用途分层，避免所有设计材料堆在同一层级。

## 推荐阅读顺序

```text
1. overview/team-technical-briefing.md
2. overview/meeting.md
3. planning/development-roadmap.md
4. planning/team-work-division.md
5. planning/agent-development-guidelines.md
6. model/data-model.md
7. workflow/task-workflow-matrix.md
8. workflow/background-job-matrix.md
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
│   ├── team-work-division.md
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
