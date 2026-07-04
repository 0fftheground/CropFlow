# 2026-07-04 Direct Seeded GDD Threshold Adjustment

## Summary

修正直播种植计划的生育期阈值消费口径。外部 GDD 阈值接口返回的累计积温阈值包含移栽返青期积温；直播计划没有移栽返青期，因此 CropFlow 后端在保存和消费阈值前扣除 `BBCH21 - BBCH13`。

## Code Changes

- `StageManagementService` 在阈值规则 enrichment 阶段识别 `PlantingPlan.planting_method_code = 1` 的直播计划。
- 直播计划计算 `BBCH21 - BBCH13` 作为返青期积温差，并从 `BBCH21` 及后续阶段阈值中扣除。
- 调整结果写入 `StagePredictionSnapshot.thermal_thresholds.direct_seeding_threshold_adjustment`，天气刷新和人工生育期重算复用旧阈值时不会重复扣减。
- 保留既有移栽逻辑：非直播早稻且存在 `transplant_date` 时，系统继续把移栽日期作为 `BBCH13` 人工锚点，再按阈值差推导后续阶段。

## Business Logic Changes

- 直播计划的分蘖期、破口期、齐穗期、成熟期等阶段日期会相对旧口径提前。
- 移栽计划不做直播阈值扣减；移栽场景仍以 `transplant_date` 作为 `BBCH13` 锚点。
- 外部算法服务仍只返回统一阈值；直播 / 移栽差异由 CropFlow 后端在消费阈值时处理。

## Affected Areas

- `app/services/stage_management.py`
- `tests/services/test_stage_management.py`
- `docs/api/growth_stage_gdd_api.md`

## Tests

已执行：

```text
.venv\Scripts\python.exe -m pytest tests\services\test_stage_management.py
```
