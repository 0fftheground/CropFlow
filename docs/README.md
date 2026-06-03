# CropFlow Docs

本目录只保留当前仍有持续维护价值的正式文档，并按用途分层，避免设计材料和一次性协作文档混在一起。

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
5. planning/development-roadmap.md
6. planning/team-work-division.md
7. planning/agent-development-guidelines.md
8. model/data-model.md
9. workflow/task-workflow-matrix.md
10. workflow/background-job-matrix.md
```

说明：

```text
1. 一次性会议议程、历史 session 记录和重复二级入口已经移除或并入稳定入口。
2. 如果只是恢复当前工作，不要顺着 docs/ 目录逐个打开，先看 project-context/ 下的稳定入口。
3. docs/planning/team-work-division/、docs/planning/P1/ 和 docs/planning/P2/ 仍然保留，但建议通过 project-context/entrypoints.md 按任务定向进入。
```

## 目录结构

```text
docs/
├── README.md
├── development/
├── overview/
│   └── team-technical-briefing.md
├── planning/
│   ├── README.md
│   ├── P1/
│   │   └── plant-protection-closed-loop-schedule.md
│   ├── P2/
│   │   ├── p2-backend-runbook.md
│   │   ├── p2-backend-weed-implementation-breakdown.md
│   │   ├── p2-v1-migration-plan.md
│   │   └── p2-v1-migration-scope.md
│   ├── development-roadmap.md
│   ├── guides/
│   │   ├── agent-development-guidelines.md
│   │   └── non-code-integration-package-template.md
│   ├── team-work-division.md
│   ├── team-work-division/
│   │   ├── product-architecture-owner.md
│   │   ├── core-backend.md
│   │   ├── calendar-stage.md
│   │   ├── plant-protection.md
│   │   ├── irrigation.md
│   │   ├── fertilization.md
│   │   ├── remote-sensing.md
│   │   ├── frontend.md
│   │   └── frontend-plant-protection-handoff.md
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
| `development/` | 仓库级本地启动、迁移、seed、联调环境说明 |
| `overview/` | 给团队说明项目目标、系统架构、核心对象和关键流转 |
| `planning/` | 推进节奏、团队分工、AI agent 开发规范 |
| `architecture/` | 系统架构、模块边界、事件、编排器设计 |
| `model/` | 领域模型、数据模型、模型核对和术语表 |
| `workflow/` | 农事项流程、后台任务、流程图来源和流程拆解 |
| `api/` | 外部算法接口、后续 OpenAPI / API contract |
| `decisions/` | 设计决策记录 |

## API 文档入口

| 文档 | 用途 |
|---|---|
| `api/frontend-plant-protection-api-contract.md` | 植保链路前端联调 contract |
| `api/weed_diagnosis_api.md` | 杂草诊断算法接口 |
| `api/growth_stage_prediction_api.md` | 生育期预测算法接口，用于 Stage Orchestrator 初始化和阶段状态管理 |
| `api/pestDisease_survey_window_api.md` | 病虫害调查窗口算法接口当前版，用于初始化常规调查计划和每日更新调查事件 |
| `api/weather_api.pdf` | 气象数据接口原始文档，用于后续组装逐日天气、逐小时天气和预警数据 |

## 本地开发入口

| 文档 | 用途 |
|---|---|
| `development/local-dev-runbook.md` | 仓库级本地启动、migration、seed 和联调环境说明 |

## 精简规则

```text
1. 一次性会议材料、阶段性 session 手记、重复目录入口不再单独保留。
2. 已被 project-context/ 或正式设计文档替代的说明稿，优先合并后删除。
3. 如果一份文档只服务某个短期联调动作，优先并入对应正式 runbook 或 handoff 文档。
```

## 维护规则

```text
1. 新增核心对象：先更新 model/data-model.md。
2. 新增农事流程：先更新 workflow/task-workflow-matrix.md。
3. 新增后台任务：先更新 workflow/background-job-matrix.md。
4. 新增算法接口：放入 api/。
5. 新增设计取舍：放入 decisions/。
6. 新增面向团队协作或 agent 的执行规则：放入 planning/。
```
