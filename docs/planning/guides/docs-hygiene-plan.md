# Docs Hygiene 整理计划

> 本文档用于在 FDE 工作模式下整理 CropFlow 文档体系。  
> 当前目标是先做非破坏性分层：明确哪些文档是长期事实源，哪些是 FDE 接入产物，哪些应归档，哪些只是原始参考资料。  
> 在归档目录和引用替换没有完成前，不直接删除历史文档。

---

## 1. 整理原则

```text
1. 不用文档数量判断价值，用“是否仍是当前事实源”判断。
2. 长期事实源必须少而稳定，避免同一事实散落在多个文档中。
3. FDE 产物用于接入和访谈，不要求业务方向同事长期维护。
4. 历史阶段材料保留证据价值，但不应出现在默认阅读路径里。
5. 原始厂商资料和算法附件应降级为 raw reference，markdown contract 才作为开发入口。
6. 只删除已经被合并、归档且无引用的文档。
```

## 2. 建议目录分层

```text
docs/
  README.md                         # docs 入口，只保留索引和维护规则
  ai/                               # AI / agent 共享入口
  architecture/                     # 长期架构事实源
  model/                            # 长期模型事实源
  workflow/                         # 长期流程和 job 事实源
  decisions/                        # ADR，长期保留
  api/                              # 当前 markdown API contract
  api/raw/                          # 原始 pdf/docx/txt/xlsx 参考资料，建议后续迁入
  planning/
    README.md
    development-roadmap.md
    guides/                         # FDE / agent / docs hygiene 等工作规范
    directions/                     # FDE 沉淀的业务方向接入材料
    team-work-division/             # 角色协作边界和前端 handoff
    archive/                        # 建议后续放 P1/P2 历史阶段材料
```

## 3. 分类标准

| 分类 | 含义 | 处理方式 |
|---|---|---|
| keep | 当前仍是长期事实源或稳定入口 | 保留并继续维护 |
| fde-active | 当前或后续方向接入会继续使用的 FDE 产物 | 保留，按 FDE 流程更新 |
| merge | 与其他文档职责重叠 | 合并后删除或降级 |
| archive | 阶段历史材料，不再作为默认入口 | 移入 `docs/planning/archive/` 或 phase archive |
| raw-reference | 原始附件或厂商资料 | 移入 `docs/api/raw/` 或 `docs/references/raw/` |
| stale-fix | 有旧路径、旧文件名或旧口径 | 立即修正引用 |
| delete-candidate | 已合并、无引用、无证据价值 | 二次确认后删除 |

## 4. 当前文档分类

### 4.1 仓库上下文

| 文件 | 分类 | 建议 |
|---|---|---|
| `project-context/entrypoints.md` | keep | 新 session 稳定入口，保留 |
| `project-context/development-plan.md` | keep | phase 计划事实源，保留 |
| `project-context/current-memory.md` | keep | 当前 phase 压缩状态，保留 |
| `project-context/phases/phase-0-contract-convergence.md` | keep | phase 级长期范围，保留 |
| `project-context/phases/phase-1-weed-sample-loop.md` | keep | phase 级长期范围，保留 |
| `project-context/phases/phase-2-core-implementation.md` | keep | phase 级长期范围，保留 |
| `project-context/phases/phase-3-expansion.md` | keep | P3 扩展接入事实源，保留 |

### 4.2 稳定事实源

| 文件 | 分类 | 建议 |
|---|---|---|
| `docs/ai/README.md` | keep | AI / agent 共享入口，保留 |
| `docs/overview/team-technical-briefing.md` | keep | 团队总览，保留 |
| `docs/architecture/system-function.md` | keep | 系统能力事实源，保留 |
| `docs/architecture/architecture.md` | keep | 总体架构，保留 |
| `docs/architecture/modules.md` | keep | 模块边界，保留 |
| `docs/architecture/events.md` | keep | 事件边界，保留 |
| `docs/architecture/orchestration-design.md` | keep | 编排器设计，保留 |
| `docs/model/domain-model.md` | keep | 领域对象事实源，保留 |
| `docs/model/data-model.md` | keep | 数据模型事实源，保留 |
| `docs/model/data-model-validation.md` | keep | 模型核对记录，保留 |
| `docs/model/er-diagram.md` | keep | ER 图入口，保留 |
| `docs/model/glossary.md` | keep | 术语表，保留 |
| `docs/workflow/task-workflow-matrix.md` | keep | 农事项 workflow 事实源，保留 |
| `docs/workflow/background-job-matrix.md` | keep | job 事实源，保留 |
| `docs/workflow/flows/plan-creation-initialization.md` | keep | 细流程补充，保留 |
| `docs/workflow/flows/runtime-event-task-update.md` | keep | 细流程补充，保留 |
| `docs/workflow/flows/task-execution-feedback.md` | keep | 细流程补充，保留 |
| `docs/decisions/*.md` | keep | ADR，长期保留 |
| `docs/development/local-dev-runbook.md` | keep | 本地开发入口，保留 |

### 4.3 当前 API contract

| 文件 | 分类 | 建议 |
|---|---|---|
| `docs/api/frontend-plant-protection-api-contract.md` | keep | 当前植保前端 contract，保留 |
| `docs/api/growth_stage_gdd_api.md` | keep | 当前生育期 / GDD contract，保留 |
| `docs/api/pestDisease_survey_window_api.md` | keep | 当前病虫调查 contract，保留 |
| `docs/api/pestDisease_control_window_api.md` | keep | 当前病虫防治 contract，保留 |
| `docs/api/weed_diagnosis_api.md` | keep | 除草算法 contract，保留 |
| `docs/api/weed_diagnosis_api入参组装和返回结果对象构建.md` | keep | 仍被 P2 拆解引用，保留；后续可重命名为英文 |

### 4.4 FDE / 协作规范

| 文件 | 分类 | 建议 |
|---|---|---|
| `docs/planning/guides/fde-standard-workflow.md` | fde-active | FDE 通用 SOP，保留 |
| `docs/planning/guides/agri-task-integration-doc-requirements.md` | fde-active | 农事项专项访谈模板，保留 |
| `docs/planning/guides/agent-development-guidelines.md` | keep | AI agent 开发规范，保留 |
| `docs/planning/archive/non-code-integration-package-template.md` | archive | 旧非代码接入模板已被 FDE 流程替代，保留为历史模板 |
| `docs/planning/team-work-division.md` | keep | 团队分工总纲，保留 |
| `docs/planning/development-roadmap.md` | keep | 对外正式 roadmap，保留 |
| `docs/planning/team-work-division/product-architecture-owner.md` | keep | 角色职责，保留 |
| `docs/planning/team-work-division/core-backend.md` | keep | 角色职责，保留 |
| `docs/planning/team-work-division/frontend.md` | keep | 前端方向总纲，保留 |
| `docs/planning/directions/calendar-stage/overview.md` | fde-active | 方向接入材料，保留 |
| `docs/planning/directions/plant-protection/overview.md` | fde-active | 当前植保方向事实源，保留 |
| `docs/planning/directions/irrigation/overview.md` | fde-active | P3 接入方向材料，保留 |
| `docs/planning/directions/fertilization/overview.md` | fde-active | P3 接入方向材料，保留 |
| `docs/planning/directions/remote-sensing/overview.md` | fde-active | P3 接入方向材料，保留 |
| `docs/planning/team-work-division/frontend-plant-protection-handoff.md` | keep | 当前前端联调 handoff，P2 收尾后可归档 |

### 4.5 阶段历史材料

| 文件 | 分类 | 建议 |
|---|---|---|
| `docs/planning/directions/plant-protection/task-checklist.md` | fde-active | 作为主链路任务清单样板保留，后续可复制结构 |
| `docs/planning/archive/P1/plant-protection-closed-loop-schedule.md` | archive | P1 历史 schedule，已从默认入口移除 |
| `docs/planning/archive/P1/todo-list.md` | archive | P1 历史 todo，已从默认入口移除 |
| `docs/planning/archive/P2/p2-backend-runbook.md` | archive | P2 runbook，已归档 |
| `docs/planning/archive/P2/p2-backend-weed-implementation-breakdown.md` | archive | P2 拆解材料，已归档 |
| `docs/planning/archive/P2/p2-v1-migration-plan.md` | archive | migration 历史计划，已归档 |
| `docs/planning/archive/P2/p2-v1-migration-scope.md` | archive | migration 历史范围，已归档 |

### 4.6 原始资料和附件

| 文件 | 分类 | 建议 |
|---|---|---|
| `docs/api/raw/weather_api.pdf` | raw-reference | 已移入 raw，开发入口应优先使用 markdown contract |
| `docs/api/raw/big_data_weather_api.txt` | raw-reference | 已移入 raw |
| `docs/api/raw/遥感算法接口文档.docx` | raw-reference | 已移入 raw，后续由 FDE 摘成 markdown |
| `docs/references/raw/生育期code_list.xlsx` | raw-reference | 已移入 references raw |
| `docs/workflow/raw/total-workflow.pdf` | raw-reference | 已移入 workflow raw |

## 5. 已发现的 stale 引用

| 位置 | 问题 | 当前处理 |
|---|---|---|
| `docs/README.md` | 推荐阅读顺序曾写 `planning/agent-development-guidelines.md` | 已改为 `planning/guides/agent-development-guidelines.md` |
| `docs/README.md` | API 入口曾写 `growth_stage_prediction_api.md`，实际文件已不存在 | 已改为 `growth_stage_gdd_api.md` |
| `project-context/entrypoints.md` | Stage Orchestrator 入口曾写 `growth_stage_prediction_api.md` | 已改为 `growth_stage_gdd_api.md` |
| `docs/api/growth_stage_gdd_api.md` | 文内提到后续对齐旧 `growth_stage_prediction_api.md` | 保留为历史说明，暂不改 |

## 6. 建议执行顺序

### Step 1：立即修正 stale 引用

```text
1. 修正 docs/README.md 的旧路径。
2. 修正 project-context/entrypoints.md 的旧 API 文件名。
3. 更新 docs/README.md 的 guides 目录说明，把 FDE 和 docs hygiene 纳入入口。
```

### Step 2：建立归档目录但不删除

```text
1. 已新增 docs/planning/archive/P1/。
2. 已新增 docs/planning/archive/P2/。
3. 已将 P1/P2 已完成阶段材料迁入 archive。
4. 已更新 entrypoints 和 README，确保默认路径不再指向历史材料。
```

### Step 3：整理 raw reference

```text
1. 已新增 docs/api/raw/、docs/workflow/raw/、docs/references/raw/。
2. 已移入 pdf/docx/txt/xlsx 原始资料。
3. 已在 raw README 和 docs/README 中声明：raw 只作证据，markdown contract 才是开发入口。
```

### Step 4：合并重叠模板

```text
1. 已对比 non-code-integration-package-template.md 与 FDE 指南。
2. 旧模板内容已由 FDE SOP 和农事项专项访谈指南覆盖。
3. 已将旧模板迁入 docs/planning/archive/，不再作为当前默认入口。
```

### Step 5：二次确认 delete candidates

```text
1. 先用 rg 确认无引用。
2. 再确认无 ADR / 历史证据价值。
3. 最后再删除。
```

## 7. 当前不建议删除的内容

```text
1. docs/decisions/ 下的 ADR：即使旧，也保留设计证据。
2. docs/planning/directions/plant-protection/task-checklist.md：作为 FDE 主链路任务清单样板保留。
3. docs/planning/archive/P2/p2-backend-weed-implementation-breakdown.md：作为 P2 历史拆解材料保留。
4. docs/api/weed_diagnosis_api入参组装和返回结果对象构建.md：虽然文件名不理想，但仍是植保实现依赖。
5. 原始 pdf/docx/xlsx：不应作为开发入口，但在 markdown contract 沉淀前不删除。
```
