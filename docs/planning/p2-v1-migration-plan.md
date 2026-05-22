# P2 第一版 Migration 顺序草案

本文档把 [P2 第一版 Migration 范围清单](/F:/workspace/CropFlow/docs/planning/p2-v1-migration-scope.md:1) 进一步落实为可执行的 migration 拆分顺序。

目标：

```text
1. 让 consolidated SQL 可以拆成可维护的迁移文件。
2. 控制第一版表结构边界，不把 deferred 对象顺手带入。
3. 让后续后端实现按稳定顺序落库，而不是继续维护单个超大 SQL。
```

## 1. Tool Recommendation

推荐工具：`Alembic`

原因：

```text
1. 当前后端口径是 Python + FastAPI + PostgreSQL，Alembic 是最常见且最稳的迁移工具。
2. 即使第一版先维护纯 SQL 文件，后续也可以平滑接入 Alembic 版本链。
3. Alembic 适合管理“先建表、后补外键、再补索引”的分阶段迁移。
```

当前仓库还没有后端工程和 Alembic 环境，因此这一轮先做：

```text
1. SQL 迁移骨架文件
2. 执行顺序约定
3. 每个迁移的职责边界
```

后续真正接入后端工程时，再把这些 SQL 骨架转成 Alembic revision。

## 2. Naming Convention

第一版推荐采用：

```text
NNN_<short_description>.sql
```

示例：

```text
001_create_base_reference_tables.sql
002_create_plan_and_stage_tables.sql
003_create_task_and_review_tables.sql
004_create_execution_tables.sql
005_create_feedback_and_notification_tables.sql
006_add_traceability_fks_and_indexes.sql
```

说明：

```text
1. 三位递增序号比日期前缀更适合表达执行顺序。
2. 语义名应直接体现本次迁移的边界，而不是泛化成 patch/update/fix。
3. 同一个迁移文件只负责同一层依赖，不跨层混放。
```

## 3. Migration Sequence

### 001 `create_base_reference_tables`

职责：

```text
基础主数据和最小用户表。
```

应包含：

```text
cf_farm
cf_field
cf_farm_field_relation
cf_code_dict
cf_user
cf_user_account
cf_rice_variety
cf_set_updated_at()
```

不应包含：

```text
PlantingPlan 及其之后的业务表
任何反向外键
Inventory*
DeviceCommand
```

### 002 `create_plan_and_stage_tables`

职责：

```text
计划、阶段状态、预测快照、事件表。
```

应包含：

```text
cf_planting_plan
cf_planting_plan_field_relation
cf_event_record
cf_stage_prediction_snapshot
cf_crop_stage_state
cf_crop_thermal_time_state
```

说明：

```text
该层负责给后续任务、执行、反馈提供 plan-level 归属和阶段上下文。
```

### 003 `create_task_and_review_tables`

职责：

```text
任务建议、人工审核、正式任务、作业方案。
```

应包含：

```text
cf_calendar_item
cf_task_intent
cf_review_request
cf_farming_task
cf_operation_plan
```

应延后到 006 的内容：

```text
cf_calendar_item.generated_task_id -> cf_farming_task
cf_task_intent.converted_task_id -> cf_farming_task
parent_task_id -> cf_farming_task
source_execution_id -> cf_execution
source_execution_record_id -> cf_execution_record
```

说明：

```text
第三层先把任务主表建起来，但不在同一文件中处理所有反向依赖。
```

### 004 `create_execution_tables`

职责：

```text
执行主表和执行结果表。
```

应包含：

```text
cf_execution
cf_execution_record
```

说明：

```text
这层完成后，运行期调查结果、作业结果、sourceExecution* 相关外键才具备补充条件。
```

### 005 `create_feedback_and_notification_tables`

职责：

```text
评价、反馈、通知。
```

应包含：

```text
cf_evaluation
cf_feedback
cf_system_notification
```

说明：

```text
这层支撑“执行 -> 评价 -> 反馈 -> 复核/后续动作”闭环，但不引入新的核心编排对象。
```

### 006 `add_traceability_fks_and_indexes`

职责：

```text
补充跨表外键、追溯字段外键、索引、唯一约束和列注释。
```

应包含：

```text
generated_task_id / converted_task_id 外键
parent_task_id 外键
source_execution_id 外键
source_execution_record_id 外键
review / traceability / execution 相关索引
uk_cf_operation_plan_active_task
关键 COMMENT ON TABLE / COMMENT ON COLUMN
```

说明：

```text
把所有“必须先有目标表才能加”的约束统一收在最后一层，可以显著降低迁移回滚和调试复杂度。
```

## 4. Deferred Objects

本轮不进入迁移链：

```text
DeviceCommand
InventoryItem
InventoryTransaction
WorkflowDefinition
WorkflowInstance
WorkflowStepInstance
ChainDefinition
GeneralFlowDefinition
```

本轮不进入正式列：

```text
workflowKey
workflowStepKey
generalFlowKey
chainKey
```

## 5. Mapping To Current SQL

当前拆分来源：

```text
database/sql/20260521_core_schema_consolidated.sql
```

拆分原则：

```text
1. 以 consolidated SQL 为字段真相。
2. 以 p2-v1-migration-scope.md 为 included/deferred 边界真相。
3. 以 data-model.md / task-workflow-matrix.md 为语义真相。
```

## 6. Immediate Next Step

建议按以下顺序继续：

1. 先在 `database/sql/migrations/v1/` 维护 SQL 骨架。
2. 再从 consolidated SQL 逐段搬运 DDL 到对应文件。
3. 等后端工程初始化后，再把这些文件转成 Alembic revision 或作为 baseline SQL 纳管。
