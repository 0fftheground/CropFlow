# P2 第一版 Migration 范围清单

本文档用于把当前设计稿收口成第一版数据库 migration 边界。

目标不是重新设计数据模型，而是明确：

```text
1. 哪些表在 P2 第一版必须落库。
2. 哪些表和字段先不进入第一版 migration。
3. 哪些索引和依赖顺序必须在第一版一起落下。
4. 哪些内容虽然业务上需要，但先保留在编排上下文、metadata 或后续 migration。
```

当前口径基于以下已冻结输入：

```text
docs/model/data-model.md
docs/model/data-model-validation.md
docs/model/er-diagram.md
docs/workflow/task-workflow-matrix.md
database/sql/20260521_core_schema_consolidated.sql
```

## 1. Scope

第一版 migration 聚焦：

```text
单个 PlantingPlan 内部的计划编排、运行期事件触发、任务建议、人工审核、正式任务、执行记录和反馈闭环。
```

第一版 migration 不覆盖：

```text
设备指令下发细节
库存模块
通用工作流定义表
复杂配置化编排定义
```

## 2. Included Tables

第一版 migration 应创建以下表：

### 2.1 基础主数据

```text
cf_farm
cf_field
cf_farm_field_relation
cf_code_dict
cf_user
cf_user_account
cf_rice_variety
```

### 2.2 计划与阶段

```text
cf_planting_plan
cf_planting_plan_field_relation
cf_stage_prediction_snapshot
cf_crop_stage_state
cf_crop_thermal_time_state
cf_event_record
```

### 2.3 任务与方案

```text
cf_calendar_item
cf_task_intent
cf_review_request
cf_farming_task
cf_operation_plan
```

### 2.4 执行与结果

```text
cf_execution
cf_execution_record
cf_evaluation
cf_feedback
cf_system_notification
```

## 3. Deferred Tables

以下对象仍属于业务范围，但暂不进入第一版 migration：

```text
DeviceCommand
InventoryItem
InventoryTransaction
GeneralFlowDefinition
WorkflowDefinition
WorkflowInstance
WorkflowStepInstance
ChainDefinition
```

暂缓原因：

```text
1. DeviceCommand 依赖外部执行系统集成边界，当前只需通过 Execution.externalSystemCode / externalExecutionId 表达。
2. InventoryItem / InventoryTransaction 虽已确认需要独立表，但不在当前 consolidated SQL 范围内，应作为库存模块单独收口。
3. WorkflowDefinition / ChainDefinition 一类对象属于配置化工作流平台能力，超出 P2 第一版实现目标。
```

## 4. Must-Have Columns

以下字段属于第一版 migration 必落字段：

### 4.1 追溯字段

```text
cf_calendar_item.parent_task_id
cf_calendar_item.source_execution_id
cf_calendar_item.source_execution_record_id

cf_task_intent.parent_task_id
cf_task_intent.source_execution_id
cf_task_intent.source_execution_record_id

cf_farming_task.parent_task_id
cf_farming_task.source_execution_id
cf_farming_task.source_execution_record_id
```

### 4.2 审核链路字段

```text
cf_task_intent.converted_task_id
cf_farming_task.calendar_item_id
cf_farming_task.task_intent_id
cf_farming_task.review_request_id
cf_review_request.source_entity_type
cf_review_request.source_entity_id
cf_review_request.decision
cf_review_request.decision_payload
```

### 4.3 运行期闭环字段

```text
cf_calendar_item.generated_task_id
cf_calendar_item.generation_condition
cf_operation_plan.operation_window_start
cf_operation_plan.operation_window_end
cf_operation_plan.parameters
cf_execution.operation_plan_id
cf_execution_record.result_payload
cf_feedback.requires_review
cf_event_record.payload
cf_event_record.processing_status
```

### 4.4 幂等与审计字段

以下表第一版必须保留 `idempotency_key`：

```text
cf_event_record
cf_calendar_item
cf_task_intent
cf_review_request
cf_farming_task
cf_operation_plan
cf_feedback
```

以下表第一版必须保留审计字段：

```text
created_by_type
created_by_id
created_at
updated_at
```

## 5. Deferred Columns

以下字段在业务层已确认有意义，但当前已决定不进入第一版表结构：

```text
workflowKey
workflowStepKey
generalFlowKey
chainKey
```

第一版建议放置位置：

```text
1. 先放在 EventRecord.payload 或相关 handler 上下文。
2. 需要写入实体时，优先放 metadata / ruleResult / decisionPayload。
3. 待 P2 第一条实现链路跑通后，再决定是否提升为正式列。
```

## 6. Must-Have Indexes

第一版 migration 至少应包含以下索引：

### 6.1 追溯回查

```text
idx_cf_calendar_item_parent_task_id
idx_cf_calendar_item_source_execution_id
idx_cf_calendar_item_source_execution_record_id

idx_cf_task_intent_parent_task_id
idx_cf_task_intent_source_execution_id
idx_cf_task_intent_source_execution_record_id

idx_cf_farming_task_parent_task_id
idx_cf_farming_task_source_execution_id
idx_cf_farming_task_source_execution_record_id
```

### 6.2 审核与建议查询

```text
idx_cf_task_intent_plan_status
idx_cf_review_request_plan_status
idx_cf_review_request_assigned_user_id
idx_cf_review_request_source_entity
idx_cf_farming_task_plan_status
idx_cf_farming_task_review_request_id
```

### 6.3 执行链路查询

```text
idx_cf_execution_task_id
idx_cf_execution_operation_plan_id
idx_cf_execution_status
idx_cf_execution_record_execution_id
idx_cf_feedback_execution_id
idx_cf_feedback_requires_review
```

### 6.4 唯一约束

```text
uk_cf_event_record_idempotency_key
uk_cf_calendar_item_idempotency_key
uk_cf_task_intent_idempotency_key
uk_cf_review_request_idempotency_key
uk_cf_farming_task_idempotency_key
uk_cf_operation_plan_idempotency_key
uk_cf_feedback_idempotency_key
uk_cf_operation_plan_active_task
```

说明：

```text
uk_cf_operation_plan_active_task 用于保证同一 FarmingTask 同时只有一个 active OperationPlan。
```

## 7. Dependency Order

正式 migration 建议按以下顺序拆分：

1. 基础主数据

```text
cf_farm
cf_field
cf_farm_field_relation
cf_code_dict
cf_user
cf_user_account
cf_rice_variety
```

2. 计划与阶段

```text
cf_planting_plan
cf_planting_plan_field_relation
cf_event_record
cf_stage_prediction_snapshot
cf_crop_stage_state
cf_crop_thermal_time_state
```

3. 任务建议与审核

```text
cf_calendar_item
cf_task_intent
cf_review_request
cf_farming_task
cf_operation_plan
```

4. 执行与结果

```text
cf_execution
cf_execution_record
```

5. 评价、反馈、通知

```text
cf_evaluation
cf_feedback
cf_system_notification
```

6. 外键补充与索引

```text
parent_task_id
source_execution_id
source_execution_record_id
generated_task_id
converted_task_id
source_entity 相关索引
active OperationPlan 唯一索引
```

说明：

```text
由于 cf_calendar_item.generated_task_id、cf_task_intent.converted_task_id、以及三张表的 parent_task_id 都会反向指向 cf_farming_task，建议在正式 migration 中采用“先建表、后补外键”的方式。
```

## 8. Implementation Notes

第一版 migration 应服务于以下最小实现链路：

```text
调查结果录入
-> 发布调查结果事件
-> 生成 TaskIntent
-> 生成 ReviewRequest
-> 审核通过后生成 FarmingTask
-> 为正式任务创建 OperationPlan
```

因此，如果某个表或字段不支撑这条链路，应优先判断是否真的需要进入第一版 migration。

## 9. Out Of Scope

以下内容不应在第一版 migration 中顺手加入：

```text
1. 设备命令表及其回调细节。
2. 库存扣减、入库流水和批次管理。
3. 通用工作流定义表和流程实例表。
4. 与 Recommendation Entity 等价的新对象。
5. 未在当前 SQL 草案中冻结的扩展字段。
```

## 10. Next Step

基于本清单，后续执行顺序建议是：

1. 从 [20260521_core_schema_consolidated.sql](/F:/workspace/CropFlow/database/sql/20260521_core_schema_consolidated.sql:1) 拆出正式 migration 顺序。
2. 先落第一条最小实现链路所需表和外键。
3. `DeviceCommand / Inventory* / workflowKey*` 保持 deferred，不在第一版 migration 中顺手落库。
