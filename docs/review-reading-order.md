# Plan-level MVP 文档审阅建议（v2：移除 Recommendation）

---

# 1. 推荐阅读顺序

## 1.1 系统与功能说明

```text
plan_level_mvp_system_function_description_v2_no_recommendation.md
```

先理解系统是什么、做什么、不做什么。

---

## 1.2 总运行流程

```text
plan_level_mvp_overall_runtime_flow_v2_no_recommendation.md
```

理解种植计划从创建到执行反馈再到归档的完整闭环。

---

## 1.3 系统结构图

```text
plan_level_mvp_architecture_mermaid_revised_v4_no_recommendation.md
```

理解模块、事件、对象、外部系统之间的关系。

---

## 1.4 模块职责说明

```text
plan_level_mvp_module_responsibilities_revised_v2_no_recommendation.md
```

确认各模块负责什么、不负责什么。

---

## 1.5 核心对象说明

```text
plan_level_mvp_core_objects_updated_v4_no_recommendation.md
```

确认核心对象是否必要、边界是否清楚。

---

## 1.6 事件系统设计

```text
plan_level_mvp_event_system_design_updated_v4_no_recommendation.md
```

确认事件分类、流转和处理边界。

---

## 1.7 三个核心流程

```text
plan_creation_initialization_flow_updated_v2_no_recommendation.md
plan_runtime_event_task_update_flow_v2_no_recommendation.md
plan_task_execution_feedback_flow_v2_no_recommendation.md
```

分别审阅：

```text
1. 计划创建与初始化
2. 运行期事件触发与任务更新
3. 任务执行与反馈闭环
```

---

# 2. 审阅重点

```text
1. 是否认可 MVP 先做单个 PlantingPlan 内部闭环？
2. CalendarItem / TaskIntent / FarmingTask / OperationPlan 是否边界清楚？
3. 是否认可 MVP 阶段移除独立 Recommendation？
4. TaskIntent 是否足以承载运行期触发原因和建议说明？
5. OperationPlan 是否足以承载处方图、剂量、参数和方案依据？
6. Execution Module 是否只消费 FarmingTask + OperationPlan？
7. Feedback 是否应该回到 Plan Orchestrator，而不是直接生成任务？
8. ReviewRequest 是否应该作为独立人工复核对象？
9. 外部执行系统是否应该单独从系统输入中拆出？
10. Background Job Center 是否只负责发现变化，不做业务决策？
```

---

# 3. 最短阅读包

如果时间有限，建议至少阅读：

```text
1. plan_level_mvp_system_function_description_v2_no_recommendation.md
2. plan_level_mvp_architecture_mermaid_revised_v4_no_recommendation.md
3. plan_level_mvp_module_responsibilities_revised_v2_no_recommendation.md
4. plan_level_mvp_core_objects_updated_v4_no_recommendation.md
```

---

# 4. 审阅结论模板

```text
1. 总体方向：
   - 认可 / 基本认可 / 需要调整

2. MVP 范围：
   - 是否同意先做 Plan-level orchestration？

3. 模块边界：
   - 哪些模块职责需要调整？

4. 核心对象：
   - 是否同意移除独立 Recommendation？
   - CalendarItem / TaskIntent / FarmingTask / OperationPlan 是否清楚？

5. 事件系统：
   - Input Event / Domain Event 是否合理？
   - 是否需要新增关键事件？

6. 三个核心流程：
   - 是否足以覆盖 MVP？
   - 哪些流程需要补充？

7. 是否可以进入数据结构设计：
   - 可以 / 修改后可以 / 暂不建议
```
