# CropFlow 团队启动说明会

> 本文档用于第一次团队说明会。  
> 目标不是把所有设计细节讲完，而是让团队对项目目标、系统架构、分工方式和下一步推进达成一致。

---

# 1. 会议目标

本次会议需要达成：

```text
1. 所有人理解 CropFlow 第一版要解决什么问题。
2. 所有人理解 Plan-level MVP 的边界。
3. 所有人理解核心对象链路和关键流转。
4. 明确后端、前端和各业务方向的职责。
5. 明确当前还不能直接全面分工开发，需要先完成 T1 契约。
6. 明确会后每个方向需要补什么材料。
```

本次会议不解决：

```text
1. 不现场细化所有农事项字段。
2. 不现场确定所有算法参数。
3. 不现场设计完整数据库表。
4. 不现场拆所有开发任务。
5. 不讨论多计划调度、复杂审批、资源排程等后续能力。
```

---

# 2. 会前阅读

建议参会人员会前至少阅读：

```text
docs/overview/team-technical-briefing.md
docs/planning/team-work-division.md
docs/planning/development-roadmap.md
```

使用 AI agent 辅助开发的人员额外阅读：

```text
AGENTS.md
docs/planning/agent-development-guidelines.md
```

---

# 3. 参会角色

| 角色 | 关注重点 |
|---|---|
| 产品 / 架构负责人 | 项目目标、边界、核心对象、分工和阶段推进 |
| 核心后端 | 数据模型、模块边界、API contract、核心闭环 |
| 农事日历 / 生育期方向 | 生育期预测、农事日历、CalendarItem 生成和更新 |
| 植保方向 | 植保调查、防治方案、打药作业、效果评价和补防判断 |
| 灌溉方向 | 灌溉方案、水位设备、执行反馈和异常处理 |
| 施肥方向 | 施肥方案、变量处方图、肥料库存、施肥效果抽查 |
| 遥感监测方向 | 缺苗识别、长势监测、影像处理、异常点位和处方图衔接 |
| 前端 | 页面清单、交互流程、mock API、任务和方案展示 |

---

# 4. 建议会议议程

建议控制在 60-90 分钟。

| 时间 | 主题 | 讲解重点 | 参考文档 |
|---|---|---|---|
| 5 min | 项目背景 | 为什么要做 CropFlow，第一版解决什么问题 | team-technical-briefing 1 |
| 10 min | MVP 边界 | 只做单个 PlantingPlan 内部闭环 | team-technical-briefing 1 |
| 15 min | 系统架构 | Plan Orchestrator 如何协调 Stage / Task / Execution / Review | team-technical-briefing 2 |
| 15 min | 核心对象 | CalendarItem、FarmingTask、OperationPlan、ExecutionRecord、Feedback 的区别 | team-technical-briefing 3 |
| 15 min | 关键流转 | 计划初始化、任务生成、运行期事件、方案生成、执行反馈、人工复核 | team-technical-briefing 4 |
| 15 min | 分工方式 | 各方向负责算法适配、OperationPlan、ExecutionRecord、Evaluation / Feedback | team-work-division |
| 10 min | 推进节奏 | 当前 T0、进入 T1 的条件、第一条垂直闭环 | development-roadmap |
| 10 min | 现场确认 | 第一条闭环、会后交付物、下一次评审时间 | 本文档第 8 节 |

---

# 5. 讲解主线

开场可以按下面这条线讲：

```text
CropFlow 第一版不是做一个完整农事管理平台，
而是先把一个种植计划内部的农事编排闭环跑通。

一个 PlantingPlan 创建后，
系统根据生育期、农事日历、调查结果、算法结果和人工反馈，
持续维护这个计划下的预备农事项、正式任务、作业方案、执行记录、反馈和复核事项。
```

核心链路：

```text
PlantingPlan
→ CropStageState / StagePredictionSnapshot
→ CalendarItem
→ TaskIntent / FarmingTask
→ OperationPlan
→ Execution / ExecutionRecord
→ Evaluation / Feedback
→ ReviewRequest
→ 回到 Plan Orchestrator 判断是否调整后续任务
```

重点强调：

```text
1. CalendarItem 是预备农事项，不是正式任务。
2. FarmingTask 是正式任务，是执行入口。
3. OperationPlan 是作业方案或处方方案。
4. ExecutionRecord 记录执行过程和结果。
5. Feedback 不能直接生成任务，必须回到 Plan Orchestrator。
6. 各业务方向不能各自定义一套任务、方案、执行和反馈模型。
```

---

# 6. 分工说明方式

## 6.1 核心后端

核心后端负责统一底座：

```text
1. PlantingPlan / Field / CalendarItem / FarmingTask / OperationPlan 等核心表结构。
2. 核心 API contract。
3. Plan Orchestrator / Task Module / Execution Module 的基础链路。
4. EventRecord / ReviewRequest / Feedback 的统一模型。
5. 为各方向提供 adapter、mapper、rule 的接入方式。
```

核心后端不替业务方向定义农艺规则和算法字段。

## 6.2 各业务方向

植保、灌溉、施肥、遥感监测、农事日历 / 生育期方向都需要围绕统一对象补齐：

```text
1. 本方向有哪些农事项。
2. 每个农事项何时触发。
3. 调用哪些算法接口。
4. 算法输入来自哪些对象字段。
5. 算法输出写入 OperationPlan / CalendarItem / TaskIntent / ReviewRequest / EventRecord 的哪里。
6. 执行结果如何形成 ExecutionRecord。
7. 评价和反馈如何形成 Evaluation / Feedback。
8. 是否需要人工复核。
9. 是否可能影响后续任务。
```

## 6.3 前端

前端先围绕第一条闭环设计页面：

```text
1. 计划创建。
2. 计划详情。
3. 农事项日历 / 任务列表。
4. 任务详情。
5. OperationPlan 查看。
6. 执行反馈录入和查看。
7. Evaluation / Feedback 查看。
8. ReviewRequest 处理。
9. 遥感监测结果查看。
10. 库存入库和流水查看。
```

---

# 7. 当前阶段判断

当前仍处于 T0：

```text
逻辑数据模型和接口核对阶段。
```

还不建议直接全面分工编码。

进入分工开发前，需要完成 T1 契约：

```text
1. ER 图。
2. 第一版表结构草案。
3. 第一版 API contract。
4. 技术栈和本地开发方式。
5. 前端页面清单。
6. 第一条垂直闭环验收标准。
7. AI agent 任务模板和代码交付规范。
```

建议第一条垂直闭环先选植保方向，因为当前已有算法接口文档，比较适合作为端到端样例。

---

# 8. 现场需要确认的问题

本次会议建议现场确认：

```text
1. 是否同意第一条垂直闭环优先选择植保。
2. 是否同意后端技术栈先按 Python + FastAPI + PostgreSQL 推进。
3. 是否同意前端技术栈由前端负责人确定，但必须以 API contract 为准。
4. 每个业务方向的负责人是谁。
5. 每个方向会后先补接口 / 流程材料，还是直接补代码样例。
6. 下一次评审是看 ER 图、API contract，还是看第一条闭环任务拆解。
```

如果现场无法确定，至少记录为待决事项，不要让方向开发各自假设。

---

# 9. 会后行动项

| 负责人 | 会后交付 |
|---|---|
| 产品 / 架构负责人 | 确认第一条垂直闭环范围，整理待决事项，安排下一次评审 |
| 核心后端 | 输出 ER 图、表结构草案、API contract 初稿 |
| 农事日历 / 生育期 | 补齐农事日历和生育期算法输入输出样例 |
| 植保 | 补齐植保调查、防治推荐、补防判断、效果评价的接口和数据映射 |
| 灌溉 | 补齐灌溉方案、设备数据、执行反馈和异常处理样例 |
| 施肥 | 补齐施肥方案、变量处方图、库存扣减、穗肥效果抽查样例 |
| 遥感监测 | 补齐缺苗识别、长势监测、影像处理、异常点位和处方图衔接样例 |
| 前端 | 输出第一版页面清单、页面流转、mock 数据需求 |

---

# 10. 会后文档更新规则

会后如果产生结论，按下面位置更新：

| 结论类型 | 更新文档 |
|---|---|
| 核心对象或字段 | `docs/model/data-model.md` |
| 数据模型待确认问题 | `docs/model/data-model-validation.md` |
| 农事项流程 | `docs/workflow/task-workflow-matrix.md` |
| 后台任务 | `docs/workflow/background-job-matrix.md` |
| 团队分工 | `docs/planning/team-work-division.md` |
| 推进节奏 | `docs/planning/development-roadmap.md` |
| Agent 开发约束 | `docs/planning/agent-development-guidelines.md` |
| 架构说明 | `docs/overview/team-technical-briefing.md` |

