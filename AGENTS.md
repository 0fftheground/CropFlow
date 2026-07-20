# AGENTS.md

本文件用于指导 Codex 或其他 AI 编程助手开发 CropFlow 项目。

## Session 启动方式

新的 session 不应默认从头扫整个仓库。推荐按以下顺序恢复上下文：

```text
1. AGENTS.md
2. docs/ai/README.md
3. project-context/entrypoints.md
4. project-context/development-plan.md
5. project-context/current-memory.md
6. 当前 phase 对应文档
7. 与当前任务直接相关的 docs/ 或代码文件
```

原则：

```text
1. 稳定入口放在 project-context/ 和 docs/ 正式文档中。
2. current-memory 只记录当前 phase 的压缩状态，不重复维护完整 backlog。
3. 已完成且对后续无影响的历史讨论，不继续保留在 current-memory。
4. current-memory 只写结论、现状、阻塞和下一步，不写长推理过程。
5. docs/ai/README.md 是 Codex 和 Claude Code 的共享入口，只做索引和通用规则，不复制完整项目事实。
```

## Before Coding

开始编码前，默认执行以下检查：

```text
1. 先读 AGENTS.md。
2. 需要恢复当前状态时，优先读 project-context/current-memory.md；它是当前仓库里 current-state 类信息的主入口。
3. 开始任何非简单任务前，先判断应该使用哪个 skill；不确定时先用 using-agent-skills。
4. 非简单任务在写代码前，先给出简短计划：至少说明当前理解、影响范围、实现取舍和验证方式。
```

## Agent Skills 通用规则

当前环境已安装一组通用 agent-skills，位于 `C:\Users\00778807\.codex\skills\`。这些 skill 不是参考资料，而是带步骤、验证和退出条件的工作流。

使用这些 skill 时，遵循以下原则：

```text
1. 先判断当前任务所处阶段，再加载对应 skill，不要一次把所有 skill 都塞进上下文。
2. using-agent-skills 是元 skill；当你不知道该用哪个 skill 时，先用它做路由。
3. skill 是流程，不是建议；一旦决定使用，就应按其步骤执行，不跳过验证。
4. 一个任务可以串联多个 skill，但应按阶段逐步加载，而不是一次全部加载。
5. 如果任务已经有 CropFlow 专用 skill，就优先使用 CropFlow 专用 skill；通用 skill 作为补充，而不是替代。
```

推荐的通用默认路由：

```text
unclear requirement -> spec-driven-development
large task -> planning-and-task-breakdown
multi-file change -> incremental-implementation
behavior change -> test-driven-development
framework/library uncertainty -> source-driven-development
test/build/runtime failure -> debugging-and-error-recovery
before merge/final answer -> code-review-and-quality
```

结合 CropFlow 当前仓库，推荐这样组合：

```text
1. 恢复今天工作上下文：cropflow-start-work；如还不清楚要做什么，再补 using-agent-skills。
2. 非简单需求先收口业务影响：cropflow-task-planning；如任务仍然很大，再补 planning-and-task-breakdown。
3. 多文件实现时：incremental-implementation。
4. 任何行为变化、bug 修复、边界条件修正：test-driven-development。
5. 外部框架、第三方接口、库行为不确定：source-driven-development。
6. 测试失败、构建失败、线上/本地报错排查：debugging-and-error-recovery。
7. 单个任务完成收口：cropflow-task-closing；提交前再走 code-review-and-quality。
8. 当天收尾、handoff、memory 更新：cropflow-wrap-up。
9. 文档漂移、索引缺口、wiki 清理：cropflow-wiki-maintenance。
```

一个完整但不强制的典型顺序：

```text
cropflow-start-work
-> spec-driven-development（需求不清时）
-> cropflow-task-planning
-> planning-and-task-breakdown（任务过大时）
-> incremental-implementation
-> test-driven-development
-> debugging-and-error-recovery（遇到异常时插入）
-> cropflow-task-closing
-> code-review-and-quality
-> cropflow-wrap-up
```

推荐优先使用以下 skill：

```text
1. 开始新一天或恢复上下文时，优先使用 $cropflow-start-work。
2. 开始非简单功能、复杂 bug、重构或业务规则变更前，优先使用 $cropflow-task-planning。
3. 单个任务完成后需要收口测试、文档、change-note 或 ADR 时，优先使用 $cropflow-task-closing。
4. 结束当天工作、更新 memory 或准备 handoff / 提交时，优先使用 $cropflow-wrap-up。
5. 定期整理 wiki、排查文档漂移和缺口时，优先使用 $cropflow-wiki-maintenance。
6. 很小的实现任务不必机械调用 skill；但涉及 session 恢复、复杂任务规划、任务收尾或 wiki 整理时，优先走对应 skill。
```

仓库内镜像定义位置：

```text
skills/cropflow-start-work/SKILL.md
skills/cropflow-task-planning/SKILL.md
skills/cropflow-task-closing/SKILL.md
skills/cropflow-wrap-up/SKILL.md
skills/cropflow-wiki-maintenance/SKILL.md
```

推荐触发方式：

```text
Use $cropflow-start-work to restore current CropFlow progress
Use $cropflow-task-planning to analyze a non-trivial CropFlow change before editing code
Use $cropflow-task-closing to close one completed CropFlow task with tests and doc updates
Use $cropflow-wrap-up to summarize today, update memory, and prepare commit actions
Use $cropflow-wiki-maintenance to audit CropFlow docs for drift, gaps, and overlap
Use using-agent-skills when you need to discover which general engineering workflow skill applies
Use spec-driven-development when the requirement is still unclear or acceptance criteria are missing
Use planning-and-task-breakdown when the task is too large to start directly
Use incremental-implementation for multi-file implementation work
Use test-driven-development when changing behavior or fixing bugs
Use source-driven-development when framework or library behavior must be verified against sources
Use debugging-and-error-recovery when tests, build, runtime, or logs reveal an unexpected failure
Use code-review-and-quality before merge or before claiming work is complete
```

## 项目背景

CropFlow 是一个作物种植计划的 Plan-level MVP 编排系统。系统围绕单个种植计划运行，支持：

```text
计划创建
生育期预测与更新
预备农事项生成
正式任务生成
运行期事件触发
作业方案生成
执行反馈
人工复核
后续任务或方案调整
```

## 当前 MVP 范围

只做：

```text
单个 PlantingPlan 内部的编排与执行闭环
```

暂不做：

```text
多农场多计划全局调度
跨计划设备资源排程
复杂审批流
独立 Recommendation Entity
完整规则后台配置系统
```

## 必须遵守的核心设计

```text
1. 不要引入独立 Recommendation Entity。
2. 农艺建议、推荐原因、方案依据分别放到 TaskIntent / FarmingTask / OperationPlan。
3. CalendarItem 是预备农事项，不是正式任务。
4. FarmingTask 是正式任务，是 Execution Module 的入口。
5. OperationPlan 是具体作业方案 / 处方方案。
6. Execution Module 只消费 FarmingTask + OperationPlan。
7. Feedback 不能直接生成 FarmingTask，必须回到 Plan Orchestrator。
8. ReviewRequestResolved 不能直接绕过编排器，必须回到 Plan Orchestrator。
9. 外部执行系统是独立外部系统，不属于系统输入。
10. HW 主动回调进入 Execution Module；轮询兜底由 ExecutionStatusPollingJob 查询 HW。
11. 药剂和肥料库存使用 InventoryItem / InventoryTransaction，不只放在 EventRecord。
12. MVP 第一版不把 TaskGenerationPlan 作为核心对象或独立表；任务生成由 TaskDueCheckJob / TaskGenerationService 根据 CalendarItem 完成。
13. Agent Runtime 不拥有 PlantingPlan / FarmingTask / ReviewRequest 权威状态；它只保存会话、运行、工具调用、批准、事件和审计。
14. 模型只能提出 Action Proposal；所有业务写动作必须经过 Available Action Resolver、PreAction，当前高风险动作还必须人工批准。
15. Agent 批准后必须重新读取最新业务状态并再次 PreAction，不能用批准前快照直接执行。
```

## 模块边界

```text
Plan Module：计划基础操作。
Plan Orchestrator：计划级总编排。
Stage Orchestrator：生育期预测、积温、生育期状态。
Runtime Rule Engine：运行期规则判断。
Task Module：CalendarItem / TaskIntent / FarmingTask / OperationPlan。
Material & Inventory Module：InventoryItem / InventoryTransaction。
Execution Module：Execution / ExecutionRecord / DeviceCommand。
Evaluation & Feedback Module：Evaluation / Feedback。
Review Module：ReviewRequest / SystemNotification。
Event Module：事件接入、标准化、记录。
Background Job Center：周期性发现变化，生成 Input Event。
Business Agent Runtime：构建模型上下文、约束动作、处理批准、回注结果和记录审计；业务副作用仍通过既有 Service / Orchestrator。
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

## 命名规则

建议沿用以下概念名，不要随意替换：

```text
PlantingPlan
CropStageState
CropThermalTimeState
StagePredictionSnapshot
CalendarItem
TaskIntent
FarmingTask
OperationPlan
InventoryItem
InventoryTransaction
Execution
ExecutionRecord
DeviceCommand
Evaluation
Feedback
ReviewRequest
SystemNotification
PlanOrchestrator
StageOrchestrator
RuntimeRuleEngine
TaskModule
MaterialInventoryModule
ExecutionModule
```

## 文档优先级

开发前优先阅读：

```text
docs/ai/README.md
docs/wiki-index.md
project-context/entrypoints.md
project-context/development-plan.md
project-context/current-memory.md
docs/README.md
docs/architecture/system-function.md
docs/architecture/architecture.md
docs/domain/README.md
docs/model/domain-model.md
docs/model/data-model.md
docs/model/data-model-validation.md
docs/workflow/task-workflow-matrix.md
docs/workflow/background-job-matrix.md
docs/fde/README.md
docs/change-notes/
docs/architecture/modules.md
docs/architecture/events.md
docs/architecture/orchestration-design.md
```

涉及流程时阅读：

```text
docs/workflow/flows/
```

涉及设计取舍时阅读：

```text
docs/decisions/
```

## 修改代码时的要求

每次修改后应尽量做到：

```text
1. 保持模块边界清楚。
2. 不把编排逻辑散落到 Entity 或 Repository 中。
3. 不让 Task Module 直接处理外部硬件执行。
4. 不让 Execution Module 反向创建业务任务。
5. 不让 Feedback 直接跳过 Plan Orchestrator。
6. 不新增与现有核心对象语义重复的对象。
7. 如新增核心对象、流程或长期规则，先更新 docs/ 中对应事实源。
8. 完成功能需求开发、重要修复或联调收口后，必须按影响范围同步更新项目知识文档。
9. 如形成长期设计取舍或冻结口径，同步补充 docs/decisions/。
10. 如一个已完成工作项值得后续回看影响范围，同步补充 docs/change-notes/。
```

## 非简单任务的处理要求

对于非简单功能、复杂 bug、重构或明显会影响业务逻辑的改动，不应直接盲改代码。

```text
1. 先恢复当前 phase 和相关文档上下文。
2. 先给出简短计划，再进入实现。
3. 先识别受影响的对象、流程、接口、任务链路和测试范围。
4. 如需求存在多种实现路径或业务口径未冻结，先向用户说明当前理解、实现取舍和验证方式。
5. 在没有把影响范围说清楚前，不把复杂改动伪装成“小修小补”直接落代码。
```

## 功能完成后的知识回写要求

为满足 LLM wiki 的核心目标，功能完成后不能只停留在代码、commit 或 current-memory。

```text
1. 对象、字段、状态变化：更新 docs/model/。
2. 模块职责、边界变化：更新 docs/architecture/。
3. workflow、job、事件链路变化：更新 docs/workflow/。
4. API 请求、响应、字段口径变化：更新 docs/api/。
5. 长期业务方向知识变化：更新 docs/domain/。
6. 前端页面构建、展示、联调口径变化：更新 docs/frontend/。
7. FDE 方法、访谈模板或知识沉淀策略变化：更新 docs/fde/。
8. 形成长期设计取舍：更新 docs/decisions/。
9. 一个工作项已经完成且需要保留可读演进摘要：更新 docs/change-notes/。
10. 不把重要结论只留在 current-memory、聊天记录、PR 描述或 commit message 中。
```

## 通用编码行为要求

这些要求用于减少常见 AI 编码错误。对很小的任务可以按实际情况简化，但不应违背项目核心设计。

### 1. 编码前先明确问题

```text
1. 不要隐藏不确定性。
2. 如果存在多种理解，先说明取舍。
3. 如果更简单的方案足够，应优先选择简单方案。
4. 如果需求关键点不清楚，应先指出不清楚的地方。
```

### 2. 优先保持简单

```text
1. 不做用户没有要求的功能。
2. 不为单次使用代码提前抽象。
3. 不引入没有明确需求的灵活性或配置项。
4. 不为不可能出现的场景堆叠错误处理。
5. 如果实现明显过度复杂，应先简化。
```

### 3. 修改保持外科手术式

```text
1. 只修改完成当前目标必须修改的内容。
2. 不顺手重构无关代码。
3. 不顺手调整无关格式、注释或命名。
4. 匹配现有风格，即使存在个人偏好的其他写法。
5. 发现无关死代码时可以说明，但不要擅自删除。
6. 只清理本次修改引入的未使用导入、变量、函数或文件。
```

### 4. 以可验证目标推进

```text
1. 修复 bug 时，优先明确如何复现和验证。
2. 新增校验时，优先明确有效和无效输入的检查方式。
3. 重构时，优先保证重构前后行为一致。
4. 多步骤任务应给出简短计划，并说明每步如何验证。
5. 修改完成后必须给出与变更范围匹配的验证证据；不能因为“改动看起来很小”就跳过测试。
```

## Never

以下行为默认禁止，除非用户明确要求，或它本身就是本次变更的必要组成部分：

```text
1. 不做无关重构。
2. 不因为“改动很简单”就跳过测试、构建或必要的手工验证。
3. 不在未说明 migration 影响、回滚路径和数据兼容性的情况下修改数据库 schema。
4. 不删除旧代码或旧注释；如果确需删除，必须说明原因。仅可顺手清理本次改动直接引入的无用内容。
5. 不在没有测试 / 构建 / 手工验证证据的情况下宣称任务完成。
```

## 本地运行与验证环境

```text
1. 跑测试、脚本和本地 FastAPI 接口时，默认使用工程内虚拟环境 `F:\workspace\CropFlow\.venv`。
2. 优先显式调用 `.venv\Scripts\python.exe`，例如 `.venv\Scripts\python.exe -m pytest`、`.venv\Scripts\python.exe -m uvicorn`。
3. 不要混用系统 Python、外部 Conda 环境或未绑定到本仓库 `.venv` 的解释器。
4. 如果当前 shell 没有激活 `.venv`，也应通过显式解释器路径执行命令，而不是继续使用外部环境。
```

## Headroom MCP 使用规则

当当前 session 提供 Headroom MCP 且任务涉及大文件、长日志、多文件分析、RAG 检索结果、数据库查询结果、测试输出或长上下文时，优先使用 Headroom MCP。

### 必须调用 `headroom_compress` 的情况

```text
1. 单个文件超过约 300 行。
2. 日志、traceback、测试输出超过约 100 行。
3. 一次需要阅读 5 个以上文件。
4. 搜索结果、grep 结果、RAG chunks 很多。
5. JSON、CSV、Markdown、SQL dump 等结构化文本很长。
6. 用户要求分析“大文件 / 多文件 / 长上下文 / 整个项目 / 全量日志”。
```

### 使用流程

```text
1. 先调用 `headroom_compress` 压缩大上下文。
2. 基于压缩结果判断是否足够回答。
3. 如果需要具体证据、行号、字段、函数实现、异常栈、配置值，必须调用 `headroom_retrieve` 获取原文片段。
4. 不要只凭压缩摘要修改关键代码。
5. 修改代码前，应 retrieve 相关原文或直接读取关键文件。
6. 任务完成后调用 `headroom_stats`，汇报压缩次数、retrieve 次数、节省 token 和是否有风险。
```

### 禁止滥用

```text
1. 不要对很短的文件或简单问题调用 Headroom。
2. 不要把压缩摘要当成完整事实。
3. 不要基于压缩摘要做数据库迁移、删除文件、修改生产配置。
4. 涉及 schema、SQL、配置、diff、正则、错误栈时，必须查看原文。
5. 如果当前 session 没有提供 Headroom MCP，则回退到常规文件读取、搜索和定点取证，不要在回答里假设这些工具存在。
```

## 当前技术栈

当前已确认的基础口径：

```text
后端：Python + FastAPI
数据库：PostgreSQL
部署：Docker
前端：由前端负责人确定，但需遵循统一 API contract
```
