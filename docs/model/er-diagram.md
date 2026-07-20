# CropFlow ER Diagram

本文档用于补充第一版核心实体关系图，重点覆盖：

- `CalendarItem / TaskIntent / FarmingTask / ReviewRequest / OperationPlan`
- 运行期调查结果触发的新农事建议链路
- `parentTaskId / sourceExecutionId / sourceExecutionRecordId`

## 1. Core ER

```mermaid
erDiagram
    PLANTING_PLAN ||--o{ CALENDAR_ITEM : has
    PLANTING_PLAN ||--o{ TASK_INTENT : has
    PLANTING_PLAN ||--o{ FARMING_TASK : has
    PLANTING_PLAN ||--o{ REVIEW_REQUEST : has
    PLANTING_PLAN ||--o{ EXECUTION : has
    PLANTING_PLAN ||--o{ EXECUTION_RECORD : has

    CALENDAR_ITEM o|--o| FARMING_TASK : generatedTaskId
    TASK_INTENT o|--o| FARMING_TASK : convertedTaskId
    REVIEW_REQUEST o|--o| FARMING_TASK : resolvedTo

    FARMING_TASK ||--o{ OPERATION_PLAN : has
    FARMING_TASK ||--o{ EXECUTION : has
    EXECUTION ||--o{ EXECUTION_RECORD : has

    EXECUTION_RECORD ||--o{ CALENDAR_ITEM : sourceExecutionRecordId
    EXECUTION_RECORD ||--o{ TASK_INTENT : sourceExecutionRecordId
    EXECUTION_RECORD ||--o{ FARMING_TASK : sourceExecutionRecordId

    EXECUTION ||--o{ CALENDAR_ITEM : sourceExecutionId
    EXECUTION ||--o{ TASK_INTENT : sourceExecutionId
    EXECUTION ||--o{ FARMING_TASK : sourceExecutionId

    FARMING_TASK ||--o{ CALENDAR_ITEM : parentTaskId
    FARMING_TASK ||--o{ TASK_INTENT : parentTaskId
    FARMING_TASK ||--o{ FARMING_TASK : parentTaskId

    TASK_INTENT ||--o| REVIEW_REQUEST : sourceEntity

    PLANTING_PLAN {
        id id PK
        string planCode
    }

    CALENDAR_ITEM {
        id id PK
        id plantingPlanId FK
        string taskSubtype
        date suggestedStartDate
        date suggestedEndDate
        string status
        id parentTaskId FK
        id sourceExecutionId FK
        id sourceExecutionRecordId FK
        id generatedTaskId FK
    }

    TASK_INTENT {
        id id PK
        id plantingPlanId FK
        string taskSubtype
        string status
        string triggerType
        text triggerSummary
        json ruleResult
        id parentTaskId FK
        id sourceExecutionId FK
        id sourceExecutionRecordId FK
        id convertedTaskId FK
    }

    REVIEW_REQUEST {
        id id PK
        id plantingPlanId FK
        string reviewType
        string status
        string decision
        string sourceEntityType
        id sourceEntityId
        json decisionPayload
    }

    FARMING_TASK {
        id id PK
        id plantingPlanId FK
        id calendarItemId FK
        id taskIntentId FK
        id reviewRequestId FK
        string taskSubtype
        datetime plannedStartAt
        datetime plannedEndAt
        string status
        id parentTaskId FK
        id sourceExecutionId FK
        id sourceExecutionRecordId FK
    }

    OPERATION_PLAN {
        id id PK
        id plantingPlanId FK
        id farmingTaskId FK
        string algorithmCode
        datetime operationWindowStart
        datetime operationWindowEnd
        json parameters
    }

    EXECUTION {
        id id PK
        id plantingPlanId FK
        id farmingTaskId FK
        id operationPlanId FK
        string executionMode
        string status
    }

    EXECUTION_RECORD {
        id id PK
        id plantingPlanId FK
        id executionId FK
        datetime actualEndAt
        json resultPayload
    }
```

## 2. Traceability Rules

- `parentTaskId`
  表示这条新农事项/任务建议/正式任务在业务上延续或补救的是哪条原 `FarmingTask`。
- `sourceExecutionRecordId`
  表示直接触发本次新增对象的那条结果记录。
- `sourceExecutionId`
  表示该结果记录所属的执行过程，便于从对象追溯到执行链路。

## 3. Review Context

`ReviewRequest.decisionPayload` 当前建议至少包含：

```json
{
  "contextRefs": {
    "parentTaskId": "task_xxx",
    "sourceExecutionId": "execution_xxx",
    "sourceExecutionRecordId": "record_xxx",
    "inputTaskIds": ["task_a", "task_b"],
    "inputExecutionRecordIds": ["record_a", "record_b"]
  },
  "adjustments": {},
  "reason": ""
}
```

## 4. Weed Loop Example

以 `additional_treatment_diagnosis` 触发补防为例：

1. 原 `WF_STEM_LEAF_WEED` 完成作业。
2. 后续安全性调查、防效兼安全性调查分别生成 `ExecutionRecord`。
3. 防效兼安全性调查结果直接触发 `TaskIntent`。
4. 该 `TaskIntent.parentTaskId` 指向原茎叶除草 `FarmingTask`。
5. 该 `TaskIntent.sourceExecutionRecordId` 指向触发补防判断的防效兼安全性调查 `ExecutionRecord`。
6. `ReviewRequest` 从 `TaskIntent` 派生，`decisionPayload.contextRefs` 保留额外输入引用，例如安全性调查记录。
7. 审核通过后生成新的补防 `FarmingTask`，并继续保留 `parentTaskId / sourceExecutionRecordId`。
