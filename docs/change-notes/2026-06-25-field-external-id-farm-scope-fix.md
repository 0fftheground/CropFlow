# 2026-06-25 Field External ID Farm Scope Fix

## Summary

修正地块 `external_field_id` 的唯一性口径：从“全局唯一”改为“同一农场内唯一”，避免不同农场使用相同外部地块 id 时被后端错误拦截。

## Code Changes

- `FarmFieldService` 的地块创建、批量创建和更新逻辑改为按 `farm_id` 范围检查 `external_field_id`
- `Field` ORM 模型去掉 `external_field_id` 的全局唯一约束，保留普通索引
- 基线 SQL `012_add_field_external_id.sql` 改为只建字段和普通索引
- 新增迁移 `014_scope_field_external_id_to_farm.sql`，用于删除已部署库上的旧全局唯一约束

## Business Logic Changes

- 不同农场可以使用相同的 `external_field_id`
- 同一农场内仍然不允许两个地块使用相同的 `external_field_id`
- 批量创建时，请求体内部重复的 `external_field_id` 仍然会被拒绝

## Affected Areas

- `app/services/farms.py`
- `app/models/master_data.py`
- `database/sql/migrations/v1/012_add_field_external_id.sql`
- `database/sql/migrations/v1/014_scope_field_external_id_to_farm.sql`
- `alembic/versions/014_scope_field_external_id_to_farm.py`
- `database/sql/20260521_core_schema_consolidated.sql`
- `tests/services/test_farms.py`
- `docs/model/data-model.md`

## Tests

已执行：

```text
tests/services/test_farms.py
tests/api/test_farms.py --import-mode=importlib
```

## Deployment Note

如果目标环境已经执行过旧版 `012_add_field_external_id`，需要继续执行新增的 `014_scope_field_external_id_to_farm`，否则数据库层仍会因为旧的全局唯一约束而报错。
