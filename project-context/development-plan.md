# CropFlow Development Plan

本文件用于维护仓库级全局开发计划。它描述长期稳定的阶段划分，不替代当前 session 的进展快照。

说明：

```text
1. 本文件中的 P0/P1/P2/P3 是为了 session 交接而使用的工作相位切片。
2. 当前不再维护独立 roadmap 文档；phase 定义以 project-context/ 下文档为准。
3. P 阶段只用于仓库内交接、当前推进定位和阶段范围维护。
```

## Phase Overview

| Phase | 对应 Roadmap | 名称 | 目标 | 当前状态 |
|---|---|---|---|---|
| `P0` | `T0` | 核心模型与契约收敛 | 冻结核心对象边界、模块边界、基础流程和接口模板 | `mostly_done` |
| `P1` | `T0 -> T1` | 杂草防治样板闭环 | 冻结第一条垂直闭环的业务口径、字段草案、页面范围和待决事项，并补齐进入实现前仍缺的关键契约 | `mostly_done` |
| `P2` | `T2` | 核心工程骨架与最小实现 | 建立后端工程、数据库迁移、最小 API、前端样板页和首条闭环实现 | `closing` |
| `P3` | `T3` | 多方向扩展接入 | 在不破坏核心模型的前提下扩展灌溉、施肥、遥感等方向 | `starting` |

## Phase Documents

| Phase | 文档 |
|---|---|
| `P0` | `project-context/phases/phase-0-contract-convergence.md` |
| `P1` | `project-context/phases/phase-1-weed-sample-loop.md` |
| `P2` | `project-context/phases/phase-2-core-implementation.md` |
| `P3` | `project-context/phases/phase-3-expansion.md` |

## 当前使用规则

```text
1. 新 session 默认先确认 current-memory 指向哪个 phase。
2. 如果当前工作改变了阶段目标、验收标准或范围，更新对应 phase 文档。
3. 如果只是推进了本阶段进度，不重复修改全局计划，只更新 current-memory。
4. phase 文档记录长期有效的阶段范围；current-memory 只记录当前阶段的压缩状态。
```
