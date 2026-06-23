# 2026-06-23 Models Module Split

## Summary

将过大的 `app/models/core.py` 拆分为按领域分组的多个模型文件，降低单文件维护成本，同时保持 `app.models` 和 `app.models.core` 的导出兼容面不变。

## Code Changes

- 新增按领域分组的模型模块：
  - `app/models/master_data.py`
  - `app/models/planning.py`
  - `app/models/tasks.py`
  - `app/models/execution.py`
- `app/models/__init__.py` 改为从上述模块统一导出模型。
- `app/models/core.py` 改为兼容层，只负责重新导出既有模型符号。

## Behavior Impact

- 无业务行为变化。
- 现有 `from app.models import ...` 继续可用。
- 现有 `from app.models.core import ...` 也继续可用。
- ORM metadata 注册结果保持不变，数据库表结构和迁移口径未改动。

## Affected Areas

- `app/models/core.py`
- `app/models/__init__.py`
- `app/models/master_data.py`
- `app/models/planning.py`
- `app/models/tasks.py`
- `app/models/execution.py`

## Tests

建议至少执行：

```text
tests/repositories/test_registry.py
tests/services/test_farms.py
tests/api/test_farms.py
tests/services/test_planting_plan_service.py
tests/api/test_planting_plans.py
```

## Remaining Assumptions

- 当前拆分只调整文件组织，不进一步引入 relationship 声明或新的子包层级。
- 后续如继续扩展模型，应优先落到对应领域文件，而不是再回填到 `app/models/core.py`。
