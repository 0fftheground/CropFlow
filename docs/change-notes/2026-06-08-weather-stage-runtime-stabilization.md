# 2026-06-08 Weather Stage Runtime Stabilization

## Summary

收口天气与生育期运行期主线，明确 `observed / forecast / climatology` 的消费顺序，稳定实际生育期刷新与 `WeatherSnapshot` 留痕逻辑。

## Code Changes

- 引入并稳定农场年度 `WeatherSnapshot` 的消费与复用口径。
- 收口 `DailyWeatherCheckJob`、`StagePredictionRefreshJob` 在天气刷新场景下的职责边界。
- 调整实际生育期录入后的刷新逻辑，避免 forecast 小幅波动导致当前阶段和任务窗口无序抖动。

## Business Logic Changes

- 当前阶段以 `observed` 和人工录入真实生育期为权威输入。
- `forecast` 只刷新预测层，不直接触发当前阶段变化。
- 历史 `observed` 修正时，从修正日期或最近人工锚点之后重算，而不是整季全量回放。

## Affected Areas

- `docs/workflow/background-job-matrix.md`
- `docs/model/data-model.md`
- `docs/architecture/data-integration.md`
- `docs/decisions/007-stage-weather-runtime-mvp-rules.md`

## Tests

本次为历史变更补档，当前没有重新执行测试。当前说明以正式文档和已合入实现为准。

## Remaining Assumptions

- 当前天气运行期仍偏 MVP 口径，缓存、版本审计和前端异常展示还会继续补。
- 这一阶段不追求完整气象主数据平台能力。

## Manual Review Checklist

- 确认 `WeatherUpdated` 不会因为 forecast 小变化反复触发任务抖动。
- 确认人工录入真实生育期后，后续预测重算会尊重人工锚点。
- 确认 `WeatherSnapshot` 仍只承担已消费天气留痕和排查职责。

## Related Documents

- `docs/decisions/007-stage-weather-runtime-mvp-rules.md`
- `docs/workflow/background-job-matrix.md`
- `docs/model/data-model.md`
