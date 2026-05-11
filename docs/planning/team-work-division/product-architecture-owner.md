# 产品 / 架构负责人

> 本文档从团队分工总览中拆出，用于单独说明产品 / 架构负责人的职责、关注点和近期交付物。

负责人：All。

## 主要职责

```text
1. 维护领域口径、核心对象和模块边界。
2. 确认业务规则、流程分支和接口优先级。
3. 判断新增需求是否进入 MVP。
4. Review 文档、表结构、API contract 和 PR 是否违反核心设计。
5. 组织每个方向补齐算法接口、OperationPlan 映射、执行反馈和评价规则。
```

## 需要重点确认

```text
1. 每个农事项是否需要生成 CalendarItem、FarmingTask、OperationPlan。
2. 哪些算法结果可以自动转任务，哪些必须人工确认。
3. 哪些执行结果会触发 Feedback、ReviewRequest 或后续任务。
4. 哪些字段需要结构化，哪些第一版先放 JSON。
5. 第一条垂直闭环的验收标准。
```

## 近期交付物

```text
1. docs/model/data-model.md 最终确认。
2. docs/workflow/task-workflow-matrix.md 业务流程确认。
3. docs/workflow/background-job-matrix.md 后台任务确认。
4. 第一条垂直闭环验收标准。
5. 各方向提交物 Review 结论。
```
