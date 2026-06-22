# Docs Hygiene

> 本文档记录当前 CropFlow 文档结构的维护规则。  
> 目标不是继续维护旧分层，而是维持已经落地的新结构，避免事实源再次混杂。

---

## 1. 当前目录分层

```text
docs/
  README.md
  ai/
  architecture/
  model/
  workflow/
  decisions/
  api/
  change-notes/
  domain/
  fde/
  frontend/
  history/
  maintenance/
```

各目录职责：

```text
1. architecture / model / workflow / api：系统正式事实源。
2. domain：按业务方向沉淀长期领域知识。
3. fde：后端/FDE 访谈、梳理、维护业务核心逻辑的方法和模板。
4. frontend：给前端开发的 handoff、页面范围和展示口径。
5. history：旧阶段计划、runbook、拆解和迁移材料，只保留历史证据。
6. change-notes：已经完成的改动记录，不承接旧 planning 材料。
7. maintenance：文档维护规则和整理说明。
```

## 2. 文档维护原则

```text
1. 长期系统事实只放在 architecture / model / workflow / api。
2. 业务方向知识只放在 docs/domain/，不再塞回 planning。
3. FDE 仍保留，但它描述的是采访、梳理和沉淀策略，不是系统正式事实源。
4. 前端 handoff 继续保留在 docs/frontend/，便于页面和展示功能联调。
5. 历史计划、runbook、拆解材料统一进入 docs/history/。
6. change-notes 只记录“已经发生的变更”，不记录未执行计划。
7. 删除旧文档前，先完成迁移、替换引用并确认仍有历史证据或无保留价值。
```

## 3. 当前事实源入口

```text
project-context/entrypoints.md
project-context/development-plan.md
project-context/current-memory.md
docs/README.md
docs/wiki-index.md
docs/domain/
docs/fde/
docs/frontend/
docs/workflow/
```

## 4. 归档规则

应进入 `docs/history/` 的内容：

```text
1. 某一阶段已经完成的计划拆解。
2. 只服务于旧阶段的 runbook。
3. migration 历史方案和旧实施记录。
4. 不再作为默认入口、但仍值得保留的过程证据。
```

不应进入 `docs/history/` 的内容：

```text
1. 当前仍在维护的业务方向知识。
2. 当前仍在使用的前端 handoff。
3. FDE 通用方法和访谈模板。
4. 核心架构、模型、workflow 事实源。
```

## 5. change-notes 规则

```text
1. change-notes 只写已经完成的文档或系统变更。
2. 历史 planning、todo、runbook 不迁入 change-notes。
3. 如果某次历史材料最终落成了明确改动，可单独补一条完成态记录。
```

## 6. 更新检查清单

每次新增或调整文档后，至少检查：

```text
1. 是否放在了正确目录。
2. 是否和现有事实源重复。
3. 是否还引用旧 planning 路径。
4. 是否需要同步 docs/wiki-index.md 和 docs/README.md。
5. 是否需要把旧材料改放 docs/history/ 或 docs/change-notes/。
```
