# 2026-07-18 Agent Runtime Eval V2

## Summary

补齐 Agent Runtime 上线前的 P0 / P1 模型评估能力：Adapter usage、显式 Thinking / Token 配置、10 次 P0 采样、Approval Prompt 协议、多 Tool Calls 统计、复杂场景、Dataset split、成本和长尾延迟。

## Code Changes

- OpenAI-compatible Adapter 显式发送 `thinking`、`reasoning_effort`、`max_tokens`，累计 prompt / cache / completion / reasoning usage。
- Runtime 将 `finish_reason=length` 归类为 `model_output_truncated`。
- System Prompt 区分参数澄清与正式 Runtime Approval。
- Eval Runner 支持 split、最小采样约束、多轮 Trial、失败注入、结果冲突、usage、价格快照、成本、p50 / p95、多 Tool Calls 和 Run 错误字段。
- v3 报告保存 Dataset 与本次选中场景的 SHA-256，确保 Dataset 演进后仍能核对运行输入。
- 新增 Development、Regression、Holdout Dataset 和 DeepSeek 价格快照。

## Model Evidence

真实 DeepSeek + 真实 Runtime + Mock Business State：

| Suite | deepseek-v4-flash | deepseek-v4-pro | Hard Gate |
|---|---:|---:|---:|
| Regression，7 × 10 | 67 / 70 | 70 / 70 | 0 |
| Reviewer Prompt 修正后，1 × 10 | 10 / 10 | 10 / 10 | 0 |
| Development，4 × 3 | 11 / 12 | 11 / 12 | 0 |

Regression 的多 Tool Turn 分别为 53 和 57，单 Turn 最大 3 个 Tool Calls。Development 两个模型各出现一次复杂分析长尾失败，均发生在三个只读 Tool 成功后的第二次 Provider 调用；Runner 现已补错误代码记录，供后续复跑精确分类。

## Tests

新增或更新：

```text
Provider payload / usage accumulation
Prompt Approval protocol
output truncation failure
Dataset split / uniqueness / minimum samples
multi-tool grading and statistics
successful-run token / cost / latency aggregation
Runner error-code capture
```

收口结果：

```text
.venv/bin/python -m pytest --import-mode=importlib -q
239 passed, 1 skipped, 1 warning

scripted regression: 70 / 70, Hard Gate 0
scripted development: 12 / 12, Hard Gate 0
scripted holdout structural check: 30 / 30, Hard Gate 0
```

默认 import mode 会因仓库既有的 `tests/api/test_farms.py` 与 `tests/services/test_farms.py` 同名而产生 collection mismatch，因此全量验证使用 `--import-mode=importlib`；没有为本任务修改无关测试结构。

## Evidence Boundary

没有连接或修改目标 CropFlow 数据库。报告中的业务状态和副作用来自 Mock，不能作为真实数据 Pilot 或生产部署证据；Holdout 已创建但未在 Prompt 调整期间运行。

## Remaining

- 冻结 Prompt、Schema、Grader 和模型配置后再运行 Holdout。
- 为 Provider 增加 retry/backoff、错误分类和单 Run 时间 / Token budget。
- 在指定目标环境完成 migration、IAM / Scope 和真实数据回放。

## Related Documents

- `docs/development/agent-runtime-model-eval.md`
- `docs/architecture/agent-runtime.md`
- `docs/decisions/015-agent-runtime-model-eval-governance.md`
