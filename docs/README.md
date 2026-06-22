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

如果当前动作属于 session 恢复、复杂任务规划、单任务收尾、当天扫尾或定期 wiki 整理，推荐先显式调用：

```text
Use $cropflow-start-work to restore current CropFlow progress
Use $cropflow-task-planning to analyze a non-trivial CropFlow change before editing code
Use $cropflow-task-closing to close one completed CropFlow task with tests and doc updates
Use $cropflow-wrap-up to summarize today, update memory, and prepare commit actions
Use $cropflow-wiki-maintenance to audit CropFlow docs for drift, gaps, and overlap
```

## 推荐阅读顺序

```text
1. ../project-context/entrypoints.md
2. ../project-context/development-plan.md
3. ../project-context/current-memory.md
4. overview/team-technical-briefing.md
5. domain/README.md
6. model/data-model.md
7. workflow/task-workflow-matrix.md
8. workflow/background-job-matrix.md
9. architecture/data-integration.md
10. fde/README.md
11. frontend/README.md
```

说明：

```text
1. 一次性会议议程、历史 session 记录和重复二级入口已经移除或并入稳定入口。
2. 如果只是恢复当前工作，不要顺着 docs/ 目录逐个打开，先看 project-context/ 下的稳定入口。
3. docs/domain/ 保存长期业务方向知识；docs/fde/ 保存沟通与梳理方法；docs/frontend/ 保存前端 handoff；P1/P2 历史阶段材料已迁入 docs/history/。
```

## 目录结构

```text
docs/
├── README.md
├── wiki-index.md
├── ai/
│   ├── README.md
│   └── codex-skill-workflow.md
├── change-notes/
├── domain/
├── development/
├── fde/
├── frontend/
├── history/
├── maintenance/
├── overview/
│   └── team-technical-briefing.md
├── architecture/
│   ├── architecture.md
│   ├── system-function.md
│   ├── modules.md
│   ├── events.md
│   ├── data-integration.md
│   └── orchestration-design.md
├── model/
│   ├── domain-model.md
│   ├── data-model.md
│   ├── data-model-validation.md
│   └── glossary.md
├── workflow/
│   ├── task-workflow-matrix.md
│   ├── background-job-matrix.md
│   ├── checklists/
│   ├── raw/
│   │   └── total-workflow.pdf
│   └── flows/
├── api/
│   └── raw/
├── references/
│   └── raw/
└── decisions/
```

## 各目录用途

| 目录 | 用途 |
|---|---|
| `ai/` | AI / agent 共用入口和 skill 工作流说明 |
| `development/` | 仓库级本地启动、迁移、seed、联调环境说明 |
| `domain/` | 长期业务方向知识和领域事实 |
| `fde/` | FDE 工作方式、访谈模板和文档沉淀方法 |
| `frontend/` | 前端页面构建、联调与展示 handoff |
| `history/` | 历史阶段计划、runbook 和拆解材料，仅作证据 |
| `maintenance/` | 文档治理和知识库维护说明 |
| `overview/` | 给团队说明项目目标、系统架构、核心对象和关键流转 |
| `architecture/` | 系统架构、模块边界、事件、编排器设计 |
| `model/` | 领域模型、数据模型、模型核对和术语表 |
| `workflow/` | 农事项流程、后台任务、流程图来源和流程拆解 |
| `api/` | 外部算法接口、后续 OpenAPI / API contract |
| `decisions/` | 设计决策记录 |
| `change-notes/` | 已完成工作项的可读变更摘要 |

## API 文档入口

| 文档 | 用途 |
|---|---|
| `api/frontend-plant-protection-api-contract.md` | 植保链路前端联调 contract |
| `api/weed_diagnosis_api.md` | 杂草诊断算法接口 |
| `api/growth_stage_gdd_api.md` | 生育期 / GDD 算法接口，用于 Stage Orchestrator 初始化和阶段状态管理 |
| `api/pestDisease_survey_window_api.md` | 病虫害调查窗口算法接口当前版，用于初始化常规调查计划和每日更新调查事件 |
| `api/raw/weather_api.pdf` | 气象数据接口原始文档；开发入口应优先使用 markdown contract |

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
6. 新增业务方向长期知识：放入 domain/。
7. 新增 FDE 工作方式或访谈模板：放入 fde/。
8. 新增前端联调和页面构建 handoff：放入 frontend/。
9. 完成功能需求开发、重要修复或联调收口后，按影响范围回写对应正式文档，不把重要结论只留在代码或 current-memory。
10. 一个工作项已经完成且需要保留可读演进摘要：放入 change-notes/。
11. 文档整理、归档和合并建议：先更新 maintenance/docs-hygiene-plan.md，不直接删除历史材料。
```
