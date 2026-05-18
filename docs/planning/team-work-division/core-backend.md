# 核心后端方向

> 本文档从团队分工总览中拆出，用于单独说明核心后端方向的职责、交付物和实现边界。

建议负责人：后端主责。

## 当前阶段说明

当前项目仍处于核心对象、ER 图、表结构草案和 API contract 收敛阶段。

因此本方向当前任务以非代码收敛和统一约束为主，用于冻结核心对象、接口边界和实现框架，而不是立即把完整后端工程、所有迁移和闭环代码一次性交付。

## 主要职责

```text
1. 建立 FastAPI 工程结构。
2. 建立 PostgreSQL 表结构和 Alembic 迁移。
3. 实现 Farm / Field / PlantingPlan 基础接口。
4. 实现 CalendarItem / TaskIntent / FarmingTask / OperationPlan 基础模型。
5. 实现 Execution / ExecutionRecord / Evaluation / Feedback / ReviewRequest 基础模型。
6. 实现 EventRecord、幂等键、状态流转、审计字段。
7. 实现最小 PlanOrchestrator 和 Handler 框架。
8. 提供 OpenAPI、mock 数据和种子数据。
```

## 当前阶段任务总表

| 方向 | 当前要交什么 | 产出形式 | 依赖谁拍板 |
|---|---|---|---|
| 核心后端 | 技术栈和本地开发方式确认记录 | 1 页说明或执行约定 | 产品 / 架构负责人 |
| 核心后端 | 第一版核心对象清单和关系草案 | 对象关系表 / 字段草案 | 产品 / 架构负责人 |
| 核心后端 | 第一版表结构草案 | 表结构草表 / 字段清单 | 产品 / 架构负责人 |
| 核心后端 | 第一版 API contract 范围建议 | 接口清单 / 请求响应草案 | 产品 / 架构负责人、前端 |
| 核心后端 | 编排最小骨架建议 | 目录草案 / 组件职责说明 | 产品 / 架构负责人 |
| 核心后端 | 第一条闭环最小实现边界建议 | 范围说明 / 风险点清单 | 产品 / 架构负责人、植保 |

## 当前阶段非代码任务

```text
1. 技术栈和本地开发方式确认记录：
   明确依赖管理、数据库、迁移方式、容器方式和最小启动约定。
2. 第一版核心对象清单和关系草案：
   明确 PlantingPlan、CalendarItem、TaskIntent、FarmingTask、OperationPlan、Execution、Feedback、ReviewRequest、EventRecord 的边界和关系。
3. 第一版表结构草案：
   给出核心表、关键字段、状态字段、审计字段和幂等字段草案。
4. 第一版 API contract 范围建议：
   明确哪些接口先进入第一条闭环，哪些接口后续补充。
5. 编排最小骨架建议：
   明确 orchestrator、handler、module、adapter、mapper、rule、service 的分层职责。
6. 第一条闭环最小实现边界建议：
   明确 PlanCreated、CalendarItem、TaskDueCheckJob、OperationPlan、Feedback、ReviewRequest 的最小链路边界。
7. 统一提交模板和承接规则：
   明确各业务方向提交的字段草案、触发规则表、依赖关系表、场景表如何落到统一对象和核心文档中。
8. 核心文档回写清单：
   明确 docs/model、docs/workflow、docs/api 中哪些文档需要由核心后端负责同步收口。
```

## 当前阶段完成标准

```text
1. 不要求当前就提交完整工程代码、全部迁移脚本或所有接口实现。
2. 需要给出能支撑各方向继续收敛的统一对象边界、表结构草案和 API contract 范围。
3. 需要明确各方向提交物如何映射到核心对象和核心文档。
4. 第一条闭环的最小实现边界、风险点和待决事项必须显式列出。
```

## 需要交付的通用能力

| 能力 | 说明 |
|---|---|
| 计划能力 | 创建、查询、更新计划状态 |
| 预备农事项能力 | 生成、查询、失效、重算 CalendarItem |
| 正式任务能力 | 创建、确认、取消、完成 FarmingTask |
| 作业方案能力 | 创建 OperationPlan、版本管理、激活 / 失效 |
| 执行能力 | 创建 Execution、记录 ExecutionRecord、接收回调或人工反馈 |
| 评价反馈能力 | 保存 Evaluation / Feedback，并触发 Plan Orchestrator |
| 复核能力 | 创建 ReviewRequest、处理结论、回到 Plan Orchestrator |
| 算法适配能力 | 为农事日历、植保、灌溉、施肥、遥感监测提供统一 adapter 接口和错误处理 |

## 进入实现阶段后参考的代码落点

```text
1. 后端项目骨架和本地启动说明。
2. 第一版数据库迁移脚本。
3. OpenAPI 草案和 mock 数据。
4. 核心对象 CRUD / 查询接口。
5. PlanCreated 到 CalendarItem 的最小链路。
6. CalendarItem 到 FarmingTask 的最小链路。
7. FarmingTask 到 OperationPlan 的最小链路。
8. ExecutionRecord / Feedback / ReviewRequest 最小闭环。
9. 各业务方向 adapter 的接口占位和样例实现。
```

## 进入实现阶段后代码落点说明

```text
1. 后端项目骨架和本地启动说明：
   需要说明目录结构、依赖管理方式、启动命令、配置文件约定和本地数据库准备方式。
2. 第一版数据库迁移脚本：
   至少覆盖 PlantingPlan、CalendarItem、FarmingTask、OperationPlan、Execution、Feedback、ReviewRequest、EventRecord 的基础表结构。
3. OpenAPI 草案和 mock 数据：
   至少覆盖计划创建、任务查询、方案查询、执行反馈录入、复核处理接口，并提供最小请求响应样例。
4. 核心对象 CRUD / 查询接口：
   重点是可支撑前端和方向联调，不要求一次性补齐所有管理接口。
5. PlanCreated 到 CalendarItem 的最小链路：
   需要说明输入事件、调用服务、生成对象、幂等键和验证方式。
6. CalendarItem 到 FarmingTask 的最小链路：
   需要明确生成窗口、阻断条件、重复生成防护和状态变化。
7. FarmingTask 到 OperationPlan 的最小链路：
   需要明确哪些 taskSubtype 允许生成方案、方案版本如何保留、旧方案如何失效。
8. ExecutionRecord / Feedback / ReviewRequest 最小闭环：
   需要明确执行结果如何落库、如何产生 Feedback、何时创建 ReviewRequest、如何回到 PlanOrchestrator。
9. 各业务方向 adapter 的接口占位和样例实现：
   重点是统一接口协议、错误处理约定和 mock 返回，不要求所有方向都接真实外部服务。
```

## 进入实现阶段后代码交付物

```text
1. backend/app/main.py 或等价应用入口。
2. backend/app/db/ 数据库连接、基础模型、迁移配置。
3. backend/app/models/ 核心 ORM 模型。
4. backend/app/schemas/common/ 通用 DTO。
5. backend/app/modules/plan/ 计划基础能力。
6. backend/app/modules/task/ CalendarItem / TaskIntent / FarmingTask / OperationPlan 通用能力。
7. backend/app/modules/execution/ Execution / ExecutionRecord / DeviceCommand 通用能力。
8. backend/app/modules/feedback/ Evaluation / Feedback 通用能力。
9. backend/app/modules/review/ ReviewRequest / SystemNotification 通用能力。
10. backend/app/orchestrators/ PlanOrchestrator 和基础 Handler。
11. backend/app/adapters/base.py 外部算法 adapter 基类或协议。
12. backend/tests/ 覆盖核心对象和第一条闭环的测试。
```

## 进入实现阶段后代码交付物说明

| 交付物 | 最少需要包含 |
|---|---|
| `backend/app/main.py` | 应用入口、路由注册、基础中间件或生命周期初始化 |
| `backend/app/db/` | 数据库连接、会话管理、基础模型或迁移配置 |
| `backend/app/models/` | 核心 ORM 模型、基础关联、状态字段和审计字段 |
| `backend/app/schemas/common/` | 通用请求响应 DTO、分页或通用枚举 |
| `backend/app/modules/plan/` | PlantingPlan 创建、查询、状态更新等基础能力 |
| `backend/app/modules/task/` | CalendarItem、TaskIntent、FarmingTask、OperationPlan 的创建、查询、状态流转 |
| `backend/app/modules/execution/` | Execution、ExecutionRecord、DeviceCommand 的通用处理 |
| `backend/app/modules/feedback/` | Evaluation / Feedback 的落库和回编排入口 |
| `backend/app/modules/review/` | ReviewRequest 创建、查询、处理结论能力 |
| `backend/app/orchestrators/` | PlanOrchestrator、handler registry、最小事件处理器 |
| `backend/app/adapters/base.py` | 外部算法或外部系统 adapter 的统一协议、错误结构、超时约定 |
| `backend/tests/` | 单元测试 + 最小链路集成测试，至少覆盖第一条闭环主链路 |

## 不要做

```text
1. 不先做复杂规则后台。
2. 不把编排逻辑写进 Entity 或 Repository。
3. 不让 Execution Module 直接创建 FarmingTask。
4. 不替业务方向臆造算法字段和农艺规则。
5. 不为了未来扩展提前做复杂框架。
```
