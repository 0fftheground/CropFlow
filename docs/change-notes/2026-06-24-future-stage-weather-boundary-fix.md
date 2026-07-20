# 2026-06-24 Future Stage Weather Boundary Fix

## Summary

修正未来实际生育期日期触发阶段重算时的天气分段逻辑，避免系统向历史观测天气接口请求“今天”尚未落库的观测日数据。

## Code Changes

- `HttpWeatherProvider.get_daily_weather()` 新增真实当前日期边界控制
- 当业务传入未来 `as_of_date` 时：
  - observed 只读取到真实当前日期的前一天
  - forecast 从真实当前日期开始补齐今天及未来窗口
  - climatology 继续从真实 forecast 窗口之后开始
- 新增天气 provider 测试，覆盖“未来 as_of_date 仍按真实今天切 observed / forecast”场景

## Business Logic Changes

- 允许继续录入未来日期的实际生育期记录
- 阶段重算不会再因为上游历史天气接口缺少“今天”的观测日数据而直接报 400
- 对过去日期的回放口径保持不变，仍按传入 `as_of_date` 作为历史回放边界

## Affected Areas

- `app/services/calendar_tasks.py`
- `tests/services/test_weather_provider.py`

## Tests

建议至少执行：

```text
tests/services/test_weather_provider.py
tests/services/test_stage_management.py
```
