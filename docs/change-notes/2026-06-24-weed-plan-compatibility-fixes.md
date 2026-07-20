# 2026-06-24 Weed And Plan Compatibility Fixes

## Summary

修正杂草防治外部接口与种植计划地块校验的兼容问题，避免 `再生稻` 直接调用杂草诊断接口时报 400，同时让 `PlantingPlan` 创建时的地块存在性校验可以只查 `Field.id`。

## Code Changes

- `HttpWeedDiagnosisClient` 新增杂草接口专用的种植制度归一化逻辑
- 仅在调用 `soil_treatment_diagnosis / weed_survey_date_diagnosis / weed_treatment_diagnosis / additional_treatment_diagnosis` 时，把 `再生稻` 映射为 `早稻`
- `PlantProtectionPlanContextResolver` 不再在系统内部提前改写 `cultivation_system`
- `PlantingPlanService` 创建计划时优先调用 `FieldRepository.list_existing_ids()` 做地块存在性校验

## Business Logic Changes

- 系统内部仍保留 `PlantingPlan` 原始种植制度，避免影响其他编排环节后续对 `再生稻` 的判断
- 杂草防治外部接口继续接收其当前支持的枚举值；只有出站请求会做最小范围兼容映射
- 创建计划时，后端仍会校验 `field_ids` 全部存在且属于指定农场，但不再要求为“仅校验 id 是否存在”的场景加载完整地块对象

## Affected Areas

- `app/services/calendar_tasks.py`
- `app/services/planting_plans.py`
- `tests/services/test_calendar_tasks.py`
- `tests/services/test_planting_plan_service.py`
- `docs/api/weed_diagnosis_api入参组装和返回结果对象构建.md`
- `project-context/current-memory.md`

## Tests

建议至少执行：

```text
tests/services/test_calendar_tasks.py
tests/services/test_planting_plan_service.py
```

## Remaining Assumptions

- 当前兼容映射只覆盖杂草防治外部接口，不扩展到病虫害、生育期、施肥或其他系统环节。
- 如杂草接口后续原生支持 `再生稻`，可移除这层出站映射并保留内部原值传递。
