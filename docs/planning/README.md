# CropFlow Planning Docs

`docs/planning/` 只保留规划、协作和阶段实现相关文档。

建议结构：

```text
1. 顶层只放长期稳定的总纲文档。
2. 执行规范放到 guides/。
3. 业务方向接入材料放到 directions/。
4. 阶段性材料按 P1 / P2 归档。
```

## 当前目录说明

| 路径 | 用途 |
|---|---|
| `docs/planning/development-roadmap.md` | 正式推进里程碑和阶段目标 |
| `docs/planning/team-work-division.md` | 通用分工原则和统一提交模板 |
| `docs/planning/guides/` | AI agent 规范、FDE 标准流程、农事项接入访谈指南和文档整理计划 |
| `docs/planning/directions/` | FDE 沉淀的业务方向接入材料 |
| `docs/planning/archive/` | 已完成阶段的历史计划、runbook 和 migration 拆分材料 |
| `docs/planning/team-work-division/` | 按角色拆分的协作边界和前端 handoff |

## 使用建议

```text
1. 恢复上下文时，先看 project-context/entrypoints.md，不要从 planning/ 逐个扫起。
2. 只需要阶段目标时，看 development-roadmap.md。
3. 只需要统一协作规则时，看 team-work-division.md 和 guides/；了解 FDE 标准流程时，看 `docs/planning/guides/fde-standard-workflow.md`；FDE 访谈并沉淀新方向农事项接入材料时，看 `docs/planning/guides/agri-task-integration-doc-requirements.md`；整理文档体系时，看 `docs/planning/guides/docs-hygiene-plan.md`。
4. 只需要回看业务方向材料或样板任务清单时，进入 directions/。
5. 只需要历史阶段证据时，进入 archive/。
```
