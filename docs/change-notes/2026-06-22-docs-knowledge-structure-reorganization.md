# 2026-06-22 Docs Knowledge Structure Reorganization

## Summary

把旧 `planning` 分层拆成面向 LLM wiki 的稳定结构：`domain / fde / frontend / history / maintenance / change-notes`，并清理默认入口中的旧路径。

## Code Changes

- 新增 `docs/domain/`、`docs/fde/`、`docs/frontend/`、`docs/history/`、`docs/maintenance/`、`docs/change-notes/`。
- 把方向知识、FDE 方法、前端 handoff 和历史阶段材料迁移到各自目录。
- 更新 `AGENTS.md`、`docs/ai/README.md`、`docs/README.md`、`docs/wiki-index.md`、`project-context/entrypoints.md` 等入口。

## Business Logic Changes

- `planning` 不再是当前默认知识入口。
- FDE 继续保留，但明确是“系统与业务沟通和沉淀策略”，不是 planning。
- 历史计划、runbook、todo 不进入 `change-notes`，而进入 `docs/history/`。

## Affected Areas

- `AGENTS.md`
- `docs/ai/README.md`
- `docs/README.md`
- `docs/wiki-index.md`
- `project-context/entrypoints.md`
- `docs/maintenance/docs-hygiene-plan.md`

## Tests

文档结构调整，无自动化测试。

## Remaining Assumptions

- 后续每次功能收口后，仍需要持续补 `change-notes` 和 `decisions`，否则新结构会再次失效。
- `docs/history/` 只保留历史证据，不应重新变成当前默认入口。

## Manual Review Checklist

- 确认共享入口不再引用旧 `docs/planning/...` 路径。
- 确认方向知识、FDE、前端 handoff 和历史材料各自有单独目录。
- 确认 `change-notes` 与 `history` 的边界没有混淆。

## Related Documents

- `docs/maintenance/docs-hygiene-plan.md`
- `docs/fde/README.md`
- `docs/frontend/README.md`
- `docs/history/README.md`
