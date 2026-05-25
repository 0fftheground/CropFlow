# CLAUDE.md

本文件用于指导 Claude Code 开发 CropFlow 项目。

## 启动方式

Claude Code 开始处理本仓库任务时，先读取共享上下文入口：

```text
1. CLAUDE.md
2. docs/ai/README.md
3. project-context/entrypoints.md
4. project-context/development-plan.md
5. project-context/current-memory.md
6. 当前 phase 对应文档
7. 与当前任务直接相关的 docs/ 或代码文件
```

不要默认从头扫描整个仓库。需要更多上下文时，按 `docs/ai/README.md` 的索引继续读取。

## 文档来源

`CLAUDE.md` 只作为 Claude Code 的薄入口，不维护第二份项目事实。

项目事实来源：

```text
docs/ai/README.md
project-context/
docs/
```

如果这些文档之间存在冲突，优先级为：

```text
1. 用户当前明确指令
2. project-context/current-memory.md
3. 当前 phase 文档
4. docs/ 下正式架构、模型、流程文档
5. 本文件
```

## 开发约束

修改代码时遵守：

```text
1. 保持模块边界清楚。
2. 不把编排逻辑散落到 Entity 或 Repository 中。
3. 不让 Task Module 直接处理外部硬件执行。
4. 不让 Execution Module 反向创建业务任务。
5. 不让 Feedback 直接跳过 Plan Orchestrator。
6. 不新增与现有核心对象语义重复的对象。
7. 如新增核心对象或流程，先更新 docs/。
```

## 核心设计提醒

完整定义以 `docs/ai/README.md` 指向的正式文档为准。这里仅保留高频硬约束：

```text
1. 不要引入独立 Recommendation Entity。
2. 农艺建议、推荐原因、方案依据分别放到 TaskIntent / FarmingTask / OperationPlan。
3. CalendarItem 是预备农事项，不是正式任务。
4. FarmingTask 是正式任务，是 Execution Module 的入口。
5. OperationPlan 是具体作业方案 / 处方方案。
6. ReviewRequestResolved 必须回到 Plan Orchestrator。
```
