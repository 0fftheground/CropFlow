# CropFlow Planning Docs

`docs/planning/` 只保留规划、协作和阶段实现相关文档。

建议结构：

```text
1. 顶层只放长期稳定的总纲文档。
2. 执行规范放到 guides/。
3. 阶段性材料按 P1 / P2 归档。
4. 方向拆分材料放到 team-work-division/。
```

## 当前目录说明

| 路径 | 用途 |
|---|---|
| `docs/planning/development-roadmap.md` | 正式推进里程碑和阶段目标 |
| `docs/planning/team-work-division.md` | 通用分工原则和统一提交模板 |
| `docs/planning/guides/` | AI agent 规范和非代码交付模板 |
| `docs/planning/P1/` | 杂草样板闭环的历史收口材料 |
| `docs/planning/P2/` | 当前 P2 实现、runbook 和 migration 拆分材料 |
| `docs/planning/team-work-division/` | 按角色和方向拆分的具体协作材料 |

## 使用建议

```text
1. 恢复上下文时，先看 project-context/entrypoints.md，不要从 planning/ 逐个扫起。
2. 只需要阶段目标时，看 development-roadmap.md。
3. 只需要统一协作规则时，看 team-work-division.md 和 guides/。
4. 只需要当前 P2 落地细节时，进入 P2/。
5. 只在需要回看杂草样板历史口径时，进入 P1/。
```
