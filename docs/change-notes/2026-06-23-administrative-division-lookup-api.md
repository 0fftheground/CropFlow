# 2026-06-23 Administrative Division Lookup API

## Summary

新增行政区划只读查询接口，基于 `docs/references/raw/china_administrative.xlsx` 为农场创建 / 编辑页提供省、市、区县级联选项。

## Code Changes

- 新增 `GET /api/administrative-divisions`
- 新增 `cf_administrative_division` 参考表和对应 Alembic migration
- 新增 `AdministrativeDivisionQueryService`，运行期只查数据库
- 扩展 `seed_reference_data`，把本地行政区划 xlsx 导入参考表
- 对直辖市补充二级虚拟城市节点，保证前端仍可按“省 -> 市 -> 区县”统一交互

## Business Logic Changes

- 根节点查询不传参数，返回全部一级行政区节点
- 继续查询子节点时，前端传 `parent_code + parent_level`
- 返回结果包含：
  - `code`
  - `adcode`
  - `name`
  - `division_type`
  - `level`
  - `parent_code`
  - `has_children`
  - `is_virtual`
- `adcode` 取自源表 12 位行政区划代码的前 6 位，可直接用于农场 `adcode` 回填

## Affected Areas

- `app/services/administrative_divisions.py`
- `app/bootstrap/reference_data.py`
- `app/api/routes/administrative_divisions.py`
- `app/api/deps.py`
- `app/api/router.py`
- `app/models/master_data.py`
- `app/repositories/core.py`
- `alembic/versions/013_create_administrative_division_table.py`
- `database/sql/migrations/v1/013_create_administrative_division_table.sql`
- `tests/services/test_administrative_divisions.py`
- `tests/api/test_lookup_routes.py`
- `docs/api/frontend-plant-protection-api-contract.md`
- `docs/frontend/plant-protection-handoff.md`
- `docs/model/data-model.md`
- `project-context/current-memory.md`

## Tests

建议至少执行：

```text
tests/services/test_administrative_divisions.py
tests/api/test_lookup_routes.py
tests/api/test_farms.py
```

## Remaining Assumptions

- 当前接口优先服务农场省 / 市 / 区县级联选择，不额外包装前端页面状态。
- 行政区划数据以仓库内参考 xlsx 为 seed 源；更新源文件后需要重新执行参考数据导入。
