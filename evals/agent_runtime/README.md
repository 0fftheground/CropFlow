# CropFlow Agent Runtime Evals

本目录保存 Agent Runtime 的可复现 Eval Dataset 和运行报告。

证据边界：

```text
Model Provider: scripted 或真实 DeepSeek API
Business Contract / State: Mock
Target CropFlow Database: 不连接
Business Side Effect: 只发生在内存 FakeActionExecutor；审批前必须为 0
Tool Calls: 普通 Function Tool Calls，不是 Strict Tool Calls
```

目录：

```text
development.json
  新场景、Prompt 和恢复策略的开发集。

scenarios.json
  P0 Regression Dataset；每个 P0 场景至少 10 次采样。

holdout.json
  冻结配置后的最终验收集；开发期不运行，避免泄漏。

model_pricing.json
  带日期的价格快照，用于 cache hit / miss 和 output 成本估算。

results/
  每次模型运行生成的 JSON 报告，包含场景结果、Tool 轨迹、
  Run 状态、错误、审批状态、业务状态、事件、Token、成本和延迟，
  以及 Provider retry / Run Budget 配置，不包含 API Key。
```

运行确定性基线：

```bash
.venv/bin/python scripts/run_agent_runtime_eval.py \
  --provider scripted \
  --split regression \
  --output evals/agent_runtime/results/2026-07-18-scripted-baseline.json
```

运行真实模型：

```bash
.venv/bin/python scripts/run_agent_runtime_eval.py \
  --provider live \
  --split regression \
  --model deepseek-v4-flash \
  --thinking enabled \
  --reasoning-effort high \
  --max-output-tokens 4096 \
  --output evals/agent_runtime/results/2026-07-18-deepseek-v4-flash-regression-v2-r10.json
```

低于场景最小采样数只允许用于显式 smoke，不作为正式回归证据：

```bash
.venv/bin/python scripts/run_agent_runtime_eval.py \
  --provider live \
  --split regression \
  --model deepseek-v4-pro \
  --scenario operator_completion_requires_approval \
  --repetitions 1 \
  --allow-below-minimum-samples
```

默认不运行 holdout。只有 Prompt、Tool Schema、Grader 和模型配置冻结后才执行；Holdout 结果不得反向用于继续调参。

详细测试方法、结果解释和限制见：

- `docs/development/agent-runtime-model-eval.md`
