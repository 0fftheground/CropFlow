# CropFlow Repository Skills

本目录用于保存随仓库分发的 CropFlow workflow skill 定义。

目标：

```text
1. 让新的 AI session 在离开个人本地环境后，仍能复用同一套启动和扫尾流程。
2. 让技能说明成为仓库资产，而不是只存在于本地 Codex skill 目录。
3. 让团队成员可以直接基于仓库内容审查和演进这些 workflow。
```

当前提供：

```text
skills/cropflow-start-work/SKILL.md
skills/cropflow-task-planning/SKILL.md
skills/cropflow-task-closing/SKILL.md
skills/cropflow-wrap-up/SKILL.md
skills/cropflow-wiki-maintenance/SKILL.md
```

说明：

```text
1. 这些 skill 是仓库内镜像定义，内容应与团队实际工作流保持一致。
2. 如果本地 Codex 已安装同名 skill，优先保证两边语义一致。
3. 修改 skill 时，应同步检查 AGENTS.md、CLAUDE.md、docs/ai/README.md 和相关入口文档是否需要更新。
4. 本文件只保留 skill 清单和仓库镜像说明。
5. 面向人的完整 skill 工作流说明，统一放在 docs/ai/codex-skill-workflow.md。
```
