# CropFlow Session Entrypoints

本文件用于提供仓库级稳定入口，帮助新的 Codex session 快速恢复工作上下文。

## 新 Session 启动顺序

```text
1. 优先显式调用 $cropflow-start-work
2. AGENTS.md
3. project-context/entrypoints.md
4. project-context/development-plan.md
5. project-context/current-memory.md
6. 当前 phase 对应文档
7. 与当前任务直接相关的 docs/ 或代码文件
```

原则：

```text
1. 不为进入新 session 默认重读整个 docs/ 目录。
2. 先读稳定入口和当前 phase 状态，再按任务定向补读。
3. 只有当 current-memory 无法支撑当前任务时，才回源到更细的设计文档。
```

## Skill 入口

推荐在 session 级动作时优先显式调用 skill，而不是只靠自然语言让 agent 猜测：

```text
$cropflow-start-work
  用途：恢复当前 phase、检查 git 状态、总结当前进展、建议下一步。
  推荐说法：Use $cropflow-start-work to restore current CropFlow progress

$cropflow-wrap-up
  用途：扫尾当天工作、更新 current-memory、生成 commit message，并在明确要求时 commit / push。
  推荐说法：Use $cropflow-wrap-up to summarize today, update memory, and prepare commit actions
```

## 全局上下文文件说明

| 文件 | 作用 |
|---|---|
| `project-context/development-plan.md` | 全局开发计划、phase 划分、阶段状态 |
| `project-context/current-memory.md` | 当前 phase 的压缩进展快照 |
| `project-context/phases/` | 每个 phase 的目标、范围、验收标准和关键任务 |

## 按任务类型的文档入口

### 架构 / 核心边界

适用场景：

```text
1. 判断某个改动是否越过模块边界。
2. 确认某类事件、编排节点或模块职责应该落在哪里。
3. 需要核对长期稳定的核心设计约束。
```

阅读收益：

```text
1. 明确 Plan / Stage / Task / Execution / Review 等模块的职责分工。
2. 明确关键事件流转、编排回路和禁止绕过的边界。
3. 明确哪些设计结论已经在 decisions 中冻结。
```

```text
docs/architecture/system-function.md
docs/architecture/architecture.md
docs/architecture/modules.md
docs/architecture/events.md
docs/architecture/orchestration-design.md
docs/decisions/
```

简要说明：

```text
docs/architecture/system-function.md
  适合先读，快速理解系统要做什么、主链路是什么、各模块承担什么能力。

docs/architecture/architecture.md
  适合在需要整体视角时读，帮助判断当前任务位于全局架构的哪一层。

docs/architecture/modules.md
  适合判断“这个逻辑该放哪个模块”，尤其对新增实现或重构最有用。

docs/architecture/events.md
  适合处理事件接入、事件命名、事件来源和事件驱动链路。

docs/architecture/orchestration-design.md
  适合处理 Plan Orchestrator、Stage Orchestrator、回编排逻辑和状态推进。

docs/decisions/
  适合在出现设计分歧时回看，确认哪些方案已经明确做或明确不做。
```

### 领域模型 / 表结构 / 状态

适用场景：

```text
1. 新增或调整对象字段、状态、关系。
2. 将业务流程映射到数据对象和表结构。
3. 判断某个字段应结构化还是先放 JSON 承接字段。
```

阅读收益：

```text
1. 明确核心对象语义、字段草案、状态枚举和关系模型。
2. 明确哪些字段已核对完成，哪些仍是待确认项。
3. 明确现有 SQL 草案已经落到了什么程度。
```

```text
docs/model/domain-model.md
docs/model/data-model.md
docs/model/data-model-validation.md
docs/model/glossary.md
database/sql/
```

简要说明：

```text
docs/model/domain-model.md
  适合理解对象之间的大语义关系，不关心字段细节时先读它。

docs/model/data-model.md
  适合处理字段、状态、对象关系，是建模和落库时的主参考。

docs/model/data-model-validation.md
  适合确认哪些字段和流程已经被业务、算法或前端核对过，哪些还未冻结。

docs/model/glossary.md
  适合快速统一术语，避免把同一概念写成不同名字。

database/sql/
  适合查看当前 DDL 草案、字典和品种数据输入文件，判断实现层准备情况。
```

### 流程 / 后台任务 / 链路

适用场景：

```text
1. 判断某个 workflow、后台 job 或分支规则该如何落地。
2. 分析从计划创建到任务生成、执行、反馈的链路。
3. 核对某一农事项是否已经进入正式矩阵文档。
```

阅读收益：

```text
1. 明确 workflowKey、taskSubtype、依赖关系和上下游动作。
2. 明确后台 job 的触发时机、输入、输出和兜底逻辑。
3. 明确某条流程目前处于“已冻结”“待同步”还是“待设计”。
```

```text
docs/workflow/task-workflow-matrix.md
docs/workflow/background-job-matrix.md
docs/workflow/flows/
```

简要说明：

```text
docs/workflow/task-workflow-matrix.md
  适合看农事项定义、上下游依赖、流程分支和对象落点。

docs/workflow/background-job-matrix.md
  适合看定时任务、轮询任务、日期维护、气象刷新等后台触发逻辑。

docs/workflow/flows/
  适合看比矩阵更细的链路拆解，用于讨论具体步骤和时序。
```

### 团队分工 / 当前阶段交付物

适用场景：

```text
1. 判断当前 phase 要交什么，而不是要实现什么未来理想形态。
2. 确认某个方向该提交哪些表、样例、字段草案或页面材料。
3. 判断当前阶段还缺哪些非代码交付物。
```

阅读收益：

```text
1. 明确当前 phase 的目标、已确认项、待产出项和完成判定。
2. 明确各方向的职责边界、交付模板和当前优先级。
3. 明确样板闭环当前已推进到哪，后续应该先补什么。
```

```text
docs/planning/development-roadmap.md
docs/planning/team-work-division.md
docs/planning/team-work-division/
docs/planning/P1/
```

简要说明：

```text
docs/planning/development-roadmap.md
  适合快速判断当前处于哪个阶段、下一阶段进入条件是什么。

docs/planning/team-work-division.md
  适合看全局分工原则、统一提交模板和通用职责边界。

docs/planning/team-work-division/
  适合按具体角色或方向定向阅读，不必每次看完整总文档。
  建议按当前任务直接进入对应子文档：
  - 范围冻结、规则拍板、跨方向收口：product-architecture-owner.md
  - 核心对象、API contract、编排骨架：core-backend.md
  - 业务方向细节：calendar-stage.md / plant-protection.md / irrigation.md / fertilization.md / remote-sensing.md
  - 页面范围和联调：frontend.md / frontend-plant-protection-handoff.md

docs/planning/P1/
  适合回看杂草样板闭环的历史收口材料和业务语义。
  建议先读 todo-list.md 了解已确认项和剩余事项；只有在需要逐项核对业务链路时，再读 植保清单.md。
```

### 算法接口 / 契约

适用场景：

```text
1. 需要核对请求字段、响应字段、分支返回或命名规范。
2. 需要把算法输出映射到 CalendarItem、OperationPlan、ExecutionRecord 等对象。
3. 需要判断当前接口契约和 workflow / data model 是否一致。
```

阅读收益：

```text
1. 明确每个接口的输入、输出、分支结构和异常处理口径。
2. 明确哪些字段来自算法原文档，哪些是系统内派生字段。
3. 明确当前仍需同步回模型和流程文档的接口变化。
```

```text
docs/api/
```

简要说明：

```text
docs/api/
  适合查看外部算法接口原始契约和项目内整理后的 Markdown 契约。
  如果当前任务与植保杂草主线有关，优先看 docs/api/weed_diagnosis_api.md。
  如果当前任务与生育期编排或 Stage Orchestrator 有关，优先看 docs/api/growth_stage_prediction_api.md。
  如果当前任务与 P3 病虫害调查扩展有关，优先看 docs/api/pestDisease_survey_window_api.md 和 docs/api/weather_api.pdf。
```

## 更新规则

```text
1. 更新长期阶段计划时，优先修改 project-context/development-plan.md 或对应 phase 文档。
2. 更新当前推进状态时，只修改 project-context/current-memory.md。
3. 不把完整 backlog、长推理过程或已无后续影响的历史讨论写进 current-memory。
4. 如核心对象、流程或约束发生变化，仍需回写 docs/ 中的正式设计文档。
```
