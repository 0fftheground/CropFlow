# AI Shared Context

本目录是 Codex 和 Claude Code 共用的项目上下文入口。

原则：这里不复制完整业务事实，只维护读取顺序、文档索引和跨工具通用规则。项目事实仍以 `project-context/` 和 `docs/` 下的正式文档为准。

## 启动读取顺序

新 session 不应默认扫描整个仓库。优先按以下顺序恢复上下文：

```text
1. 当前工具入口：AGENTS.md 或 CLAUDE.md
2. docs/ai/README.md
3. project-context/entrypoints.md
4. project-context/development-plan.md
5. project-context/current-memory.md
6. 当前 phase 对应文档，例如 project-context/phases/phase-2-core-implementation.md
7. 与当前任务直接相关的 docs/ 或代码文件
```

## 核心项目文档

稳定入口：

```text
project-context/entrypoints.md
project-context/development-plan.md
project-context/current-memory.md
project-context/phases/phase-2-core-implementation.md
```

正式文档索引：

```text
docs/README.md
docs/architecture/system-function.md
docs/architecture/architecture.md
docs/architecture/modules.md
docs/architecture/events.md
docs/architecture/orchestration-design.md
docs/model/domain-model.md
docs/model/data-model.md
docs/model/data-model-validation.md
docs/model/glossary.md
docs/workflow/task-workflow-matrix.md
docs/workflow/background-job-matrix.md
docs/workflow/flows/
docs/decisions/
docs/planning/development-roadmap.md
docs/planning/team-work-division.md
docs/planning/guides/agent-development-guidelines.md
```

## 工具入口职责

`AGENTS.md` 用于 Codex 专用约束，例如 skill 使用、会话恢复和代码修改行为。

`CLAUDE.md` 用于 Claude Code 专用约束，只做薄入口，不维护第二份项目事实。

两者都应指向本文件，并避免重复维护架构、数据模型、流程矩阵和当前进度。

## 文档维护规则

```text
1. 新增或修改核心对象、模块边界、流程时，优先更新 docs/ 下的正式文档。
2. 当前阶段进度、阻塞和下一步只更新 project-context/current-memory.md。
3. 本文件只在入口顺序、共享索引或跨工具规则变化时更新。
4. 不在本文件复制长篇架构说明，避免与正式文档漂移。
```

## 当前项目硬约束摘要

以下只是提醒，完整定义以正式文档为准：

```text
1. CropFlow 是 Plan-level MVP 编排系统。
2. 当前只做单个 PlantingPlan 内部闭环。
3. 不引入独立 Recommendation Entity。
4. CalendarItem 是预备农事项，FarmingTask 是正式任务。
5. Execution Module 只消费 FarmingTask + OperationPlan。
6. Feedback 和 ReviewRequestResolved 必须回到 Plan Orchestrator。
7. 外部执行系统不属于系统输入，HW 回调进入 Execution Module。
```
