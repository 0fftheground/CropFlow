# V1 SQL Migrations

本目录用于承接 P2 第一版数据库迁移骨架。

当前状态：

```text
1. 先按纯 SQL 文件维护执行顺序。
2. 后续后端工程初始化后，推荐迁移到 Alembic revision 管理。
3. 表结构真相来源仍是 ../20260521_core_schema_consolidated.sql。
```

执行顺序：

```text
001_create_base_reference_tables.sql
002_create_plan_and_stage_tables.sql
003_create_task_and_review_tables.sql
004_create_execution_tables.sql
005_create_feedback_and_notification_tables.sql
006_add_traceability_fks_and_indexes.sql
```

Deferred：

```text
DeviceCommand
InventoryItem
InventoryTransaction
workflowKey / workflowStepKey / generalFlowKey / chainKey
```
