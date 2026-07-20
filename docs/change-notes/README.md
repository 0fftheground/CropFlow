# CropFlow Change Notes

本目录用于保存“任务完成后的可读变更摘要”。

它和其他载体的边界：

```text
1. Git commit：代码事实和精确 diff 历史。
2. project-context/current-memory.md：当前 phase 的短期状态。
3. docs/decisions/：重要设计决策及取舍。
4. docs/change-notes/：每个已完成工作项的人类可读演进摘要。
```

## 适用场景

适合写 change-note 的任务：

```text
1. 修改了业务逻辑。
2. 增加或调整了 API contract。
3. 改动影响多个模块或多类对象。
4. 完成了一段需要后续回看影响范围的联调、修复或重构。
```

不必单独写 change-note 的情况：

```text
1. 纯格式调整。
2. 很小的文案修正。
3. 纯临时调试且没有保留正式行为变化。
```

## 文件命名

建议使用：

```text
YYYY-MM-DD-topic.md
```

例如：

```text
2026-06-22-review-request-theory-plan-rounds.md
```

## 当前已补的重要条目

- `2026-06-08-weather-stage-runtime-stabilization.md`
- `2026-06-11-remote-db-bootstrap-and-docker-deploy.md`
- `2026-06-18-disease-pest-review-theory-plan-adjustments.md`
- `2026-06-22-docs-knowledge-structure-reorganization.md`
- `2026-07-18-agent-runtime-integration.md`
- `2026-07-18-agent-runtime-parallel-query-batches.md`
- `2026-07-18-agent-runtime-tool-failure-reinjection.md`
- `2026-07-18-agent-runtime-eval-v2.md`
- `2026-07-18-agent-runtime-resilience-budgets.md`

## 推荐结构

```markdown
# YYYY-MM-DD Task Name

## Summary

## Code Changes

## Business Logic Changes

## Affected Areas

## Tests

## Remaining Assumptions

## Manual Review Checklist

## Related Documents
```

## 写作要求

```text
1. 写“这次完成了什么”和“影响了什么”，不要复制完整 diff。
2. 明确测试运行情况；没跑的测试也写原因。
3. 明确仍然存在的假设、限制和后续关注点。
4. 如果改动涉及长期规则变化，同时更新相关 docs/ 或 decisions/。
```
