# CropFlow Development Plan

> 本文档用于记录 CropFlow MVP 的阶段性开发安排。  
> 目标是明确当前处于哪一步、下一步做什么，以及每个阶段的完成标准。

---

# 1. 当前状态

当前阶段：

```text
Phase 2：逻辑数据模型设计
```

已完成：

```text
1. MVP 范围确认：只做单个 PlantingPlan 内部闭环。
2. 核心对象边界确认：不引入独立 Recommendation Entity。
3. 模块边界确认：Plan / Stage / Task / Execution / Feedback / Review / Event。
4. 编排设计确认：Orchestrator 内部采用 Handler / Policy / Strategy / Service 分层。
5. 第一版逻辑数据模型草案已生成：docs/data-model.md。
```

当前正在做：

```text
1. 收敛数据模型字段、关系、状态枚举和幂等策略。
2. 确认 Farm / Field、EventRecord、TaskCategory / TaskSubtype 等基础模型。
3. 使用 docs/data-model-validation.md 与业务流程和算法服务核对模型。
```

下一步：

```text
先完成 data-model-validation 核对，再基于 docs/data-model.md 生成 ER 图和第一版表结构草案。
```

---

# 2. 团队分工与协作方式

当前预期参与角色：

```text
1. 产品 / 架构负责人：你。
2. 后端开发：另一位后端同学。
3. 前端开发：一位前端同学。
4. 可选第 4 人：后端集成、测试、外部接口 mock 或工程基础设施。
```

## 2.1 产品 / 架构负责人

主要职责：

```text
1. 维护 CropFlow 的领域口径和模块边界。
2. 确认业务规则、数据模型决策和接口优先级。
3. 定义每个阶段的验收标准。
4. Review PR 是否违反核心设计。
5. 判断新增需求是否进入 MVP。
```

重点把控：

```text
1. 不引入独立 Recommendation Entity。
2. Feedback 和 ReviewRequestResolved 必须回到 Plan Orchestrator。
3. Execution Module 不反向创建 FarmingTask。
4. Task Module 不直接处理外部硬件执行。
5. 新增农事子类优先通过 taskSubtype 扩展，不新增重复核心对象。
```

不建议承担：

```text
1. 所有 CRUD 细节实现。
2. 所有页面交互细节。
3. 所有测试代码编写。
```

## 2.2 后端开发

主要职责：

```text
1. 数据库表结构和迁移。
2. 模块目录和领域服务实现。
3. PlanOrchestrator / Handler / Policy / Strategy 的后端实现。
4. Plan Module / Task Module / Execution Module / Feedback / Review 后端接口。
5. EventRecord、幂等、追溯和状态流转。
6. 后端单元测试和集成测试。
```

第一阶段重点：

```text
1. PlantingPlan 创建。
2. CalendarItem / TaskGenerationPlan / FarmingTask 基础链路。
3. OperationPlan 基础模型。
4. EventRecord 和最小 PlanOrchestrator。
5. ReviewRequest / Feedback 的基础闭环占位。
```

避免事项：

```text
1. 不先做复杂规则后台。
2. 不把编排逻辑写进 Repository。
3. 不让 Execution Module 直接创建 FarmingTask。
4. 不为了未来扩展提前做复杂框架。
```

## 2.3 前端开发

主要职责：

```text
1. 计划创建页面。
2. 计划详情页面。
3. 农事项 / 任务列表。
4. 任务详情和 OperationPlan 查看。
5. 执行反馈录入或查看。
6. ReviewRequest 人工复核页面。
7. 与后端 API 契约对齐。
```

第一阶段重点：

```text
1. 基于 mock API 搭建主流程页面。
2. 确认页面需要的字段和状态。
3. 和后端并行对齐 API contract。
4. 先覆盖主链路，不先做复杂配置后台。
```

避免事项：

```text
1. 不把 Recommendation 当成独立页面主对象。
2. 不把 CalendarItem 当成可执行任务。
3. 不绕过 ReviewRequest 直接修改后续任务。
```

## 2.4 可选第 4 人

如果后续增加第 4 人，优先安排在：

```text
1. EventRecord、Background Job、外部接口 mock。
2. 测试和本地开发环境。
3. CI、数据库迁移、种子数据。
4. 前后端联调支持。
```

不建议把第 4 人直接投入未收敛的复杂规则后台。

---

# 3. 分工开发进入条件

当前还不建议直接全面并行开发。建议先完成以下“开工前契约”：

```text
1. ER 图：docs/er-diagram.md。
2. 第一版表结构草案。
3. 技术栈选择。
4. API 契约草案：docs/api-contract.md。
5. 前端页面清单和主流程原型。
6. 本地开发方式。
7. 第一阶段迭代目标和验收标准。
```

进入分工开发的判断标准：

```text
1. 开发成员不需要频繁确认“这个对象归谁管”。
2. 核心接口已经有字段和状态定义。
3. 前端可以基于 mock API 开始页面开发。
4. 后端可以基于表结构和模块边界开始实现。
5. 第一阶段只做一个垂直闭环，不铺开所有功能。
```

---

# 4. 时间节点建议

## T0：当前节点

状态：

```text
Phase 2：逻辑数据模型设计
```

目标：

```text
1. 完成 data-model.md 收敛。
2. 生成 ER 图。
3. 收敛剩余数据模型开放项。
```

主要负责人：

```text
产品 / 架构负责人
```

## T1：开工前契约节点

进入条件：

```text
1. ER 图完成。
2. 第一版表结构草案完成。
3. 后端技术栈确定。
4. API 契约草案完成。
5. 前端页面清单完成。
6. 前端技术栈由前端负责人确认，或至少确认 mock 和接口对接方式。
```

输出：

```text
1. 后端可以开始建表、迁移和核心接口。
2. 前端可以基于 mock API 开始主流程页面。
3. 产品 / 架构负责人开始按 PR 和接口契约把控边界。
```

## T2：第一轮垂直闭环开发节点

目标闭环：

```text
创建 PlantingPlan
  -> 生成 CalendarItem / TaskGenerationPlan
  -> 生成 FarmingTask
  -> 查看 OperationPlan
  -> 创建 Execution
  -> 写入 Feedback
  -> 生成 ReviewRequest
```

后端任务：

```text
1. 建表和迁移。
2. PlantingPlan / CalendarItem / FarmingTask / OperationPlan 基础接口。
3. EventRecord 和最小 PlanOrchestrator。
4. Execution / Feedback / ReviewRequest 基础接口。
```

前端任务：

```text
1. 计划创建页。
2. 计划详情页。
3. 农事项 / 任务列表。
4. 任务详情和方案查看。
5. 反馈和复核入口。
```

产品 / 架构任务：

```text
1. Review PR。
2. 更新设计文档中的实际决策。
3. 控制新增需求不打断第一轮闭环。
```

## T3：运行期事件与复核增强节点

目标：

```text
1. FieldConditionReported / WeatherUpdated 等事件入口。
2. Runtime Rule Engine 最小规则判断。
3. TaskIntent 和人工确认。
4. FeedbackGenerated 和 ReviewRequestResolved 的完整回流。
```

---

# 5. 阶段安排

## Phase 0：项目范围与核心边界

状态：

```text
done
```

目标：

```text
1. 明确 MVP 只做 Plan-level orchestration。
2. 明确不做多计划全局调度、复杂审批流、独立 Recommendation。
3. 明确 CalendarItem / TaskIntent / FarmingTask / OperationPlan 边界。
```

主要产物：

```text
docs/system-function.md
docs/architecture.md
docs/domain-model.md
docs/decisions/
```

完成标准：

```text
1. 核心对象不再频繁变动。
2. 模块边界有明确禁止事项。
3. 关键设计取舍有 ADR。
```

---

## Phase 1：流程与编排设计

状态：

```text
done
```

目标：

```text
1. 明确计划创建、运行期事件、执行反馈三条主流程。
2. 明确 Feedback 和 ReviewRequestResolved 必须回到 Plan Orchestrator。
3. 明确 Orchestrator 内部不做超级服务类。
```

主要产物：

```text
docs/flows/
docs/events.md
docs/orchestration-design.md
docs/decisions/006-orchestrator-internal-layering.md
```

完成标准：

```text
1. 每类关键事件有归属模块。
2. Handler / Policy / Strategy / Service 只作为内部实现分层。
3. Execution Module 与 Task Module 边界清楚。
```

---

## Phase 2：逻辑数据模型设计

状态：

```text
in_progress
```

目标：

```text
1. 确定第一版实体清单。
2. 确定实体关系。
3. 确定字段草案。
4. 确定状态枚举。
5. 确定幂等、追溯、版本和历史策略。
```

主要产物：

```text
docs/data-model.md
```

当前已确认：

```text
1. EventRecord 进入第一版数据模型。
2. Farm / Field 进入第一版数据模型。
3. 当前没有用户体系，用户相关字段先用字符串占位。
4. stageCode 当前按固定编码处理。
5. taskCategory 固定大类，taskSubtype 允许后续新增。
6. 同一 FarmingTask 同一时间只允许一个 active OperationPlan。
7. 同一 FarmingTask 允许多次 Execution。
8. 附件、图片、无人机轨迹 MVP 先放 JSON。
9. 关键幂等键建议数据库唯一约束。
10. 软删除先统一使用业务 status，不引入 deletedAt。
11. DeviceCommand 与 Execution 暂不强行确定一对一，先允许一个 Execution 关联 0..N 个 DeviceCommand。
12. ReviewRequest.decision 先采用最简单枚举，复杂内容放 decisionPayload。
13. Farm 第一版字段为 farmName、longitude、latitude、address、province。
14. Field 第一版字段为 farmId、boundaryAddress。
```

待完成：

```text
1. 使用 docs/data-model-validation.md 核对业务流程和算法服务。
2. 根据核对结果更新 docs/data-model.md。
3. 生成 ER 图。
4. 固化 stageCode 第一版枚举。
5. 固化 taskSubtype 第一版建议清单。
6. 确定后端技术栈。
7. 根据后端技术栈生成表结构或 ORM 草案。
```

完成标准：

```text
1. data-model.md 中没有阻塞表结构设计的问题。
2. ER 图能覆盖 MVP 主链路。
3. 字段、状态、关系足以支持计划创建到反馈复核闭环。
```

---

## Phase 3：技术栈与工程骨架

状态：

```text
not_started
```

目标：

```text
1. 确定后端语言、框架、数据库和迁移工具。
2. 建立最小工程骨架。
3. 建立模块目录边界。
4. 建立基础测试和本地运行方式。
```

当前推荐但未最终拍板：

```text
后端：Python + FastAPI
数据库：PostgreSQL
迁移：Alembic
ORM：SQLAlchemy
数据校验 / DTO：Pydantic
接口：REST API + OpenAPI
前端：由前端负责人选择
ID：UUID 或数据库生成 ID
命名：数据库 snake_case，代码 camelCase
```

前端技术栈暂不强制指定，但需要遵守接口契约：

```text
1. 接口协议：REST API。
2. API 文档：OpenAPI。
3. Mock：基于 OpenAPI 或固定 JSON 示例。
4. API 字段命名：camelCase。
5. 时间格式：ISO 8601。
6. 枚举值：与 docs/data-model.md 保持一致。
```

备选：

```text
1. Django + Django REST Framework + PostgreSQL：适合需要后台管理能力优先的场景。
2. Node.js + NestJS + PostgreSQL + Prisma：适合后端团队更熟 TypeScript 的场景。
3. Java + Spring Boot + PostgreSQL：适合后续强企业集成和团队有 Java 经验的场景。
```

进入条件：

```text
1. Phase 2 数据模型达到可落表程度。
2. 后端技术栈已明确。
3. 前端技术栈由前端负责人确认，或已明确 mock 和接口对接方式。
```

完成标准：

```text
1. 本地可以启动服务或运行测试。
2. 数据库迁移可以执行。
3. 模块目录与文档边界一致。
```

---

## Phase 4：核心闭环最小实现

状态：

```text
not_started
```

目标：

```text
1. 实现 PlantingPlan 创建。
2. 实现 PlanCreated 编排入口。
3. 实现 Stage 初始化占位能力。
4. 实现 CalendarItem / TaskGenerationPlan / FarmingTask 创建链路。
5. 实现 OperationPlan 占位或简单生成。
```

完成标准：

```text
1. 创建 PlantingPlan 后能生成预备农事项。
2. 能按窗口生成近期 FarmingTask。
3. 任务和方案数据可追溯来源。
```

---

## Phase 5：运行期事件与任务意图

状态：

```text
not_started
```

目标：

```text
1. 实现 EventRecord。
2. 实现 FieldConditionReported / WeatherUpdated 等事件入口。
3. 实现 Runtime Rule Engine 的最小规则判断。
4. 实现 TaskIntent 生成、NeedMoreInfo、NoAction 记录。
5. 实现人工确认 TaskIntent 转 FarmingTask。
```

完成标准：

```text
1. 运行期事件不会直接生成 FarmingTask。
2. TaskIntent 能保留规则原因和建议动作。
3. 人工确认后由 Plan Orchestrator 编排生成 FarmingTask。
```

---

## Phase 6：执行、评价、反馈与复核

状态：

```text
not_started
```

目标：

```text
1. 实现 Execution / ExecutionRecord。
2. 实现 DeviceCommand 占位或设备下发抽象。
3. 实现 Evaluation / Feedback。
4. 实现 ReviewRequest。
5. 实现 FeedbackGenerated 和 ReviewRequestResolved 回到 Plan Orchestrator。
```

完成标准：

```text
1. Execution Module 不创建 FarmingTask。
2. Feedback 不直接生成任务。
3. ReviewRequestResolved 不绕过 Plan Orchestrator。
4. 执行反馈能触发复核或后续任务调整。
```

---

## Phase 7：规则、策略与任务类型扩展

状态：

```text
not_started
```

目标：

```text
1. 拆分 TaskTypeStrategy。
2. 补充灌溉、施肥、植保、巡田、整地、收割等类型差异。
3. 收敛 taskSubtype 清单。
4. 补充策略测试。
```

完成标准：

```text
1. 新增农事子类不需要新增核心对象。
2. 不同农事类型差异不堆在 Plan Orchestrator 中。
3. 策略行为有测试覆盖。
```

---

# 6. 近期任务清单

建议下一轮按以下顺序推进：

```text
1. 使用 docs/data-model-validation.md 核对业务流程和算法服务。
2. 将核对结论回写到 docs/data-model.md。
3. 生成 docs/er-diagram.md。
4. 确定后端技术栈。
5. 前端负责人确认前端技术栈或 mock 对接方式。
6. 根据后端技术栈生成数据库表结构草案。
7. 再决定是否创建工程骨架。
```

---

# 7. 当前不做

```text
1. 不创建完整工程框架，直到后端技术栈明确。
2. 不做多农场、多计划全局调度。
3. 不做复杂审批流。
4. 不做独立 Recommendation Entity。
5. 不做完整规则后台配置系统。
```
