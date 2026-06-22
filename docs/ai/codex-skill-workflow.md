# Codex Skill Workflow

本文件用于说明 CropFlow 仓库中 Codex / Claude Code 的推荐工作流，以及各个 skill 在什么阶段使用。

目标：

```text
1. 让 AI 的工作方式成为仓库资产，而不是只存在于对话里。
2. 让 session 恢复、任务规划、任务收尾、当天 handoff 和 wiki 整理各自有清晰职责。
3. 避免把不同阶段的动作都混进同一个 skill。
```

## 1. 基本原则

```text
1. 对话只承担当前任务推理和执行，不承担长期项目记忆。
2. 长期知识回写到 docs/、docs/decisions/、docs/change-notes/。
3. current-memory 只保存当前 phase 的压缩状态。
4. skill 是工作流入口，不是替代正式文档。
5. 复杂任务先分析再改代码；完成后回写知识；当天结束再做 handoff。
```

## 2. 五个 skill 的职责边界

### 2.1 `$cropflow-start-work`

适用时机：

```text
1. 新一天开始开发。
2. 新 session 恢复上下文。
3. 需要先判断当前 phase、最近变更和下一步任务。
```

主要职责：

```text
1. 读取 AGENTS.md、docs/ai/README.md、entrypoints、development-plan、current-memory。
2. 查看 git 当前状态。
3. 回顾最近仍然相关的 change-notes。
4. 输出当前阶段、当前目标、最近完成、下一步建议。
```

不负责：

```text
1. 不直接改代码。
2. 不替代任务级方案分析。
3. 不替代任务完成后的测试和文档收尾。
```

### 2.2 `$cropflow-task-planning`

适用时机：

```text
1. 非简单功能。
2. 复杂 bug。
3. 重构。
4. 业务规则变化。
5. 任何会明显影响对象、流程、API、job、测试或文档的任务。
```

主要职责：

```text
1. 恢复最小必要上下文。
2. 识别受影响的对象、流程、接口、前后端和数据层。
3. 分析影响范围、验证路径和文档更新点。
4. 在需要时给出 2-3 种实现取舍。
5. 输出可 review 的实施计划。
```

不负责：

```text
1. 不直接改代码。
2. 不替代当天结束时的 handoff。
```

### 2.3 `$cropflow-task-closing`

适用时机：

```text
1. 单个任务已经完成。
2. 需要收口测试、文档、ADR、change-note。
3. 准备让别人 review 一个明确任务范围。
```

主要职责：

```text
1. 以单个任务为边界检查 final diff。
2. 总结代码变化和业务逻辑变化。
3. 记录已跑测试、未跑测试和人工验证点。
4. 按影响范围更新 docs/model、docs/workflow、docs/api、docs/domain、docs/frontend。
5. 在需要时新增或更新 docs/decisions/ 和 docs/change-notes/。
```

不负责：

```text
1. 不以“整天所有工作”为边界。
2. 不替代 current-memory 的 day-end handoff 更新。
```

### 2.4 `$cropflow-wrap-up`

适用时机：

```text
1. 当天工作结束。
2. 当前 session 要交接。
3. 需要刷新 current-memory。
4. 需要准备 commit message、commit 或 push。
```

主要职责：

```text
1. 汇总今天完成了什么、还剩什么。
2. 更新 project-context/current-memory.md。
3. 明确下个 session 先做什么。
4. 在用户要求时准备 commit / push。
```

关键边界：

```text
1. wrap-up 是“当天 / 当前 session 收尾”，不是“单个任务关闭”。
2. 如果某个任务还没做 task-closing 层面的测试、ADR、change-note，wrap-up 先指出缺口。
3. 如果缺口范围清楚且不大，wrap-up 可以顺手补齐后再完成当天 handoff。
4. 如果任务边界混杂或缺口过大，wrap-up 应明确建议单独走 task-closing，而不是假装已经完成。
```

### 2.5 `$cropflow-wiki-maintenance`

适用时机：

```text
1. 每完成几项任务后做一次文档巡检。
2. 某个 phase 结束后做一次 wiki 整理。
3. 怀疑 docs 已经过时、重复、缺少入口或与代码漂移时。
```

主要职责：

```text
1. 审查 docs 是否与当前代码和流程一致。
2. 查找缺失的 decisions / change-notes / workflow 文档。
3. 修复低风险 stale link 和索引问题。
4. 对高风险清理动作先输出方案，不直接删历史文档。
```

## 3. 推荐工作流

### 3.1 新一天 / 新 session

```text
$cropflow-start-work
  ↓
确认当前 phase、最近变更、下一步
```

### 3.2 开始复杂任务

```text
$cropflow-task-planning
  ↓
识别影响范围、实现取舍、测试计划、文档更新点
  ↓
再进入代码修改
```

### 3.3 单个任务完成

```text
代码和测试基本完成
  ↓
$cropflow-task-closing
  ↓
补测试结果、docs、ADR、change-note、review checklist
```

### 3.4 当天工作结束

```text
$cropflow-wrap-up
  ↓
更新 current-memory
  ↓
形成下次可恢复的 handoff
```

### 3.5 周期性文档整理

```text
$cropflow-wiki-maintenance
  ↓
检查 docs 漂移、缺口、重复、坏链接
```

## 4. skill 与正式文档的关系

```text
1. skill 定义保存在仓库 skills/ 中，作为团队可审查的 workflow 资产。
2. Codex 真正可直接调用的 skill 需要安装到 ~/.codex/skills。
3. 仓库中的 skills/ 和本地 ~/.codex/skills 应尽量保持语义一致。
4. skill 只说明“怎么工作”，不替代 docs/ 中的系统事实源。
```

## 5. 哪些文档要一起看

与 skill 工作流一起使用的主要文档：

```text
AGENTS.md
CLAUDE.md
docs/ai/README.md
project-context/entrypoints.md
project-context/development-plan.md
project-context/current-memory.md
docs/wiki-index.md
skills/README.md
```

## 6. 典型说法

```text
Use $cropflow-start-work to restore current CropFlow progress
Use $cropflow-task-planning to analyze a non-trivial CropFlow change before editing code
Use $cropflow-task-closing to close one completed CropFlow task with tests and doc updates
Use $cropflow-wrap-up to summarize today, update memory, and prepare commit actions
Use $cropflow-wiki-maintenance to audit CropFlow docs for drift, gaps, and overlap
```
