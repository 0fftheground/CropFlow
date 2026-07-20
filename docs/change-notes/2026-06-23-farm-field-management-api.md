# 2026-06-23 Farm Field Management API

## Summary

补齐农场删除和农场下地块管理接口，新增地块 `external_field_id`，为后续更多农事方向接入提供基础农场/地块主数据能力。

## Code Changes

- 为 `Field` 新增 `external_field_id`，并补 Alembic + SQL migration。
- 在后端补齐 `FarmFieldRelation` 的 ORM / repository / service 实现。
- 新增农场删除接口和农场下地块 CRUD 接口：
  - `DELETE /api/farms/{farmId}`
  - `GET /api/farms/{farmId}/fields`
  - `POST /api/farms/{farmId}/fields`
  - `POST /api/farms/{farmId}/fields/batch`
  - `GET /api/farms/{farmId}/fields/{fieldId}`
  - `PATCH /api/farms/{farmId}/fields/{fieldId}`
  - `DELETE /api/farms/{farmId}/fields/{fieldId}`
  - `POST /api/farms/{farmId}/fields/batch-delete`

## Business Logic Changes

- `Field.id` 继续作为系统内部主键和 `PlantingPlan.field_ids` 的引用 id。
- 新增 `Field.external_field_id` 作为外部系统映射字段，不替代内部主键。
- 批量创建和批量删除地块按“整批成功或整批失败”处理。
- `PlantingPlan` 创建和更新时，后端会校验 `farm_id` 存在，且 `field_ids` 全部属于该农场。
- 农场 / 地块的 `PATCH` 现在支持通过显式传 `null` 清空可选字段，例如 `external_*_id`、`boundary_wkt`、中心点和 `area_ha`。
- 农场 / 地块写入时增加基础校验：纬度 `-90..90`、经度 `-180..180`、`area_ha > 0`。
- 删除农场时，如果农场已被 `PlantingPlan` 引用，或农场下地块已被 `PlantingPlanFieldRelation` 引用，后端返回 `409`。
- 删除地块时，如果地块已被 `PlantingPlanFieldRelation` 引用，后端返回 `409`。

## Affected Areas

- `app/models/core.py`
- `app/repositories/core.py`
- `app/services/farms.py`
- `app/api/routes/farms.py`
- `app/api/deps.py`
- `tests/api/test_farms.py`
- `tests/services/test_farms.py`
- `docs/model/data-model.md`
- `docs/api/frontend-plant-protection-api-contract.md`

## Tests

建议至少执行：

```text
tests/api/test_farms.py
tests/services/test_farms.py
```

## Remaining Assumptions

- 当前 `Field.external_field_id` 只作为外部映射字段，不作为前端主引用 id。
- `PlantingPlan.field_ids` 继续使用内部 `Field.id`，前端联调时不应把 `external_field_id` 当作计划主引用 id。
